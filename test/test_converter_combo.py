# -*- encoding: utf-8 -*-
"""图片格式转换下拉项解耦：fmt_combo 每项 data 等于格式名"""

import pytest

from plugins.image_format_converter import FormatConverter


@pytest.fixture
def converter_widget(qapp):
    from toolbox import Theme
    plugin = FormatConverter.__new__(FormatConverter)
    plugin.icon = "🔁"
    plugin.name = "图片格式转换"
    plugin.description = ""
    plugin.widget = None
    plugin.theme = Theme.DARK
    w = plugin.create_ui()
    return plugin, w


def test_converter_fmt_combo_data(converter_widget):
    plugin, _ = converter_widget
    combo = plugin.fmt_combo
    for fmt in ["JPEG", "PNG", "WebP", "BMP", "TIFF", "GIF"]:
        assert combo.findData(fmt) >= 0, f"缺少 data: {fmt}"
