# -*- encoding: utf-8 -*-
"""文件去重插件 i18n 迁移测试：词典文本、retranslate_ui、组合框稳定 data、结果树"""

import pytest

from PyQt6.QtCore import Qt

from common import i18n
from common.i18n import t
from plugins.file_deduplicator import FileDeduplicationWorker, FileDeduplicator


EN_DICT = {
    "plugin.file_deduplicator.name": "File Deduplicator",
    "plugin.file_deduplicator.description": "Find duplicate files by content hash",
    "plugin.file_deduplicator.card.select_folder": "Select folder to scan",
    "plugin.file_deduplicator.card.results": "Duplicate files",
    "plugin.file_deduplicator.card.deletion_rules": "Deletion rules",
    "plugin.file_deduplicator.column.file_info": "File info",
    "plugin.file_deduplicator.column.size": "Size",
    "plugin.file_deduplicator.column.created": "Created",
    "plugin.file_deduplicator.column.modified": "Modified",
    "plugin.file_deduplicator.tree.group_label": (
        "Duplicate group: {hash}... ({count} files)"),
    "plugin.file_deduplicator.placeholder.folder": "Choose a folder to scan...",
    "plugin.file_deduplicator.button.browse": "Browse",
    "plugin.file_deduplicator.button.scan": "Start scan",
    "plugin.file_deduplicator.button.select_all": "Select all",
    "plugin.file_deduplicator.button.deselect_all": "Deselect all",
    "plugin.file_deduplicator.button.expand": "Expand",
    "plugin.file_deduplicator.button.collapse": "Collapse",
    "plugin.file_deduplicator.button.sort_by_rule": "Sort by rule",
    "plugin.file_deduplicator.button.delete_duplicates": "Delete duplicates",
    "plugin.file_deduplicator.label.rule": "Deletion rule:",
    "plugin.file_deduplicator.label.auto_rescan": "Rescan after deletion",
    "plugin.file_deduplicator.combo.rule_ctime_asc": "By creation time (oldest first)",
    "plugin.file_deduplicator.combo.rule_ctime_desc": "By creation time (newest first)",
    "plugin.file_deduplicator.combo.rule_name_asc": "By file name (A to Z)",
    "plugin.file_deduplicator.combo.rule_name_desc": "By file name (Z to A)",
    "plugin.file_deduplicator.combo.rule_smart_asc": "Smart copy detection (oldest first)",
    "plugin.file_deduplicator.combo.rule_smart_desc": "Smart copy detection (newest first)",
}


@pytest.fixture(autouse=True)
def reset_language():
    """每个用例从 zh_CN 开始，避免语言状态泄漏"""
    i18n.set_language("zh_CN")
    yield
    i18n.set_language("zh_CN")


@pytest.fixture
def dedup(qapp):
    """构造插件 UI（不启动工作线程）"""
    plugin = FileDeduplicator.__new__(FileDeduplicator)
    plugin.icon = "🧹"
    plugin.name = "文件去重"
    plugin.description = ""
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


def _header_texts(widget):
    tree = widget.results_tree
    header = tree.headerItem()
    return [header.text(i) for i in range(tree.columnCount())]


def test_texts_use_dictionary_zh(dedup):
    """创建后关键文本等于 zh_CN 词典原文"""
    widget = dedup.widget

    assert dedup.title_label.text() == f"🧹 {t('plugin.file_deduplicator.name')}"
    assert dedup.title_label.text() == "🧹 文件去重"
    assert dedup.desc_label.text() == t("plugin.file_deduplicator.description")
    assert widget.folder_card.title_label.text() == (
        t("plugin.file_deduplicator.card.select_folder"))
    assert widget.results_card.title_label.text() == (
        t("plugin.file_deduplicator.card.results"))
    assert widget.deletion_card.title_label.text() == (
        t("plugin.file_deduplicator.card.deletion_rules"))
    assert widget.rule_label.text() == t("plugin.file_deduplicator.label.rule")
    assert widget.auto_rescan_label.text() == (
        t("plugin.file_deduplicator.label.auto_rescan"))
    assert widget.folder_display.placeholderText() == (
        t("plugin.file_deduplicator.placeholder.folder"))
    assert widget.browse_btn.text() == t("plugin.file_deduplicator.button.browse")
    assert widget.scan_panel.btn.text() == t("plugin.file_deduplicator.button.scan")
    assert widget.select_all_btn.text() == (
        t("plugin.file_deduplicator.button.select_all"))
    assert widget.deselect_all_btn.text() == (
        t("plugin.file_deduplicator.button.deselect_all"))
    assert widget.sort_by_rule_btn.text() == (
        t("plugin.file_deduplicator.button.sort_by_rule"))
    assert widget.delete_panel.btn.text() == (
        t("plugin.file_deduplicator.button.delete_duplicates"))

    assert _header_texts(widget) == [
        t("plugin.file_deduplicator.column.file_info"),
        t("plugin.file_deduplicator.column.size"),
        t("plugin.file_deduplicator.column.created"),
        t("plugin.file_deduplicator.column.modified"),
    ]


