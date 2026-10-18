# -*- encoding: utf-8 -*-
"""
common/i18n 单元测试

词典 fixture 写入 tmp_path，完全隔离，不依赖仓库 i18n 目录。
运行：cd test && python -m pytest test_i18n.py -v
"""

import json
import threading

import pytest
from PyQt6.QtWidgets import QComboBox, QLabel

from common import i18n
from common.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGES,
    LanguageManager,
    bind,
    bind_combo,
    install_qt_translator,
    set_language,
    t,
)

# 测试词典：zh_CN 为源语言，en 缺少 only.zh 用于验证回退
TEST_DICTS = {
    "zh_CN.json": {
        "a.b": "你好 {name}",
        "p.c": {"one": "1 张", "other": "{count} 张"},
        "only.zh": "仅中文",
    },
    "en.json": {
        "a.b": "Hello {name}",
        "p.c": {"one": "{count} item", "other": "{count} items"},
    },
}


def _write_dicts(target_dir):
    """把测试词典写入 target_dir，返回该目录"""
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, content in TEST_DICTS.items():
        (target_dir / name).write_text(
            json.dumps(content, ensure_ascii=False), encoding="utf-8"
        )
    return target_dir


@pytest.fixture
def mgr(tmp_path, monkeypatch):
    """隔离 LanguageManager：词典来自 tmp_path，并接管模块级 manager"""
    m = LanguageManager(dict_dir=_write_dicts(tmp_path / "i18n"))
    monkeypatch.setattr(i18n, "manager", m)
    return m


def test_t_lookup_and_switch(mgr):
    """切换语言后 t() 返回对应语言文本（覆盖模块级 t/set_language 委托）"""
    assert DEFAULT_LANGUAGE in LANGUAGES
    assert mgr.current_language == DEFAULT_LANGUAGE

    set_language("en")
    assert t("a.b", name="X") == "Hello X"

    set_language("zh_CN")
    assert t("a.b", name="X") == "你好 X"


def test_fallback_to_zh_cn(mgr):
    """en 缺失的 key 回退到 zh_CN 原文"""
    set_language("en")
    assert t("only.zh") == "仅中文"


def test_missing_key_returns_key(mgr):
    """两种语言都缺失的 key 原样返回，便于发现遗漏"""
    set_language("en")
    assert t("no.such") == "no.such"

    set_language("zh_CN")
    assert t("no.such") == "no.such"


def test_plural(mgr):
    """复数词条：count==1 选 one，否则选 other"""
    assert t("p.c", count=1) == "1 张"

    set_language("en")
    assert t("p.c", count=1) == "1 item"
    assert t("p.c", count=2) == "2 items"


def test_unknown_placeholder_kept(mgr):
    """未知占位符保持 {name} 原样，不抛 KeyError（运行时健壮性）"""
    assert t("a.b") == "你好 {name}"

    set_language("en")
    assert t("a.b") == "Hello {name}"


def test_language_changed_signal(mgr):
    """language_changed 信号携带新语言代码"""
    received = []
    mgr.language_changed.connect(received.append)

    set_language("en")
    set_language("zh_CN")

    assert received == ["en", "zh_CN"]


def test_set_language_rejects_unknown_code(mgr):
    """未注册的语言代码抛 ValueError，且不改变当前语言"""
    assert "fr" not in LANGUAGES
    with pytest.raises(ValueError):
        set_language("fr")
    assert mgr.current_language == DEFAULT_LANGUAGE


def test_malformed_plural_entry_returns_key(mgr):
    """缺 one/other 的 dict 词条视为配置错误：返回 key 不崩溃"""
    mgr._load_dict("zh_CN")["bad.entry"] = {"unexpected": "结构"}
    assert t("bad.entry", count=3) == "bad.entry"


