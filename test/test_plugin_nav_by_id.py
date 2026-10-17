# -*- encoding: utf-8 -*-
"""插件字典键与导航按 id 匹配"""

from toolbox import ToolboxWindow, SidebarButton


def test_plugins_dict_keyed_by_id(loaded_plugins):
    # 设置项可通过 id 取到
    assert "settings" in loaded_plugins
    assert loaded_plugins["settings"].name == "设置"


def test_all_plugins_have_id(loaded_plugins):
    for pid, plugin in loaded_plugins.items():
        assert hasattr(plugin, "id")
        assert plugin.id == pid


def test_switch_plugin_by_id(qapp):
    win = ToolboxWindow()
    win.load_plugins()
    win.switch_plugin("settings")
    assert win.current_plugin == "settings"


def test_sidebar_button_stores_plugin_id(qapp):
    btn = SidebarButton("image_compressor", "图片压缩", "🗜️")
    assert btn.plugin_id() == "image_compressor"
    # 显示文本仍包含中文名（翻译在后续计划处理）
    assert "图片压缩" in btn.text()
