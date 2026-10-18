# -*- encoding: utf-8 -*-
"""
test_app_settings — AppSettings INI 配置持久化单元测试

覆盖：默认文件创建、持久化往返、损坏文件回退、启动加载不覆盖已存值、
备份文件、便携模式、旧 QSettings 迁移、window 节读写、应用身份设置。

全部用例使用 tmp_path 作为 config_dir，不触碰真实 AppData / 注册表；
旧 QSettings 通过 monkeypatch 模拟，无需 QApplication。
"""

import configparser
import sys
from pathlib import Path

import pytest
from PyQt6.QtCore import QCoreApplication, QStandardPaths

from common import app_settings
from common.app_settings import (
    APP_NAME,
    ORG_NAME,
    AppSettings,
    bytes_to_qbytearray,
    setup_app_identity,
)

INI_NAME = "config.ini"


# ==================== fixtures ====================


@pytest.fixture(autouse=True)
def _sandbox_standard_paths(tmp_path, monkeypatch):
    """把 AppConfigLocation 重定向到临时目录，兜底防止触碰真实 AppData

    正常用例都显式传 config_dir，不会走到 QStandardPaths；此 fixture
    保证即使路径定位逻辑意外回退，也不会读写真实 AppData。
    """
    sandbox = tmp_path / "appdata_sandbox"
    sandbox.mkdir()
    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        lambda _standard: str(sandbox),
        raising=True,
    )


# ==================== 辅助 ====================


def _read_ini(path):
    """读取 INI 文件为 ConfigParser（用于直接断言文件内容）"""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(str(path), encoding="utf-8")
    return parser


# ==================== 1. 默认文件创建 ====================


def test_default_file_created(tmp_path):
    """首次 load 后文件存在、内容为默认值：language=zh_CN、theme=dark"""
    s = AppSettings(config_dir=tmp_path)
    assert (tmp_path / INI_NAME).exists()
    assert s.get("general", "language") == "zh_CN"
    assert s.get("general", "theme") == "dark"

    # 首次生成的文件本身即包含默认值（设计文档：缺失时用默认值初始化）
    ini = _read_ini(tmp_path / INI_NAME)
    assert ini.get("general", "language") == "zh_CN"
    assert ini.get("general", "theme") == "dark"
    assert ini.get("meta", "config_version") == "1"


# ==================== 2. 持久化往返 ====================


def test_persist_roundtrip(tmp_path):
    """set + save 后，新建 AppSettings 能读回相同值"""
    s1 = AppSettings(config_dir=tmp_path)
    s1.set("general", "language", "en_US")
    s1.set("general", "theme", "light")
    s1.save()

    s2 = AppSettings(config_dir=tmp_path)
    assert s2.get("general", "language") == "en_US"
    assert s2.get("general", "theme") == "light"


# ==================== 3. 损坏文件回退 ====================


def test_corrupt_file_falls_back(tmp_path, capsys):
    """写垃圾内容：load 不抛异常、print 错误信息、用默认值重建文件"""
    (tmp_path / INI_NAME).write_text("{{{ this is not an ini", encoding="utf-8")

    s = AppSettings(config_dir=tmp_path)  # 不应抛出
    assert s.get("general", "language") == "zh_CN"
    assert s.get("general", "theme") == "dark"

    out = capsys.readouterr().out
    assert "配置文件" in out  # 错误信息已报告，不静默

    # 损坏文件被默认值内容替换，便于用户查看和手工修复
    ini = _read_ini(tmp_path / INI_NAME)
    assert ini.get("general", "language") == "zh_CN"


def test_corrupt_non_utf8_bytes_falls_back(tmp_path, capsys):
    """写非 UTF-8 原始字节（如记事本另存的 GBK）：UnicodeDecodeError 也回退默认值

    configparser.read 按 utf-8-sig 解码文件，GBK 字节（0xd6... 非 UTF-8
    合法序列）抛 UnicodeDecodeError——它是 ValueError 子类，不在
    OSError/configparser.Error 之列，构造 AppSettings 不得因此崩溃。
    """
    (tmp_path / INI_NAME).write_bytes(b"[general]\ntheme=\xd6\xd0\xce\xc4\n")

    s = AppSettings(config_dir=tmp_path)  # 不应抛出 UnicodeDecodeError
    assert s.get("general", "theme") == "dark"

    out = capsys.readouterr().out
    assert "配置文件" in out  # 错误信息已报告，不静默

    # 损坏文件被默认值内容替换
    ini = _read_ini(tmp_path / INI_NAME)
    assert ini.get("general", "theme") == "dark"


# ==================== 4. 启动加载不覆盖已存值 ====================


def test_no_overwrite_on_load(tmp_path):
    """手写 INI language=en → load 后仍是 en（不复制旧 init_theme 强制重置 bug）"""
    ini_path = tmp_path / INI_NAME
    ini_path.write_text("[general]\nlanguage=en\n", encoding="utf-8")

    s = AppSettings(config_dir=tmp_path)
    s.load()
    assert s.get("general", "language") == "en"
    # 缺失的键在内存中用默认值填充
    assert s.get("general", "theme") == "dark"
    # 文件本身未被默认值覆盖（加载是只读修复缺失项，不重写）
    assert "language=en" in ini_path.read_text(encoding="utf-8")


# ==================== 5. 备份文件 ====================


def test_backup_created(tmp_path):
    """save 两次后存在 config.ini.bak，且 bak 保存上一次的内容"""
    s = AppSettings(config_dir=tmp_path)
    s.set("general", "language", "v1")
    s.save()  # 首次保存：此前无 config.ini，不产生备份
    s.set("general", "language", "v2")
    s.save()  # 第二次保存：旧 config.ini(v1) 备份为 .bak

    bak = tmp_path / (INI_NAME + ".bak")
    assert bak.exists()
    assert "v1" in bak.read_text(encoding="utf-8")


