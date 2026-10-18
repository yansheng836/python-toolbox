# -*- encoding: utf-8 -*-
"""
test_p2_settings_language — P2-C 设置页语言切换测试

覆盖：语言下拉填充、切换持久化到 INI 并触发重放、静态文本重放、
主题切换回归（P2-A 反覆盖修复后仍正常持久化）。
"""

import configparser

import pytest

from common import i18n
from config import APP_VERSION
from toolbox import ToolboxWindow, Theme


TEST_EN = {
    "settings.label.language": "Language:",
    "settings.label.appearance": "Appearance:",
    "settings.card.general": "General",
    "settings.card.about": "About",
    "settings.button.light_theme": "☀️ Light",
    "settings.button.dark_theme": "🌙 Dark",
    "settings.label.version": "Version: v{version}",
    "settings.link.check_update": "Check updates",
    "settings.link.feedback": "Feedback",
    "app.website_link_text": "🌐 Website",
    "app.copyright": "© 2026 yansheng836",
}


@pytest.fixture
def en_dict_injected():
    saved = dict(i18n.manager._dicts)
    saved_current = i18n.manager.current_language
    i18n.manager._dicts["en"] = dict(TEST_EN)
    yield i18n.manager
    i18n.manager._dicts.clear()
    i18n.manager._dicts.update(saved)
    i18n.set_language(saved_current)


def _read_ini(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(str(path), encoding="utf-8")
    return parser


def _make_window(tmp_path):
    from common.app_settings import AppSettings
    settings = AppSettings(config_dir=tmp_path)
    return ToolboxWindow(settings=settings)


@pytest.mark.usefixtures("qapp")
def test_language_combo_populated(tmp_path):
    """语言下拉 2 项，data 为 zh_CN/en，当前选中为 zh_CN"""
    win = _make_window(tmp_path)
    try:
        settings_plugin = win.plugins["settings"]
        settings_plugin.get_widget()  # 确保 UI 已创建
        combo = settings_plugin.language_combo
        assert combo.count() == 2
        assert {combo.itemData(i) for i in range(combo.count())} == {"zh_CN", "en"}
        assert combo.currentData() == "zh_CN"
    finally:
        win.close()


@pytest.mark.usefixtures("qapp")
def test_switch_language_persists_and_retranslates(tmp_path, en_dict_injected):
    """选 en → INI general.language=en 且 current_language 变化；选回恢复"""
    win = _make_window(tmp_path)
    try:
        sp = win.plugins["settings"]
        sp.get_widget()
        combo = sp.language_combo

        combo.setCurrentIndex(combo.findData("en"))
        assert i18n.manager.current_language == "en"
        ini = _read_ini(tmp_path / "config.ini")
        assert ini.get("general", "language") == "en"

        combo.setCurrentIndex(combo.findData("zh_CN"))
        assert i18n.manager.current_language == "zh_CN"
        ini = _read_ini(tmp_path / "config.ini")
        assert ini.get("general", "language") == "zh_CN"
    finally:
        win.close()


@pytest.mark.usefixtures("qapp")
def test_retranslate_updates_static_texts(tmp_path, en_dict_injected):
    """切语言后设置页静态文本重放为英文，切回恢复中文"""
    win = _make_window(tmp_path)
    try:
        sp = win.plugins["settings"]
        sp.get_widget()
        combo = sp.language_combo

        combo.setCurrentIndex(combo.findData("en"))
        assert sp.theme_label.text() == "Appearance:"
        assert sp.language_label.text() == "Language:"
        assert sp.light_theme_btn.text() == "☀️ Light"
        assert sp._general_card.title_label.text() == "General"
        assert sp.version_label.text() == f"Version: v{APP_VERSION}"

        combo.setCurrentIndex(combo.findData("zh_CN"))
        assert sp.theme_label.text() == "外观:"
        assert sp._general_card.title_label.text() == "通用设置"
    finally:
        win.close()


@pytest.mark.usefixtures("qapp")
def test_theme_still_works(tmp_path):
    """回归：语言切换接线后主题切换仍持久化且应用（反覆盖修复不回归）"""
    win = _make_window(tmp_path)
    try:
        sp = win.plugins["settings"]
        sp.get_widget()
        sp.switch_theme("light")

        assert win._current_theme is Theme.LIGHT
        ini = _read_ini(tmp_path / "config.ini")
        assert ini.get("general", "theme") == "light"
    finally:
        win.close()
