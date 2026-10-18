# -*- encoding: utf-8 -*-
"""
test_p2_wiring — P2 启动接线测试

覆盖：main.py 启动顺序单元级验证、ToolboxWindow 几何走 INI 的往返、
init_theme 读取已保存主题（反覆盖）。
"""

import configparser

import pytest

from common import i18n
from common.app_settings import AppSettings
from main import resolve_startup_language
from toolbox import ToolboxWindow, Theme


INI_NAME = "config.ini"


def _read_ini(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(str(path), encoding="utf-8")
    return parser


def test_main_startup_order_smoke(tmp_path):
    """启动顺序单元级验证：AppSettings → set_language 生效"""
    settings = AppSettings(config_dir=tmp_path)
    settings.set("setting", "language", "zh_CN")
    settings.save()

    i18n.set_language(settings.get("setting", "language", "zh_CN"))
    assert i18n.manager.current_language == "zh_CN"


def test_resolve_startup_language_first_run(tmp_path, monkeypatch):
    """首次启动：按系统语言初始化并写回 INI，标记为自动检测"""
    monkeypatch.setattr(i18n, "detect_system_language", lambda: "en")
    settings = AppSettings(config_dir=tmp_path)
    assert not settings.is_explicit("setting", "language")

    assert resolve_startup_language(settings) == ("en", True)
    assert _read_ini(tmp_path / INI_NAME).get("setting", "language") == "en"


def test_resolve_startup_language_keeps_saved_choice(tmp_path, monkeypatch):
    """已有保存值（用户选择）优先，不再按系统语言重设，也不弹提示"""
    first = AppSettings(config_dir=tmp_path)
    first.set("setting", "language", "zh_CN")
    first.save()

    monkeypatch.setattr(i18n, "detect_system_language", lambda: "en")
    settings = AppSettings(config_dir=tmp_path)
    assert resolve_startup_language(settings) == ("zh_CN", False)


@pytest.mark.usefixtures("qapp")
def test_toolboxwindow_ini_geometry_roundtrip(tmp_path):
    """ToolboxWindow 用 INI 保存/恢复几何（base64 编码，无 QSettings）"""
    settings = AppSettings(config_dir=tmp_path)
    win1 = ToolboxWindow(settings=settings)
    win1.resize(1100, 760)
    win1.save_geometry()

    ini = _read_ini(tmp_path / INI_NAME)
    geo = ini.get("setting.window", "geometry")
    assert geo  # 非空 base64
    assert not geo.startswith("b'")  # 不是 Python repr

    win2 = ToolboxWindow(settings=AppSettings(config_dir=tmp_path))
    # restoreGeometry 成功后 geometry() 尺寸应接近保存值
    assert win2.width() > 900

    win1.close()
    win2.close()


@pytest.mark.usefixtures("qapp")
def test_init_theme_reads_saved_theme(tmp_path):
    """INI 已保存 theme=light → init_theme 应用 LIGHT；无值 → 默认 dark"""
    light_dir = tmp_path / "light"
    default_dir = tmp_path / "default"

    settings = AppSettings(config_dir=light_dir)
    settings.set("setting", "theme", "light")
    settings.save()

    win_light = ToolboxWindow(settings=AppSettings(config_dir=light_dir))
    assert win_light._current_theme is Theme.LIGHT
    win_light.close()

    # default_dir 从未写入 theme，走默认 dark
    win_default = ToolboxWindow(settings=AppSettings(config_dir=default_dir))
    assert win_default._current_theme is Theme.DARK
    win_default.close()


@pytest.mark.usefixtures("qapp")
def test_init_theme_does_not_write(tmp_path):
    """init_theme 不写回 INI（启动加载绝不覆盖已存值）"""
    settings = AppSettings(config_dir=tmp_path)
    ini_path = tmp_path / INI_NAME
    before = ini_path.read_text(encoding="utf-8")

    win = ToolboxWindow(settings=settings)
    win.init_theme()

    assert ini_path.read_text(encoding="utf-8") == before
    win.close()
