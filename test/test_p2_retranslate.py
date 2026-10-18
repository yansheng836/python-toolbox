# -*- encoding: utf-8 -*-
"""
test_p2_retranslate — P2-B 主框架 t() 迁移与语言切换重放测试

覆盖：ToolboxWindow.retranslate_ui 全框架文本、侧边栏插件按钮按 id 重放、
欢迎页文本重放、ToolPlugin 基类空实现。

en.json 尚未存在（P4 阶段交付），测试通过向 manager._dicts 注入临时
en 词典来模拟语言切换，结束后恢复。
"""

import pytest

from common import i18n
from config import APP_VERSION
from toolbox import ToolboxWindow, ToolPlugin


TEST_EN = {
    "app.window_title": "Toolbox v{version}",
    "sidebar.logo_text": "Toolbox",
    "sidebar.home": "Home",
    "sidebar.version": "v{version}",
    "sidebar.tooltip.collapse": "Collapse sidebar",
    "sidebar.tooltip.expand": "Expand sidebar",
    "tray.tooltip": "Toolbox",
    "tray.show": "Show",
    "tray.quit": "Quit",
    "menu.file": "File",
    "menu.exit": "Exit",
    "menu.tools": "Tools",
    "menu.settings": "Settings",
    "menu.view": "View",
    "menu.toggle_sidebar": "Toggle sidebar",
    "welcome.title": "Toolbox",
    "welcome.subtitle": "Offline, fast, beautiful desktop tools",
    "welcome.hint": "👈 Pick a tool from the sidebar",
    "plugin.settings.name": "Settings EN",
}


@pytest.fixture
def en_dict_injected():
    """注入临时 en 词典，测试结束恢复"""
    saved = dict(i18n.manager._dicts)
    saved_current = i18n.manager.current_language
    i18n.manager._dicts["en"] = dict(TEST_EN)
    yield i18n.manager
    i18n.manager._dicts.clear()
    i18n.manager._dicts.update(saved)
    i18n.set_language(saved_current)


@pytest.mark.usefixtures("qapp")
def test_retranslate_switches_framework_text(en_dict_injected):
    """切 en 后窗口标题/logo/首页按钮/菜单/版本标签变英文，切回恢复"""
    win = ToolboxWindow()
    try:
        i18n.set_language("en")
        assert win.windowTitle() == f"Toolbox v{APP_VERSION}"
        assert win.logo_text.text() == "Toolbox"
        assert "Home" in win.home_btn.text()
        assert win.file_menu.title() == "File"
        assert win.tools_menu.title() == "Tools"
        assert win.settings_action.text() == "Settings"
        assert win.view_menu.title() == "View"
        assert win.toggle_sidebar_action.text() == "Toggle sidebar"

        i18n.set_language("zh_CN")
        assert win.windowTitle() == f"工具箱 v{APP_VERSION}"
        assert win.logo_text.text() == "工具箱"
        assert "首页" in win.home_btn.text()
        assert win.file_menu.title() == "文件"
    finally:
        win.close()


@pytest.mark.usefixtures("qapp")
def test_plugin_button_texts_follow_language(en_dict_injected):
    """侧边栏插件按钮按稳定 id 重放文本"""
    win = ToolboxWindow()
    try:
        i18n.set_language("en")
        btn = next(
            b for b in (win.nav_layout.itemAt(i).widget()
                        for i in range(win.nav_layout.count()))
            if isinstance(b, type(win.home_btn)) and b.plugin_id() == "settings"
        )
        assert "Settings EN" in btn.text()

        i18n.set_language("zh_CN")
        assert "设置" in btn.text()
    finally:
        win.close()


@pytest.mark.usefixtures("qapp")
def test_welcome_page_texts_follow_language(en_dict_injected):
    """欢迎页 title/subtitle/hint/功能卡片按 id 重放"""
    win = ToolboxWindow()
    try:
        wp = win.welcome_page
        i18n.set_language("en")
        assert wp.title.text() == "Toolbox"
        assert wp.subtitle.text() == "Offline, fast, beautiful desktop tools"
        assert wp.hint.text() == "👈 Pick a tool from the sidebar"
        # 功能卡片第一个（image_compressor）未被测试词典覆盖 → 回退 zh_CN
        first_text = wp.text_labels[0].text()
        assert first_text  # 非空即可（回退 zh_CN 原文）

        i18n.set_language("zh_CN")
        assert wp.title.text() == "工具箱"
        assert wp.subtitle.text() == "离线、高效、美观的桌面工具集合"
    finally:
        win.close()


def test_toolplugin_retranslate_default_noop():
    """基类 retranslate_ui() 空实现可调用不抛"""
    ToolPlugin().retranslate_ui()
