# -*- encoding: utf-8 -*-
"""
app_settings — INI 配置持久化（含旧 QSettings 注册表迁移与便携模式）

基于 docs/2026-10-17-多语言国际化方案分析.md §7 的设计：

- 配置以 INI 格式存储于 config.ini（configparser，UTF-8）
- 默认位置为本地应用数据目录下的单层应用名文件夹，如 Windows 的
  %LOCALAPPDATA%/Toolbox/config.ini（不含组织名层）
- exe 同目录存在可写的 portable.flag 时进入便携模式，配置随程序携带
- 文件缺失/损坏时用默认值初始化并报告错误；加载不会覆盖已存在的值
- 写入前把旧文件备份为 config.ini.bak，写入采用 tmp + os.replace 原子替换
- migrate_from_qsettings() 读取旧版 QSettings("Toolbox", "App") 的
  theme/geometry/windowState，仅在 INI 尚无对应值时复制，且不删除注册表

使用 config_dir=None（自动定位）时，调用方须先创建 QApplication，
否则 QStandardPaths 无法解析本地应用数据目录。

迁移时机约定：migrate_from_qsettings() 应在首次创建 INI 时（即第一次
构造 AppSettings 后）调用——此时默认值尚未被视为已保存值，注册表数据
得以导入；INI 已存在时其中所有键均视为已保存值，迁移不会覆盖。

INI 结构::

    [setting]
    language=zh_CN
    theme=dark

    [setting.window]
    geometry=
    state=

    [setting.nav]
    order=
    hidden=

    [setting.meta]
    config_version=2

    [plugin.<id>]
    ...
"""

import base64
import configparser
import os
import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import QByteArray, QSettings, QStandardPaths

ORG_NAME = "yansheng836"
APP_NAME = "Toolbox"

# 旧版 QSettings("Toolbox", "App") 的身份与键名（保守迁移，不删除）
_LEGACY_ORG = "Toolbox"
_LEGACY_APP = "App"
# 旧键名 -> (INI 节, INI 键)
_LEGACY_KEY_MAP = {
    "theme": ("setting", "theme"),
    "geometry": ("setting.window", "geometry"),
    "windowState": ("setting.window", "state"),
}

CONFIG_FILE_NAME = "config.ini"
PORTABLE_FLAG_DEFAULT_NAME = "portable.flag"
CONFIG_VERSION = 2

# 默认值：仅用于填充缺失项，加载时绝不覆盖文件中已有的值
_DEFAULTS = {
    "setting": {"language": "zh_CN", "theme": "dark"},
    "setting.window": {"geometry": "", "state": ""},
    "setting.nav": {"order": "", "hidden": ""},
    "setting.meta": {"config_version": str(CONFIG_VERSION)},
}


