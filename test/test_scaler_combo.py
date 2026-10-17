# -*- encoding: utf-8 -*-
"""
图片缩放下拉项解耦：scale_type 与 quality 使用 currentData() 稳定值
"""

import pytest

from plugins.image_scaler import ImageScaler


@pytest.fixture
def scaler_widget(qapp):
    from toolbox import Theme
    plugin = ImageScaler.__new__(ImageScaler)
    plugin.icon = "🔍"
    plugin.name = "图片缩放"
    plugin.description = ""
    plugin.theme = Theme.DARK
    w = plugin.create_ui()
    # combos 是 w（ImageScalerWidget）的属性，而非 plugin 的属性
    return plugin, w


def test_scaler_scale_type_combo_data(scaler_widget):
    _, w = scaler_widget
    combo = w.scale_type_combo
    assert combo.findData("percent") >= 0
    assert combo.findData("width") >= 0
    assert combo.findData("height") >= 0


def test_scaler_quality_combo_data_is_int(scaler_widget):
    _, w = scaler_widget
    combo = w.quality_combo
    for i in range(combo.count()):
        assert isinstance(combo.itemData(i), int)
    assert combo.findData(85) >= 0
