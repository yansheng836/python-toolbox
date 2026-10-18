# -*- encoding: utf-8 -*-
"""
PDF拆分插件 i18n 迁移测试

覆盖：zh_CN 词典文本、retranslate_ui 英中切换、
组合框稳定 data、worker 消息走词典（不启动线程）。
"""

import pytest

from common import i18n
from common.i18n import t
from plugins import pdf_splitter as pdf_splitter_module
from plugins.pdf_splitter import PDFSplitter, PDFSplitWorker


EN_DICT = {
    "plugin.pdf_splitter.name": "PDF Splitter",
    "plugin.pdf_splitter.description": (
        "Split a PDF into images or single-page PDF files"
    ),
    "plugin.pdf_splitter.card.file_list": (
        "PDF file list (only one file supported)"
    ),
    "plugin.pdf_splitter.card.settings": "Split settings",
    "plugin.pdf_splitter.card.output": "Output settings",
    "plugin.pdf_splitter.label.output_format": "Output format:",
    "plugin.pdf_splitter.label.pages_per_split": "Pages per file:",
    "plugin.pdf_splitter.label.image_format": "Image format:",
    "plugin.pdf_splitter.label.quality": "Image quality:",
    "plugin.pdf_splitter.label.output_dir": "Output directory:",
    "plugin.pdf_splitter.spin.suffix": " pages/file",
    "plugin.pdf_splitter.placeholder.output_dir": "Default source directory",
    "plugin.pdf_splitter.button.browse": "Browse",
    "plugin.pdf_splitter.button.start_split": "Start splitting",
    "plugin.pdf_splitter.radio.pdf": "Single-page PDF",
    "plugin.pdf_splitter.radio.image": "Images",
    "plugin.pdf_splitter.filter.add_files": (
        "PDF files (*.pdf);;All files (*.*)"
    ),
    "plugin.pdf_splitter.dialog.choose_output_dir": "Choose output directory",
    "plugin.pdf_splitter.dialog.done_title": "Done",
    "plugin.pdf_splitter.dialog.error_title": "Error",
    "plugin.pdf_splitter.dialog.warning_title": "Warning",
    "plugin.pdf_splitter.error.install_pillow": (
        "Exporting images requires Pillow: pip install Pillow"
    ),
    "plugin.pdf_splitter.error.install_pymupdf": (
        "Please install PyMuPDF first: pip install PyMuPDF"
    ),
    "plugin.pdf_splitter.error.pymupdf_missing_status": (
        "Error: PyMuPDF library is not installed, please run: "
        "pip install PyMuPDF"
    ),
    "plugin.pdf_splitter.error.pymupdf_not_installed": (
        "PyMuPDF is not installed"
    ),
    "plugin.pdf_splitter.error.split_failed": "Split failed: {error}",
    "plugin.pdf_splitter.msg.convert_done": (
        "Conversion complete, generated {count} images"
    ),
    "plugin.pdf_splitter.msg.converting_page": (
        "Converting: page {index}/{total}"
    ),
    "plugin.pdf_splitter.msg.split_done": (
        "Split complete, generated {count} PDF files"
    ),
    "plugin.pdf_splitter.msg.splitting_pages": (
        "Splitting: pages {start}-{end}"
    ),
    "plugin.pdf_splitter.msg.starting": "Splitting...",
    "plugin.pdf_splitter.warning.no_file": "Please add a PDF file first!",
    "plugin.pdf_splitter.warning.no_output_dir": (
        "Please choose an output directory!"
    ),
    "plugin.pdf_splitter.warning.only_one_file": (
        "Splitting supports only one PDF file!"
    ),
}


@pytest.fixture(autouse=True)
def reset_language():
    """每个用例从 zh_CN 开始，避免语言状态泄漏"""
    i18n.set_language("zh_CN")
    yield
    i18n.set_language("zh_CN")


@pytest.fixture
def splitter(qapp):
    """构造插件 UI（不启动工作线程）"""
    plugin = PDFSplitter.__new__(PDFSplitter)
    plugin.icon = "✂️"
    plugin.name = "PDF拆分"
    plugin.description = "将PDF拆分为图片或单页PDF文件，支持自定义页数"
    plugin.widget = None
    plugin.create_ui()
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