class AppSettings:
    """INI 配置的读取、写入、迁移与便携模式定位"""

    def __init__(self, config_dir=None, portable_flag_name=PORTABLE_FLAG_DEFAULT_NAME):
        """初始化并定位 config.ini，随后立即加载

        参数:
            config_dir: 配置目录。None 时按优先级自动定位：
                1. exe/脚本同目录存在 portable.flag 且可写 -> 该目录下 config.ini
                2. 否则本地应用数据目录 / "Toolbox" / config.ini
                   （需先创建 QApplication 以解析标准路径）
            portable_flag_name: 便携标志文件名
        """
        self._portable_flag_name = portable_flag_name
        self._config_path = str(
            self._resolve_config_path(config_dir, portable_flag_name)
        )
        # 显式存在于 INI 文件中或经 set() 设置的 "section.key" 集合；
        # 用于迁移时区分"已保存值"与"默认值填充"，避免迁移覆盖用户数据
        self._explicit_keys = set()
        self._parser = configparser.ConfigParser(interpolation=None)
        self.load()

    # ==================== 路径定位 ====================

    @property
    def config_path(self):
        """config.ini 的绝对路径（str）"""
        return self._config_path

    @staticmethod
    def _resolve_config_path(config_dir, portable_flag_name):
        """按优先级解析 config.ini 路径

        非便携模式落在本地应用数据目录下的单层应用名目录，
        如 Windows 的 %LOCALAPPDATA%/Toolbox/config.ini（不含组织名层）。
        """
        if config_dir is not None:
            return Path(config_dir) / CONFIG_FILE_NAME

        base_dir = AppSettings._portable_base_dir(portable_flag_name)
        if base_dir is not None:
            return base_dir / CONFIG_FILE_NAME

        data_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.GenericDataLocation
        )
        return Path(data_dir) / APP_NAME / CONFIG_FILE_NAME

    @staticmethod
    def _portable_base_dir(portable_flag_name):
        """返回便携模式的基础目录；不满足条件返回 None

        打包运行（sys.frozen）用 exe 所在目录，源码运行用项目根目录
        （common/ 的上一级）。目录不可写时返回 None，回退本地应用数据目录。
        """
        if getattr(sys, "frozen", False):
            base = Path(os.path.dirname(sys.executable))
        else:
            base = Path(__file__).resolve().parent.parent

        flag = base / portable_flag_name
        if not flag.exists():
            return None
        if not AppSettings._is_writable_dir(base):
            return None
        return base

    @staticmethod
    def _is_writable_dir(directory):
        """检查目录是否可写（通过创建并删除临时文件探测）"""
        probe = Path(directory) / f".write_test_{os.getpid()}.tmp"
        try:
            with open(probe, "w", encoding="utf-8"):
                pass
            return True
        except OSError:
            return False
        finally:
            try:
                if probe.exists():
                    probe.unlink()
            except OSError:
                # 探测文件无法删除（如目录权限在中途变化），不影响结论
                print(f"警告：无法清理写测试临时文件 {probe}")

    # ==================== 读 ====================

    def load(self):
        """读取 INI；文件缺失用默认值初始化，损坏则报告错误并用默认值

        只填充缺失的键，绝不覆盖文件中已存在的值（旧版 init_theme 无条件
        重置主题的问题在此杜绝）。首次运行或文件损坏时，把默认值立即落盘。
        """
        self._parser = configparser.ConfigParser(interpolation=None)
        self._explicit_keys = set()
        path = Path(self.config_path)
        rewrite_needed = True
        if path.exists():
            try:
                # utf-8-sig：兼容用户用记事本保存时带入的 BOM
                read_ok = self._parser.read(str(path), encoding="utf-8-sig")
                if not read_ok:
                    raise OSError(f"无法读取 {path}")
            except (OSError, ValueError, configparser.Error) as e:
                # ValueError 覆盖 UnicodeDecodeError（如记事本另存的 GBK 内容）
                print(f"配置文件损坏或无法读取，使用默认值：{e}")
                self._parser = configparser.ConfigParser(interpolation=None)
            else:
                # 文件中已有值均为"已保存值"，供迁移判断使用
                self._explicit_keys = {
                    f"{section}.{key}"
                    for section in self._parser.sections()
                    for key in self._parser[section]
                }
                rewrite_needed = False
        else:
            print(f"配置文件不存在，使用默认值初始化：{path}")

        # 旧版全局节 [general]/[window]/[nav]/[meta] → setting.*（v1 → v2），
        # 发生迁移时需重写文件
        if self._migrate_legacy_sections():
            rewrite_needed = True

        self._fill_defaults()
        self._check_version()
        if rewrite_needed:
            try:
                self.save()
            except OSError as e:
                # 配置目录不可写时降级为仅内存配置，不阻塞启动
                print(f"警告：无法写入配置文件，本次设置将不会持久化：{e}")
        return True

    def _migrate_legacy_sections(self):
        """把旧版全局节 [general]/[window]/[nav]/[meta] 迁到 setting.* 节

        v1 配置的全局节与插件节 [plugin.*] 平铺；v2 起全局项统一收进
        setting.* 命名空间，与插件配置区分清晰。目标键已存在则不覆盖
        （用户已保存值优先）。迁移后移除旧节并升级 config_version。
        返回是否发生改动。
        """
        legacy_map = {
            "general": "setting",
            "window": "setting.window",
            "nav": "setting.nav",
            "meta": "setting.meta",
        }
        touched = False
        for old_section, new_section in legacy_map.items():
            if not self._parser.has_section(old_section):
                continue
            touched = True
            for key, value in self._parser.items(old_section):
                if self._parser.has_option(new_section, key):
                    continue  # 目标已存在，不覆盖
                if not self._parser.has_section(new_section):
                    self._parser.add_section(new_section)
                self._parser.set(new_section, key, value)
                self._explicit_keys.add(f"{new_section}.{key}")
            # 旧节已无用途，移除并同步清理 explicit_keys
            self._parser.remove_section(old_section)
            self._explicit_keys = {
                k for k in self._explicit_keys
                if not k.startswith(f"{old_section}.")
            }
        if touched:
            if not self._parser.has_section("setting.meta"):
                self._parser.add_section("setting.meta")
            self._parser.set("setting.meta", "config_version", str(CONFIG_VERSION))
        return touched

    def _check_version(self):
        """配置文件版本高于当前程序时提示可能不兼容（仅警告，不阻断启动）"""
        try:
            file_version = int(self._parser.get("meta", "config_version", fallback="0"))
        except ValueError:
            file_version = 0
        if file_version > CONFIG_VERSION:
            print(
                f"警告：配置文件版本 ({file_version}) 高于当前程序版本 "
                f"({CONFIG_VERSION})，部分设置可能无法识别"
            )

    def _fill_defaults(self):
        """为解析结果中缺失的节/键填充默认值（不覆盖已有值）"""
        for section, keys in _DEFAULTS.items():
            if not self._parser.has_section(section):
                self._parser.add_section(section)
            for key, value in keys.items():
                if not self._parser.has_option(section, key):
                    self._parser.set(section, key, value)

    def get(self, section, key, default=None):
        """读取配置值；键不存在时返回 default"""
        if self._parser.has_option(section, key):
            return self._parser.get(section, key)
        return default

    def is_explicit(self, section, key):
        """键是否来自配置文件或 set()，而非启动时填充的默认值"""
        return f"{section}.{key}" in self._explicit_keys

    # ==================== 写 ====================

    def set(self, section, key, value):
        """设置配置值（内存中；需调用 save() 持久化）"""
        value = str(value)
        if not self._parser.has_section(section):
            self._parser.add_section(section)
        self._parser.set(section, key, value)
        self._explicit_keys.add(f"{section}.{key}")

    def save(self):
        """把当前配置写入 INI；写前把旧文件备份为 config.ini.bak

        原子写：先写 config.ini.tmp，再 os.replace 覆盖目标文件。
        """
        path = Path(self.config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            bak_path = Path(str(path) + ".bak")
            try:
                shutil.copy2(str(path), str(bak_path))
            except OSError as e:
                # 备份失败不阻塞保存（.bak 仅是安全网），但要报告
                print(f"警告：备份配置文件失败 {bak_path}：{e}")

        tmp_path = Path(str(path) + ".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                self._parser.write(f, space_around_delimiters=False)
            os.replace(str(tmp_path), str(path))
        except OSError:
            # 清理写失败的临时文件，避免残留
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError as e:
                print(f"警告：无法清理临时文件 {tmp_path}：{e}")
            raise
        return True

    def remove_section(self, section):
        """删除指定节；不存在则无操作（供插件 reset_settings 清空本插件配置）"""
        if self._parser.has_section(section):
            self._parser.remove_section(section)

    def reset(self):
        """清空所有已保存设置并恢复默认值（旧文件备份为 config.ini.bak）"""
        self._parser = configparser.ConfigParser(interpolation=None)
        self._explicit_keys = set()
        self._fill_defaults()
        self.save()

    # ==================== 旧 QSettings 迁移 ====================

    def migrate_from_qsettings(self):
        """从旧版 QSettings("Toolbox", "App")（Windows 注册表）迁移配置

        读取 theme/geometry/windowState，仅在 INI 中尚无对应已保存值时复制；
        迁移后不删除注册表数据（保守策略，便于回滚）。

        返回:
            bool：是否发生了实际复制
        """
        legacy = QSettings(_LEGACY_ORG, _LEGACY_APP)
        migrated = False
        for legacy_key, (section, key) in _LEGACY_KEY_MAP.items():
            # 已保存值（来自文件或用户/迁移设置）优先，迁移不得覆盖
            if f"{section}.{key}" in self._explicit_keys:
                continue
            value = legacy.value(legacy_key)
            if value is None:
                continue
            # QByteArray（geometry/windowState 的 saveGeometry 载荷）用 base64
            # 存储；str(QByteArray) 是 Python repr（b'...'），无法还原
            if isinstance(value, QByteArray):
                value = bytes(value.toBase64()).decode("ascii")
            self.set(section, key, str(value))
            migrated = True
        if migrated:
            try:
                self.save()
            except OSError as e:
                print(f"警告：迁移结果无法写入配置文件：{e}")
        return migrated


def bytes_to_qbytearray(encoded):
    """把 migrate_from_qsettings 存的 base64 字符串还原为 QByteArray

    用于接线阶段读取 [window] geometry/state 后传给 restoreGeometry/
    restoreState。非 base64 字符串（如手工配置）原样转为 QByteArray。
    """
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raw = encoded.encode("utf-8")
    return QByteArray(raw)


def setup_app_identity(app):
    """设置应用身份（organizationName/applicationName）

    配置路径不再依赖应用身份（直接用 APP_NAME 定位），但 QSettings、
    窗口类名等 Qt 功能仍使用组织名，因此启动时调用一次即可。
    """
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)
    return app
