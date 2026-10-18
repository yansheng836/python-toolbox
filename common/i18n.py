# -*- encoding: utf-8 -*-
"""
i18n 基础设施：LanguageManager、t()、控件绑定器、qtbase 翻译器加载

设计依据 docs/2026-10-17-多语言国际化方案分析.md §6.2/6.3/6.7：

- JSON 词典 + 信号驱动即时刷新（方案 B）。
- 查找顺序：当前语言 → zh_CN → 返回 key 本身（缺失文件 → 空 dict + 警告）。
- t() 只做字典查找和字符串格式化，不依赖 Qt 对象，工作线程可安全调用。
- 业务代码只使用模块级 manager、t()、set_language()、bind()、bind_combo()。
"""

import json
import sys
import weakref
from pathlib import Path

import PyQt6
from PyQt6.QtCore import QLocale, QObject, QTranslator, pyqtSignal

# ==================== 语言注册表（扩展语言只加这里） ====================

LANGUAGES = {"zh_CN": "简体中文", "en": "English"}
DEFAULT_LANGUAGE = "zh_CN"


def detect_system_language():
    """按系统语言推断界面语言：中文（含各地区变体）→ zh_CN，其余 → en

    仅在首次启动（配置中尚无保存值）时调用。
    """
    if QLocale.system().name().startswith("zh"):
        return "zh_CN"
    return "en"

# 复数词条的候选形式：值为 {"one": ..., "other": ...} 时按 count 选择
_PLURAL_FORMS = ("one", "other")


class _SafeFormatDict(dict):
    """str.format_map 用的字典：未知占位符保持 {name} 原样，不抛 KeyError"""

    def __missing__(self, key):
        return "{" + key + "}"