def test_retranslate_switches_to_english(dedup, en_dict):
    """切到 en 后 retranslate_ui 更新关键文本，切回 zh_CN 恢复"""
    widget = dedup.widget

    i18n.set_language("en")
    dedup.retranslate_ui()

    assert dedup.title_label.text() == "🧹 File Deduplicator"
    assert dedup.desc_label.text() == "Find duplicate files by content hash"
    assert widget.folder_card.title_label.text() == "Select folder to scan"
    assert widget.results_card.title_label.text() == "Duplicate files"
    assert widget.deletion_card.title_label.text() == "Deletion rules"
    assert widget.rule_label.text() == "Deletion rule:"
    assert widget.auto_rescan_label.text() == "Rescan after deletion"
    assert widget.folder_display.placeholderText() == (
        "Choose a folder to scan...")
    assert widget.browse_btn.text() == "Browse"
    assert widget.scan_panel.btn.text() == "Start scan"
    assert widget.select_all_btn.text() == "Select all"
    assert widget.deselect_all_btn.text() == "Deselect all"
    assert widget.sort_by_rule_btn.text() == "Sort by rule"
    assert widget.delete_panel.btn.text() == "Delete duplicates"
    assert widget.toggle_expand_btn.text() == "Expand"
    assert _header_texts(widget) == [
        "File info", "Size", "Created", "Modified",
    ]

    i18n.set_language("zh_CN")
    dedup.retranslate_ui()

    assert dedup.title_label.text() == "🧹 文件去重"
    assert widget.folder_card.title_label.text() == (
        t("plugin.file_deduplicator.card.select_folder"))
    assert widget.rule_label.text() == t("plugin.file_deduplicator.label.rule")
    assert widget.browse_btn.text() == t("plugin.file_deduplicator.button.browse")
    assert _header_texts(widget)[0] == (
        t("plugin.file_deduplicator.column.file_info"))


def test_combo_keeps_stable_data(dedup, en_dict):
    """组合框每项 data 非空；切换语言后 currentData 不变"""
    combo = dedup.widget.rule_combo

    for i in range(combo.count()):
        assert combo.itemData(i) is not None

    assert combo.currentData() == 0
    assert combo.currentText() == (
        t("plugin.file_deduplicator.combo.rule_ctime_asc"))

    i18n.set_language("en")
    assert combo.currentData() == 0
    assert combo.currentText() == EN_DICT[
        "plugin.file_deduplicator.combo.rule_ctime_asc"]

    i18n.set_language("zh_CN")
    assert combo.currentData() == 0
    assert combo.currentText() == (
        t("plugin.file_deduplicator.combo.rule_ctime_asc"))


def test_tree_labels_use_dictionary_and_userrole(dedup, tmp_path):
    """分组标签与保留/删除前缀走词典，路径仍存 UserRole（不解析显示文本）"""
    widget = dedup.widget
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("same content", encoding="utf-8")
    second.write_text("same content", encoding="utf-8")

    widget.duplicates = {"abcdef123456": [str(first), str(second)]}
    widget.rule_combo.setCurrentIndex(widget.rule_combo.findData(2))
    widget.show_duplicates(widget.duplicates)

    tree = widget.results_tree
    parent = tree.topLevelItem(0)
    assert parent.text(0) == t(
        "plugin.file_deduplicator.tree.group_label",
        hash="abcdef12", count=2,
    )
    assert parent.child(0).text(0) == t(
        "plugin.file_deduplicator.tree.keep", path=str(first))
    assert parent.child(1).text(0) == t(
        "plugin.file_deduplicator.tree.delete", path=str(second))
    assert parent.child(0).data(0, Qt.ItemDataRole.UserRole) == str(first)
    assert parent.child(1).data(0, Qt.ItemDataRole.UserRole) == str(second)


def test_retranslate_preserves_checked_and_expanded(dedup, en_dict, tmp_path):
    """语言切换重建结果树时保留用户勾选与展开状态"""
    widget = dedup.widget
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("same content", encoding="utf-8")
    second.write_text("same content", encoding="utf-8")

    widget.duplicates = {"abcdef123456": [str(first), str(second)]}
    widget.show_duplicates(widget.duplicates)
    tree = widget.results_tree
    parent = tree.topLevelItem(0)
    parent.setCheckState(0, Qt.CheckState.Checked)
    parent.setExpanded(False)

    i18n.set_language("en")
    dedup.retranslate_ui()

    rebuilt = tree.topLevelItem(0)
    assert rebuilt.checkState(0) == Qt.CheckState.Checked
    assert not rebuilt.isExpanded()
    assert rebuilt.text(0) == EN_DICT[
        "plugin.file_deduplicator.tree.group_label"].format(
            hash="abcdef12", count=2)


def test_worker_messages_use_dictionary(qapp, tmp_path):
    """worker 扫描消息通过词典发出（直接调用 run，不启动线程）"""
    worker = FileDeduplicationWorker(str(tmp_path))
    statuses = []
    results = []
    worker.status.connect(statuses.append)
    worker.result.connect(lambda ok, msg: results.append((ok, msg)))

    worker.run()

    assert statuses[0] == t("plugin.file_deduplicator.msg.scanning_folder")
    assert results == [
        (True, t("plugin.file_deduplicator.msg.scan_done", count=0))
    ]


def test_message_keys_format_with_dictionary():
    """worker / 提示消息的占位符与词典一致"""
    assert t("plugin.file_deduplicator.msg.found_files", count=3) == (
        "找到 3 个文件，按大小分组...")
    assert t(
        "plugin.file_deduplicator.error.read_failed", path="a.txt", error="boom"
    ) == "无法读取文件 a.txt: boom"
    assert t(
        "plugin.file_deduplicator.msg.scanned_progress", count=2, total=5
    ) == "已扫描 2/5 个文件..."
    assert t("plugin.file_deduplicator.error.scan_failed", error="boom") == (
        "扫描失败: boom")