def test_texts_use_dictionary_zh(splitter):
    """创建后关键文本等于 zh_CN 词典原文"""
    widget = splitter.widget

    assert splitter.title_label.text() == f"✂️ {t('plugin.pdf_splitter.name')}"
    assert splitter.title_label.text() == "✂️ PDF拆分"
    assert splitter.desc_label.text() == t("plugin.pdf_splitter.description")
    assert widget.file_card.title_label.text() == (
        t("plugin.pdf_splitter.card.file_list"))
    assert widget.file_card.title_label.text() == "PDF文件列表（仅支持一个文件）"
    assert widget.settings_card.title_label.text() == (
        t("plugin.pdf_splitter.card.settings"))
    assert widget.settings_card.title_label.text() == "拆分设置"
    assert widget.output_card.title_label.text() == (
        t("plugin.pdf_splitter.card.output"))
    assert widget.output_card.title_label.text() == "输出设置"
    assert widget.pdf_radio.text() == "单页PDF"
    assert widget.image_radio.text() == "图片"
    assert widget.format_label.text() == "输出格式:"
    assert widget.pages_label.text() == "拆分页数:"
    assert widget.pages_spin.suffix() == " 页/文件"
    assert widget.image_format_label.text() == "图片格式:"
    assert widget.quality_row_label.text() == "图片质量:"
    assert widget.output_label.text() == "输出目录:"
    assert widget.output_path.placeholderText() == "默认原文件目录"
    assert widget.browse_btn.text() == "浏览"
    assert widget.action_panel.btn.text() == "开始拆分"
    assert widget.file_panel.file_filter == "PDF文件 (*.pdf);;所有文件 (*.*)"


def test_retranslate_switches_to_english(splitter, en_dict):
    """切到 en 后 retranslate_ui 更新关键文本，切回 zh_CN 恢复"""
    widget = splitter.widget

    i18n.set_language("en")
    splitter.retranslate_ui()

    assert splitter.title_label.text() == "✂️ PDF Splitter"
    assert splitter.desc_label.text() == EN_DICT[
        "plugin.pdf_splitter.description"]
    assert widget.file_card.title_label.text() == (
        "PDF file list (only one file supported)")
    assert widget.settings_card.title_label.text() == "Split settings"
    assert widget.output_card.title_label.text() == "Output settings"
    assert widget.pdf_radio.text() == "Single-page PDF"
    assert widget.image_radio.text() == "Images"
    assert widget.format_label.text() == "Output format:"
    assert widget.pages_label.text() == "Pages per file:"
    assert widget.pages_spin.suffix() == " pages/file"
    assert widget.image_format_label.text() == "Image format:"
    assert widget.quality_row_label.text() == "Image quality:"
    assert widget.output_label.text() == "Output directory:"
    assert widget.output_path.placeholderText() == "Default source directory"
    assert widget.browse_btn.text() == "Browse"
    assert widget.action_panel.btn.text() == "Start splitting"
    assert widget.file_panel.file_filter == "PDF files (*.pdf);;All files (*.*)"

    i18n.set_language("zh_CN")
    splitter.retranslate_ui()

    assert splitter.title_label.text() == "✂️ PDF拆分"
    assert widget.file_card.title_label.text() == "PDF文件列表（仅支持一个文件）"
    assert widget.pdf_radio.text() == "单页PDF"
    assert widget.format_label.text() == "输出格式:"
    assert widget.pages_spin.suffix() == " 页/文件"
    assert widget.output_path.placeholderText() == "默认原文件目录"
    assert widget.action_panel.btn.text() == "开始拆分"


def test_combo_keeps_stable_data(splitter, en_dict):
    """图片格式下拉项 data 非空，切语言后 currentData 不变"""
    combo = splitter.widget.image_format_combo

    for i in range(combo.count()):
        assert combo.itemData(i) is not None

    combo.setCurrentIndex(combo.findData("PNG"))
    i18n.set_language("en")
    splitter.retranslate_ui()

    assert combo.currentData() == "PNG"
    assert combo.currentText() == "PNG"


def test_worker_missing_fitz_message_uses_dictionary(qapp, monkeypatch):
    """FITZ 不可用时 worker 通过词典发出错误消息"""
    monkeypatch.setattr(pdf_splitter_module, "FITZ_AVAILABLE", False)
    worker = PDFSplitWorker("in.pdf", "", "pdf", 1, "PNG", 85)
    received = []
    worker.result.connect(lambda ok, msg: received.append((ok, msg)))

    worker.run()  # 直接调用 run，不启动线程

    assert received == [
        (False, t("plugin.pdf_splitter.error.pymupdf_not_installed"))
    ]
    assert received[0][1] == "PyMuPDF 未安装"


def test_worker_messages_format_with_dictionary():
    """worker 完成/处理中/失败消息的占位符与词典一致"""
    assert t("plugin.pdf_splitter.msg.splitting_pages", start=1, end=5) == (
        "正在拆分: 第 1-5 页")
    assert t("plugin.pdf_splitter.msg.converting_page", index=2, total=9) == (
        "正在转换: 第 2/9 页")
    assert t("plugin.pdf_splitter.msg.split_done", count=3) == (
        "拆分完成，共生成 3 个PDF文件")
    assert t("plugin.pdf_splitter.msg.convert_done", count=4) == (
        "转换完成，共生成 4 张图片")
    assert t("plugin.pdf_splitter.error.split_failed", error="boom") == (
        "拆分失败: boom")
