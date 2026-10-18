# -*- encoding: utf-8 -*-
"""图片转PDF插件 i18n 迁移测试：词典文本、retranslate_ui、组合框稳定 data"""

import pytest

from common import i18n
from common.i18n import t
from plugins.image_to_pdf import ImageToPDF, PDFWorker


EN_DICT = {
    "plugin.image_to_pdf.name": "Images to PDF",
    "plugin.image_to_pdf.description": "Merge multiple images into one PDF file",
    "plugin.image_to_pdf.card.list": "Image list (order equals PDF order)",
    "plugin.image_to_pdf.card.pdf_settings": "PDF settings",
    "plugin.image_to_pdf.label.page_size": "Page size:",
    "plugin.image_to_pdf.label.compress": "Enable compression:",
    "plugin.image_to_pdf.label.quality": "JPEG quality:",
    "plugin.image_to_pdf.label.output_file": "Output file:",
    "plugin.image_to_pdf.placeholder.output_file": "Choose save location...",
    "plugin.image_to_pdf.button.browse": "Browse",
    "plugin.image_to_pdf.button.start": "Start conversion",
    "plugin.image_to_pdf.combo.auto": "Auto fit",
    "plugin.image_to_pdf.combo.original": "Original size",
    "plugin.image_to_pdf.combo.smart": "Smart scaling",
    "plugin.image_to_pdf.filter.images": "Images (*.jpg *.jpeg *.png)",
    "plugin.image_to_pdf.dialog.save_pdf": "Save PDF",
    "plugin.image_to_pdf.dialog.error": "Error",
    "plugin.image_to_pdf.error.no_images_processed": (
        "No image was processed successfully, please check the files."
    ),
    "column.filename": "File name",
    "column.dimensions": "Dimensions",
    "column.size": "Size",
    "column.created": "Created",
}


@pytest.fixture
def pdf_plugin(qapp):
    """构造插件 UI（不启动工作线程）"""
    plugin = ImageToPDF.__new__(ImageToPDF)
    plugin.icon = "🖨️"
    plugin.name = "图片转PDF"
    plugin.description = ""
    plugin.widget = None
    plugin._test_widget = plugin.create_ui()  # 持有引用，避免 Qt 对象被回收
    return plugin


@pytest.fixture
def en_dict():
    """注入临时英文词典，测试结束后恢复原状"""
    saved = dict(i18n.manager._dicts)
    saved_current = i18n.manager.current_language
    i18n.manager._dicts["en"] = dict(EN_DICT)
    yield
    i18n.manager._dicts.clear()
    i18n.manager._dicts.update(saved)
    i18n.set_language(saved_current)


def _header_texts(plugin):
    table = plugin.file_panel.table
    return [
        table.horizontalHeaderItem(i).text()
        for i in range(table.columnCount())
    ]


def test_texts_use_dictionary_zh(pdf_plugin):
    """创建后关键文本等于 zh_CN 词典原文"""
    i18n.set_language("zh_CN")
    plugin = pdf_plugin

    assert plugin.title_label.text() == f"🖨️ {t('plugin.image_to_pdf.name')}"
    assert plugin.desc_label.text() == t("plugin.image_to_pdf.description")
    assert plugin.file_card.title_label.text() == t("plugin.image_to_pdf.card.list")
    assert plugin.settings_card.title_label.text() == t("plugin.image_to_pdf.card.pdf_settings")
    assert plugin.page_size_label.text() == t("plugin.image_to_pdf.label.page_size")
    assert plugin.compress_label.text() == t("plugin.image_to_pdf.label.compress")
    assert plugin.quality_title_label.text() == t("plugin.image_to_pdf.label.quality")
    assert plugin.output_file_label.text() == t("plugin.image_to_pdf.label.output_file")
    assert plugin.output_path.placeholderText() == t("plugin.image_to_pdf.placeholder.output_file")
    assert plugin.browse_btn.text() == t("plugin.image_to_pdf.button.browse")
    assert plugin.action_panel.btn.text() == t("plugin.image_to_pdf.button.start")

    # 表头列标签走 column.* 词典
    assert _header_texts(plugin) == [
        t("column.filename"),
        t("column.dimensions"),
        t("column.size"),
        t("column.created"),
    ]


def test_retranslate_switches_to_english(pdf_plugin, en_dict):
    """切换 en 后 retranslate_ui 把关键文本变为英文，切回 zh_CN 恢复"""
    plugin = pdf_plugin

    i18n.set_language("en")
    plugin.retranslate_ui()

    assert plugin.title_label.text() == f"🖨️ {t('plugin.image_to_pdf.name')}"
    assert plugin.file_card.title_label.text() == "Image list (order equals PDF order)"
    assert plugin.page_size_label.text() == "Page size:"
    assert plugin.compress_label.text() == "Enable compression:"
    assert plugin.quality_title_label.text() == "JPEG quality:"
    assert plugin.output_path.placeholderText() == "Choose save location..."
    assert plugin.browse_btn.text() == "Browse"
    assert plugin.action_panel.btn.text() == "Start conversion"
    assert _header_texts(plugin) == ["File name", "Dimensions", "Size", "Created"]
    assert plugin.file_panel.file_filter == EN_DICT["plugin.image_to_pdf.filter.images"]

    i18n.set_language("zh_CN")
    plugin.retranslate_ui()

    assert plugin.page_size_label.text() == t("plugin.image_to_pdf.label.page_size")
    assert plugin.browse_btn.text() == t("plugin.image_to_pdf.button.browse")
    assert _header_texts(plugin)[0] == t("column.filename")


def test_combo_keeps_stable_data(pdf_plugin, en_dict):
    """组合框每项 data 非空；切换语言后 currentData 不变"""
    plugin = pdf_plugin

    for i in range(plugin.size_combo.count()):
        assert plugin.size_combo.itemData(i)

    assert plugin.size_combo.currentData() == "smart"

    i18n.set_language("en")
    assert plugin.size_combo.currentData() == "smart"
    assert plugin.size_combo.currentText() == EN_DICT["plugin.image_to_pdf.combo.smart"]
    assert plugin.size_combo.findData("auto") >= 0

    i18n.set_language("zh_CN")
    assert plugin.size_combo.currentData() == "smart"
    assert plugin.size_combo.currentText() == t("plugin.image_to_pdf.combo.smart")


def test_worker_messages_use_dictionary(tmp_path, qapp):
    """worker 完成消息使用词典格式化（不启动线程）"""
    i18n.set_language("zh_CN")
    worker = PDFWorker([], str(tmp_path / "out.pdf"), "original")
    results = []
    worker.result.connect(lambda success, message: results.append((success, message)))

    worker.run()

    assert results == [
        (False, t("plugin.image_to_pdf.error.no_images_processed"))
    ]
