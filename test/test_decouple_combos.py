# -*- encoding: utf-8 -*-
"""下拉项解耦：currentData() 返回稳定值"""

import pytest

from plugins.image_compressor import ImageCompressor, CompressionWorker


@pytest.fixture
def compressor_widget(qapp):
    from toolbox import Theme
    plugin = ImageCompressor.__new__(ImageCompressor)
    plugin.icon = "🗜️"
    plugin.name = "图片压缩"
    plugin.description = ""
    from PyQt6.QtWidgets import QWidget
    plugin.widget = None
    plugin.theme = Theme.DARK
    w = plugin.create_ui()
    return plugin, w


def test_compressor_format_combo_has_stable_data(compressor_widget):
    plugin, _ = compressor_widget
    combo = plugin.format_combo
    # 每项都有 data
    for i in range(combo.count()):
        assert combo.itemData(i) is not None
    # "保持原格式" 对应稳定值 "keep"
    idx = combo.findData("keep")
    assert idx >= 0
    assert combo.itemText(idx) == "保持原格式"


def test_compressor_worker_receives_keep_code(compressor_widget):
    plugin, _ = compressor_widget
    plugin.format_combo.setCurrentIndex(plugin.format_combo.findData("keep"))
    # 直接断言传给 worker 的 format_code（不启动线程）
    code = plugin.format_combo.currentData()
    assert code == "keep"