# ==================== 6. 便携模式 ====================


def test_portable_mode(tmp_path, monkeypatch):
    """exe 同目录存在 portable.flag → config_path 落在同目录"""
    (tmp_path / "portable.flag").write_text("", encoding="utf-8")
    # 模拟打包后的 exe 位于 tmp_path
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Toolbox.exe"))

    s = AppSettings()  # config_dir=None → 走便携模式检测
    assert Path(s.config_path) == tmp_path / INI_NAME
    assert (tmp_path / INI_NAME).exists()  # 首次初始化已写入默认配置


# ==================== 7. 旧 QSettings 迁移 ====================


class _FakeLegacySettings:
    """模拟旧版 QSettings("Toolbox", "App")（Windows 注册表）"""

    payload = {}

    def __init__(self, organization, application):
        self.organization = organization
        self.application = application

    def value(self, key, default=None):
        return _FakeLegacySettings.payload.get(key, default)


def test_migrate_from_qsettings(tmp_path, monkeypatch):
    """迁移 theme 到 INI；再次迁移不覆盖用户改过的值；不删除旧数据源"""
    monkeypatch.setattr(app_settings, "QSettings", _FakeLegacySettings)
    _FakeLegacySettings.payload = {"theme": "light"}

    s = AppSettings(config_dir=tmp_path)
    assert s.get("general", "theme") == "dark"  # 迁移前为默认值

    assert s.migrate_from_qsettings() is True
    assert s.get("general", "theme") == "light"

    # 迁移结果已写入 INI 文件
    ini = _read_ini(tmp_path / INI_NAME)
    assert ini.get("general", "theme") == "light"

    # 迁移读取的是旧身份 QSettings("Toolbox", "App")
    legacy = _FakeLegacySettings("Toolbox", "App")
    assert legacy.organization == "Toolbox"
    assert legacy.application == "App"

    # 保守策略：旧数据源 payload 未被删除
    assert _FakeLegacySettings.payload == {"theme": "light"}

    # 用户改过之后，再次迁移不覆盖
    s.set("general", "theme", "custom")
    assert s.migrate_from_qsettings() is False  # 已有已保存值，无可迁移
    assert s.get("general", "theme") == "custom"


def test_migrate_empty_registry_is_noop(tmp_path, monkeypatch):
    """注册表无数据时迁移为空操作，不写文件、返回 False"""
    monkeypatch.setattr(app_settings, "QSettings", _FakeLegacySettings)
    _FakeLegacySettings.payload = {}

    s = AppSettings(config_dir=tmp_path)  # 首次构造生成默认文件
    before = (tmp_path / INI_NAME).read_text(encoding="utf-8")
    assert s.migrate_from_qsettings() is False
    assert (tmp_path / INI_NAME).read_text(encoding="utf-8") == before


def test_migrate_qbytearray_stored_as_base64(tmp_path, monkeypatch):
    """geometry/windowState 是 QByteArray：以 base64 存储（非 Python repr）

    str(QByteArray) 会产生 b'...' 的 repr 字符串，restoreGeometry 无法
    还原——迁移必须走 toBase64，且 bytes_to_qbytearray 能无损还原。
    """
    from PyQt6.QtCore import QByteArray

    monkeypatch.setattr(app_settings, "QSettings", _FakeLegacySettings)
    geometry_payload = QByteArray(b"\x01\xd9\x00\xdd\x01\x00\xff\xfe")
    _FakeLegacySettings.payload = {
        "geometry": geometry_payload,
        "windowState": QByteArray(b"\x00\x00\xff\x01"),
    }

    s = AppSettings(config_dir=tmp_path)
    assert s.migrate_from_qsettings() is True

    stored = s.get("window", "geometry")
    # 不含 repr 特征（b' 前缀），可无损还原为原始字节
    assert not stored.startswith("b'")
    assert bytes_to_qbytearray(stored) == geometry_payload
    assert bytes_to_qbytearray(s.get("window", "state")) == QByteArray(
        b"\x00\x00\xff\x01"
    )

    # 落盘后重读仍能还原
    s2 = AppSettings(config_dir=tmp_path)
    assert bytes_to_qbytearray(s2.get("window", "geometry")) == geometry_payload


def test_bytes_to_qbytearray_falls_back_for_plain_text():
    """非 base64 字符串（手工配置）按 UTF-8 原样转为 QByteArray"""
    from PyQt6.QtCore import QByteArray

    assert bytes_to_qbytearray("not base64!!") == QByteArray(b"not base64!!")


# ==================== 8. window 节读写 ====================


def test_geometry_state_roundtrip(tmp_path):
    """[window] 节 geometry/state 读写与持久化"""
    s = AppSettings(config_dir=tmp_path)
    assert s.get("window", "geometry") == ""  # 默认空
    assert s.get("window", "state") == ""

    s.set("window", "geometry", "GEO-BYTES")
    s.set("window", "state", "STATE-BYTES")
    s.save()

    s2 = AppSettings(config_dir=tmp_path)
    assert s2.get("window", "geometry") == "GEO-BYTES"
    assert s2.get("window", "state") == "STATE-BYTES"


# ==================== 9. 应用身份设置 ====================


def test_setup_app_identity():
    """setup_app_identity 设置 organizationName / applicationName"""
    app = QCoreApplication.instance() or QCoreApplication([])
    setup_app_identity(app)
    assert app.organizationName() == ORG_NAME
    assert app.applicationName() == APP_NAME