class LanguageManager(QObject):
    """语言管理器：加载 JSON 词典、切换语言、发出 language_changed 信号"""

    language_changed = pyqtSignal(str)

    def __init__(self, dict_dir=None):
        super().__init__()
        if dict_dir is None:
            dict_dir = self._default_dict_dir()
        self._dict_dir = Path(dict_dir)
        self._dicts = {}  # {code: dict} 词典缓存，避免重复读盘
        self._current = DEFAULT_LANGUAGE
        self._bindings = []  # [(weakref.ref(widget), method, key, params)]

    # ---------- 目录解析 ----------

    @staticmethod
    def _default_dict_dir():
        """dict_dir=None 时解析词典目录：打包模式用 sys._MEIPASS/i18n"""
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / "i18n"
        return Path(__file__).parent.parent / "i18n"

    # ---------- 词典加载 ----------

    def _load_dict(self, code):
        """加载并缓存指定语言词典；文件缺失/损坏返回空 dict 并打印警告"""
        if code in self._dicts:
            return self._dicts[code]

        path = self._dict_dir / f"{code}.json"
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"i18n warning: dictionary not found: {path}")
            data = {}
        except json.JSONDecodeError as e:
            print(f"i18n warning: invalid JSON in {path}: {e}")
            data = {}

        self._dicts[code] = data
        return data

    def _lookup(self, key):
        """按 当前语言 → zh_CN 顺序查找词条；都缺失返回 None"""
        for code in (self._current, DEFAULT_LANGUAGE):
            entry = self._load_dict(code).get(key)
            if entry is not None:
                return entry
        return None

    # ---------- 语言切换 ----------

    def set_language(self, code):
        """切换语言：校验代码 → 加载词典（缓存）→ 重放绑定 → 发出信号"""
        if code not in LANGUAGES:
            raise ValueError(
                f"Unsupported language: {code!r}, valid: {sorted(LANGUAGES)}"
            )
        self._current = code
        self._load_dict(code)  # 提前加载，保证切换后 t() 立即可用
        self._replay_bindings()
        self.language_changed.emit(code)

    @property
    def current_language(self):
        return self._current

    # ---------- 翻译 ----------

    def translate(self, key, **params):
        """查找词条并格式化；缺失返回 key 本身；复数按 count 选择"""
        entry = self._lookup(key)
        if entry is None:
            return key

        if isinstance(entry, dict):
            entry = self._plural_form(entry, params)
            if not isinstance(entry, str):
                # 词典中非 {"one"/"other"} 结构的 dict 视为配置错误：
                # 打印警告并返回 key，避免 format_map 在运行时抛异常
                print(f"i18n warning: malformed entry for {key!r}: {entry!r}")
                return key

        return entry.format_map(_SafeFormatDict(params))

    @staticmethod
    def _plural_form(entry, params):
        """值为 {"one": ..., "other": ...} 时按 params["count"] 选择；否则原样返回"""
        if not all(form in entry for form in _PLURAL_FORMS):
            return entry
        count = params.get("count", 0)
        form = "one" if count == 1 else "other"
        return entry[form]

    # ---------- 控件绑定器 ----------

    def bind(self, widget, method, key, **params):
        """绑定控件方法到词条：立即执行一次，语言变化时自动重放

        只存弱引用；失效条目由 _replay_bindings 在重放时清理。
        不连接 destroyed 信号：窗口销毁期间的 Python 回调在某些
        时序下会导致进程崩溃。
        """
        ref = weakref.ref(widget)
        self._bindings.append((ref, method, key, params))
        self._apply(widget, method, key, params)

    def bind_combo(self, combo, items):
        """绑定下拉框：items=[(key, data)]；重放时用 findData 保持选中项"""
        ref = weakref.ref(combo)
        self._bindings.append((ref, None, items, None))
        self._apply_combo(combo, items)

    def _remove_binding(self, ref):
        """移除失效绑定（重放时清理由 GC 回收的控件）"""
        self._bindings = [b for b in self._bindings if b[0] is not ref]

    def _replay_bindings(self):
        """语言变化后遍历存活控件重放绑定；已销毁控件被跳过不崩溃"""
        for ref, method, key, params in list(self._bindings):
            widget = ref()
            if widget is None:
                self._remove_binding(ref)  # 已被 GC，顺手清理
                continue
            try:
                if method is None:
                    self._apply_combo(widget, key)
                else:
                    self._apply(widget, method, key, params)
            except RuntimeError:
                # C++ 对象已删除但 Python wrapper 仍存活（destroyed 时序边界）
                print(f"i18n warning: skip replay for destroyed widget, key={key}")

    def _apply(self, widget, method, key, params):
        """对单个控件执行 getattr(w, method)(t(key, **params))"""
        getattr(widget, method)(self.translate(key, **params))

    def _apply_combo(self, combo, items):
        """重建下拉项，用 findData 尽量保持当前 data 选中项

        重放期间屏蔽信号：清空/重填会触发 currentIndexChanged，若调用方
        在该信号里再次 set_language 会造成无限递归。
        """
        current_data = combo.currentData()
        combo.blockSignals(True)
        try:
            combo.clear()
            for key, data in items:
                combo.addItem(self.translate(key), data)
            if current_data is not None:
                index = combo.findData(current_data)
                if index >= 0:
                    combo.setCurrentIndex(index)
        finally:
            combo.blockSignals(False)


# ==================== 模块级单例与便捷函数（业务代码只用这些） ====================

manager = LanguageManager()


def t(key, **params):
    """翻译词条：委托 manager.translate，纯字典路径，线程安全"""
    return manager.translate(key, **params)


def set_language(code):
    """切换语言：委托 manager.set_language"""
    manager.set_language(code)


def bind(widget, method, key, **params):
    """绑定控件方法到词条：立即执行一次，语言变化时自动重放"""
    manager.bind(widget, method, key, **params)


def bind_combo(combo, items):
    """绑定下拉框：items=[(key, data)]；语言变化时重建并保持选中 data"""
    manager.bind_combo(combo, items)


# ==================== qtbase 翻译器（仅 Qt 标准对话框文本） ====================

_qt_translator = None  # 模块级 QTranslator；zh_CN 安装、en 移除


def install_qt_translator(app, code):
    """加载/移除 qtbase_<code>.qm；加载失败只打印不抛异常"""
    global _qt_translator

    if _qt_translator is not None:
        app.removeTranslator(_qt_translator)
        _qt_translator = None

    if code == DEFAULT_LANGUAGE:
        translations_dir = Path(PyQt6.__file__).parent / "Qt6" / "translations"
        translator = QTranslator()
        if translator.load(f"qtbase_{code}", str(translations_dir)):
            app.installTranslator(translator)
            _qt_translator = translator
        else:
            print(
                f"i18n warning: failed to load qtbase_{code}.qm "
                f"from {translations_dir}"
            )
    # 非 zh_CN（如 en）：不安装翻译器，Qt 标准对话框使用默认英文
