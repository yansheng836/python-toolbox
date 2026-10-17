# -*- encoding: utf-8 -*-
"""图片转 PDF 页面大小下拉解耦：size_combo 每项携带稳定 data"""

import pytest

from plugins.image_to_pdf import ImageToPDF


@pytest.fixture
def pdf_widget(qapp):
    from toolbox import Theme
    plugin = ImageToPDF.__new__(ImageToPDF)
    plugin.icon = "🖨️"
    plugin.name = "图片转PDF"
    plugin.description = ""
    plugin.widget = None
    plugin.theme = Theme.DARK
    w = plugin.create_ui()
    return plugin, w


def test_pdf_size_combo_data(pdf_widget):
    plugin, _ = pdf_widget
    combo = plugin.size_combo
    assert combo.findData("smart") >= 0
    assert combo.findData("auto") >= 0
    assert combo.findData("A4") >= 0
    assert combo.findData("A3") >= 0
    assert combo.findData("original") >= 0


def test_pdf_default_smart(pdf_widget):
    plugin, _ = pdf_widget
    assert plugin.size_combo.currentData() == "smart"
