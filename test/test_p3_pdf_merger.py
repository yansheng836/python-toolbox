# -*- encoding: utf-8 -*-
"""
PDF合并插件 i18n 迁移测试

覆盖：zh_CN 词典文本、retranslate_ui 英中切换、
worker 消息走词典（不启动线程）。
"""

import pytest

from common import i18n
from common.i18n import t
from plugins import pdf_merger as pdf_merger_module
from plugins.pdf_merger import PDFMerger, PDFMergeWorker


EN_DICT = {
    "plugin.pdf_merger.name": "PDF Merger",
    "plugin.pdf_merger.description": "Merge multiple PDF files into one",
    "plugin.pdf_merger.card.file_list": "PDF files (in merge order)",
    "plugin.pdf_merger.card.output": "Output settings",
    "plugin.pdf_merger.label.output_file": "Output file:",
    "plugin.pdf_merger.placeholder.output_path": "Choose output file path...",
    "plugin.pdf_merger.button.browse": "Browse",
    "plugin.pdf_merger.button.start_merge": "Start merging",
    "plugin.pdf_merger.filter.add_files": "PDF files (*.pdf);;All files (*.*)",
    "plugin.pdf_merger.dialog.save_pdf": "Save merged PDF",
    "plugin.pdf_merger.filter.save_pdf": "PDF files (*.pdf)",
    "plugin.pdf_merger.dialog.done_title": "Done",
    "plugin.pdf_merger.dialog.error_title": "Error",
    "plugin.pdf_merger.dialog.warning_title": "Warning",
    "plugin.pdf_merger.msg.status_merging": "Merging PDFs...",
    "plugin.pdf_merger.msg.processing": "Processing: {name}",
    "plugin.pdf_merger.msg.merge_done": "Merged {count} files",
    "plugin.pdf_merger.msg.starting": "Merging...",
    "plugin.pdf_merger.error.pymupdf_not_installed": "PyMuPDF is not installed",
    "plugin.pdf_merger.error.merge_failed": "Merge failed: {error}",
    "plugin.pdf_merger.error.pymupdf_missing_status": (
        "Error: PyMuPDF library is not installed, please run: pip install PyMuPDF"
    ),
    "plugin.pdf_merger.error.install_pymupdf": (
        "Please install PyMuPDF first: pip install PyMuPDF"
    ),
    "plugin.pdf_merger.warning.min_files": "Please add at least 2 PDF files!",
}


@pytest.fixture(autouse=True)
def reset_language():
    """每个用例从 zh_CN 开始，避免语言状态泄漏"""
    i18n.set_language("zh_CN")
    yield
    i18n.set_language("zh_CN")


@pytest.fixture
def merger(qapp):
    """构造插件 UI（不启动工作线程）"""
    plugin = PDFMerger.__new__(PDFMerger)
    plugin.icon = "📚"
    plugin.name = "PDF合并"
    plugin.description = "将多个PDF文件合并为一个，支持拖拽排序和调整顺序"
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


def test_texts_use_dictionary_zh(merger):
    """创建后关键文本等于 zh_CN 词典原文"""
    widget = merger.widget

    assert merger.title_label.text() == f"📚 {t('plugin.pdf_merger.name')}"
    assert merger.title_label.text() == "📚 PDF合并"
    assert merger.desc_label.text() == t("plugin.pdf_merger.description")
    assert widget.file_card.title_label.text() == (
        t("plugin.pdf_merger.card.file_list"))
    assert widget.file_card.title_label.text() == "PDF文件列表（顺序即为合并顺序）"
    assert widget.output_card.title_label.text() == (
        t("plugin.pdf_merger.card.output"))
    assert widget.output_card.title_label.text() == "输出设置"
    assert widget.output_file_label.text() == "输出文件:"
    assert widget.output_path.placeholderText() == "选择输出文件路径..."
    assert widget.browse_btn.text() == "浏览"
    assert widget.action_panel.btn.text() == "开始合并"
    assert widget.file_panel.file_filter == "PDF文件 (*.pdf);;所有文件 (*.*)"


def test_retranslate_switches_to_english(merger, en_dict):
    """切到 en 后 retranslate_ui 更新关键文本，切回 zh_CN 恢复"""
    widget = merger.widget

    i18n.set_language("en")
    merger.retranslate_ui()

    assert merger.title_label.text() == "📚 PDF Merger"
    assert merger.desc_label.text() == "Merge multiple PDF files into one"
    assert widget.file_card.title_label.text() == "PDF files (in merge order)"
    assert widget.output_card.title_label.text() == "Output settings"
    assert widget.output_file_label.text() == "Output file:"
    assert widget.output_path.placeholderText() == (
        "Choose output file path...")
    assert widget.browse_btn.text() == "Browse"
    assert widget.action_panel.btn.text() == "Start merging"
    assert widget.file_panel.file_filter == (
        "PDF files (*.pdf);;All files (*.*)")

    i18n.set_language("zh_CN")
    merger.retranslate_ui()

    assert merger.title_label.text() == "📚 PDF合并"
    assert widget.file_card.title_label.text() == "PDF文件列表（顺序即为合并顺序）"
    assert widget.output_file_label.text() == "输出文件:"
    assert widget.output_path.placeholderText() == "选择输出文件路径..."
    assert widget.browse_btn.text() == "浏览"
    assert widget.action_panel.btn.text() == "开始合并"


def test_worker_missing_fitz_message_uses_dictionary(qapp, monkeypatch):
    """FITZ 不可用时 worker 通过词典发出错误消息"""
    monkeypatch.setattr(pdf_merger_module, "FITZ_AVAILABLE", False)
    worker = PDFMergeWorker([], "")
    received = []
    worker.finished.connect(lambda ok, msg: received.append((ok, msg)))

    worker.run()  # 直接调用 run，不启动线程

    assert received == [
        (False, t("plugin.pdf_merger.error.pymupdf_not_installed"))
    ]
    assert received[0][1] == "PyMuPDF 未安装"


def test_worker_messages_format_with_dictionary():
    """worker 完成/处理中/失败消息的占位符与词典一致"""
    assert t("plugin.pdf_merger.msg.merge_done", count=3) == (
        "合并完成，共 3 个文件")
    assert t("plugin.pdf_merger.msg.processing", name="a.pdf") == (
        "正在处理: a.pdf")
    assert t("plugin.pdf_merger.error.merge_failed", error="boom") == (
        "合并失败: boom")
