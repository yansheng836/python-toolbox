# -*- encoding: utf-8 -*-
"""
空文件夹清理插件 i18n 迁移测试（P3）

覆盖：
- 中文界面文本来自 zh_CN 词典
- 切换到英文后 retranslate_ui 重放静态文本，切回后恢复
- worker 用户可见消息使用词典
- 删除确认对话框标题与正文使用词典
"""

import pytest

from common import i18n
from plugins.empty_folder_cleaner import EmptyFolderCleaner, EmptyFolderWorker


@pytest.fixture(autouse=True)
def _start_in_zh_cn():
    """每个用例从 zh_CN 开始，结束后恢复原语言"""
    saved = i18n.manager.current_language
    i18n.set_language("zh_CN")
    yield
    i18n.set_language(saved)


@pytest.fixture
def plugin(qapp):
    """构造插件及其界面"""
    instance = EmptyFolderCleaner()
    instance.get_widget()
    return instance


@pytest.fixture
def en_dict():
    """注入最小英文词典，避免依赖 en.json 的完整内容"""
    saved = dict(i18n.manager._dicts)
    i18n.manager._dicts["en"] = {
        "plugin.empty_folder_cleaner.name": "Empty Folder Cleaner",
        "plugin.empty_folder_cleaner.description": "Recursively delete empty folders",
        "plugin.empty_folder_cleaner.card.select_folder": "Select Folder to Scan",
        "plugin.empty_folder_cleaner.placeholder.folder": "Select the root folder...",
        "plugin.empty_folder_cleaner.button.browse": "Browse",
        "plugin.empty_folder_cleaner.button.start_scan": "Start Scan",
        "plugin.empty_folder_cleaner.card.results": "Empty Folders to Delete",
        "plugin.empty_folder_cleaner.column.path": "Folder Path",
        "plugin.empty_folder_cleaner.button.select_all": "Select All",
        "plugin.empty_folder_cleaner.button.deselect_all": "Deselect All",
        "plugin.empty_folder_cleaner.card.delete": "Delete Actions",
        "plugin.empty_folder_cleaner.button.delete_selected": "Delete Selected Folders",
    }
    yield i18n.manager._dicts["en"]
    i18n.manager._dicts.clear()
    i18n.manager._dicts.update(saved)


def test_texts_use_dictionary_zh(plugin):
    """创建后关键文本等于 zh_CN 词典值"""
    widget = plugin.widget

    assert widget.title_label.text() == (
        f"{widget.icon} {i18n.t('plugin.empty_folder_cleaner.name')}"
    )
    assert widget.desc_label.text() == i18n.t(
        "plugin.empty_folder_cleaner.description"
    )
    assert widget.folder_card.title_label.text() == i18n.t(
        "plugin.empty_folder_cleaner.card.select_folder"
    )
    assert widget.folder_display.placeholderText() == i18n.t(
        "plugin.empty_folder_cleaner.placeholder.folder"
    )
    assert widget.browse_btn.text() == i18n.t(
        "plugin.empty_folder_cleaner.button.browse"
    )
    assert widget.scan_panel.btn.text() == i18n.t(
        "plugin.empty_folder_cleaner.button.start_scan"
    )
    assert widget.scan_panel.status_label.text() == i18n.t(
        "plugin.empty_folder_cleaner.msg.status_idle_scan"
    )
    assert widget.results_card.title_label.text() == i18n.t(
        "plugin.empty_folder_cleaner.card.results"
    )
    assert widget.results_tree.headerItem().text(0) == i18n.t(
        "plugin.empty_folder_cleaner.column.path"
    )
    assert widget.stats_label.text() == i18n.t(
        "plugin.empty_folder_cleaner.msg.stats_not_scanned"
    )
    assert widget.delete_card.title_label.text() == i18n.t(
        "plugin.empty_folder_cleaner.card.delete"
    )
    assert widget.delete_panel.btn.text() == i18n.t(
        "plugin.empty_folder_cleaner.button.delete_selected"
    )


def test_retranslate_switches_to_english(plugin, en_dict):
    """切到英文后静态文本变英文，切回 zh_CN 恢复中文"""
    widget = plugin.widget

    i18n.set_language("en")
    plugin.retranslate_ui()

    assert widget.title_label.text() == "🗑️ Empty Folder Cleaner"
    assert widget.desc_label.text() == en_dict[
        "plugin.empty_folder_cleaner.description"
    ]
    assert widget.folder_card.title_label.text() == "Select Folder to Scan"
    assert widget.folder_display.placeholderText() == "Select the root folder..."
    assert widget.browse_btn.text() == "Browse"
    assert widget.scan_panel.btn.text() == "Start Scan"
    assert widget.results_card.title_label.text() == "Empty Folders to Delete"
    assert widget.results_tree.headerItem().text(0) == "Folder Path"
    assert widget.select_all_btn.text() == "Select All"
    assert widget.deselect_all_btn.text() == "Deselect All"
    assert widget.delete_card.title_label.text() == "Delete Actions"
    assert widget.delete_panel.btn.text() == "Delete Selected Folders"

    i18n.set_language("zh_CN")
    plugin.retranslate_ui()

    assert widget.title_label.text() == (
        f"{widget.icon} {i18n.t('plugin.empty_folder_cleaner.name')}"
    )
    assert widget.browse_btn.text() == "浏览"


def test_worker_scan_message_uses_dictionary(tmp_path):
    """扫描完成消息在 emit 时通过词典格式化"""
    root = tmp_path / "root"
    root.mkdir()
    worker = EmptyFolderWorker(str(root), "scan")
    finished = []
    worker.finished.connect(
        lambda success, message: finished.append((success, message))
    )

    worker.run()

    assert finished == [
        (
            True,
            i18n.t(
                "plugin.empty_folder_cleaner.msg.worker_scan_done", count=0
            ),
        )
    ]


def test_worker_error_message_uses_dictionary(tmp_path):
    """不支持的操作走词典错误消息"""
    worker = EmptyFolderWorker(str(tmp_path), "unknown")
    finished = []
    worker.finished.connect(
        lambda success, message: finished.append((success, message))
    )

    worker.run()

    inner = i18n.t(
        "plugin.empty_folder_cleaner.error.unsupported_operation",
        operation="unknown",
    )
    assert finished == [
        (
            False,
            i18n.t(
                "plugin.empty_folder_cleaner.error.operation_failed", error=inner
            ),
        )
    ]


def test_delete_confirmation_uses_dictionary(plugin, monkeypatch, tmp_path):
    """删除确认对话框的标题与正文使用词典"""
    widget = plugin.widget
    captured = {}

    def fake_show_question(parent, title, message):
        captured["title"] = title
        captured["message"] = message
        return False

    monkeypatch.setattr(
        "plugins.empty_folder_cleaner.show_question", fake_show_question
    )

    path = str(tmp_path / "empty")
    widget.show_candidates([path])
    widget.select_all_candidates()
    widget.delete_selected()

    assert captured["title"] == i18n.t(
        "plugin.empty_folder_cleaner.dialog.confirm_delete_title"
    )
    assert captured["message"].startswith(
        i18n.t(
            "plugin.empty_folder_cleaner.msg.confirm_delete_header", count=1
        )
    )
    assert i18n.t(
        "plugin.empty_folder_cleaner.msg.confirm_delete_item",
        index=1,
        path=path,
    ) in captured["message"]
    assert captured["message"].endswith(
        i18n.t("plugin.empty_folder_cleaner.msg.confirm_delete_footer")
    )
    # 用户取消后不应启动删除任务
    assert widget.worker is None