def test_binder_updates_label(mgr, qapp):
    """bind 立即执行一次；切换语言自动重放；销毁控件被跳过不崩溃"""
    label = QLabel()
    bind(label, "setText", "a.b", name="X")
    assert label.text() == "你好 X"

    set_language("en")
    assert label.text() == "Hello X"

    doomed = QLabel()
    bind(doomed, "setText", "only.zh")
    assert doomed.text() == "仅中文"

    del doomed  # 弱引用失效；重放时惰性清理，不再访问该控件
    set_language("zh_CN")
    assert label.text() == "你好 X"


def test_bind_combo_keeps_selection(mgr, qapp):
    """bind_combo 填充项并重放；切换语言后文本变、currentData 选中不变"""
    combo = QComboBox()
    bind_combo(combo, [("a.b", "keep"), ("p.c", "plural"), ("only.zh", "only")])

    assert combo.count() == 3
    assert combo.itemText(0) == "你好 {name}"
    assert combo.currentData() == "keep"

    combo.setCurrentIndex(2)
    assert combo.currentData() == "only"

    set_language("en")
    assert combo.count() == 3
    assert combo.itemText(0) == "Hello {name}"
    assert combo.itemText(2) == "仅中文"  # en 缺失 → 回退 zh_CN
    assert combo.currentData() == "only"  # 选中项 data 保持不变


def test_bind_combo_replay_does_not_emit_signals(mgr, qapp):
    """重放下拉项时屏蔽信号：防止 currentIndexChanged 处理器再次切语言造成递归"""
    combo = QComboBox()
    bind_combo(combo, [("a.b", "keep"), ("p.c", "plural")])
    emitted = []
    combo.currentIndexChanged.connect(emitted.append)

    set_language("en")  # 触发 _replay_bindings → clear+重填

    assert emitted == []  # 重放期间不应发出 currentIndexChanged
    assert combo.count() == 2


def test_t_without_qt(tmp_path, monkeypatch):
    """t() 为纯字典路径：可在普通线程调用，不依赖 QApplication/QWidget"""
    m = LanguageManager(dict_dir=_write_dicts(tmp_path / "i18n"))
    monkeypatch.setattr(i18n, "manager", m)
    set_language("en")

    results = {}

    def worker():
        results["en"] = t("a.b", name="X")
        results["fallback"] = t("only.zh")

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=5)

    assert results["en"] == "Hello X"
    assert results["fallback"] == "仅中文"


def test_missing_dict_dir_falls_back_to_keys(tmp_path, monkeypatch):
    """词典目录没有语言文件时使用空词典（打印警告），t() 返回 key 本身"""
    empty_dir = tmp_path / "empty_i18n"
    empty_dir.mkdir()

    m = LanguageManager(dict_dir=empty_dir)
    monkeypatch.setattr(i18n, "manager", m)

    assert m.current_language == DEFAULT_LANGUAGE
    assert t("a.b") == "a.b"


def test_install_qt_translator(qapp):
    """qtbase 翻译器：zh_CN 从 PyQt6 目录加载成功；en 移除翻译器"""
    install_qt_translator(qapp, "zh_CN")
    assert i18n._qt_translator is not None
    assert not i18n._qt_translator.isEmpty()

    install_qt_translator(qapp, "en")
    assert i18n._qt_translator is None


def _fake_qlocale_class(locale_name):
    """构造只实现 name()/system() 的 QLocale 替身，避免依赖真实系统区域"""

    class _FakeLocale:
        def name(self):
            return locale_name

    _FakeLocale.system = staticmethod(lambda: _FakeLocale())
    return _FakeLocale


@pytest.mark.parametrize(
    "locale_name, expected",
    [
        ("zh_CN", "zh_CN"),
        ("zh_TW", "zh_CN"),
        ("en_US", "en"),
        ("fr_FR", "en"),
    ],
)
def test_detect_system_language(locale_name, expected, monkeypatch):
    """系统语言检测：中文各变体映射 zh_CN，其余回退 en"""
    monkeypatch.setattr(i18n, "QLocale", _fake_qlocale_class(locale_name))
    assert i18n.detect_system_language() == expected
