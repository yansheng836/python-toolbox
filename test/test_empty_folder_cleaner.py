# -*- encoding: utf-8 -*-
"""
空文件夹清理插件的核心行为与 UI 测试
"""

import os

import pytest
from PyQt6.QtWidgets import QTreeWidget, QWidget

import plugins.empty_folder_cleaner as cleaner
from common.directory_drop_line_edit import DirectoryDropLineEdit
from plugins.empty_folder_cleaner import (
    EmptyFolderCleaner,
    EmptyFolderWorker,
    find_empty_folder_candidates,
    remove_empty_folder_tree,
)
from plugins.file_deduplicator import DirectoryDropLineEdit as DeduplicatorDirectoryDropLineEdit
from toolbox import Theme


def test_nested_empty_tree_returns_only_highest_directory(tmp_path):
    root = tmp_path / "root"
    highest = root / "highest"
    (highest / "nested" / "deepest").mkdir(parents=True)

    assert find_empty_folder_candidates(str(root)) == [os.path.abspath(str(highest))]


def test_empty_sibling_is_returned_as_a_separate_candidate(tmp_path):
    root = tmp_path / "root"
    (root / "nested" / "child").mkdir(parents=True)
    sibling = root / "sibling"
    sibling.mkdir(parents=True)

    assert find_empty_folder_candidates(str(root)) == sorted(
        [os.path.abspath(str(root / "nested")), os.path.abspath(str(sibling))]
    )


def test_empty_descendant_under_non_empty_parent_is_still_candidate(tmp_path):
    root = tmp_path / "root"
    parent = root / "parent"
    (parent / "empty-child").mkdir(parents=True)
    (parent / "file.txt").write_text("keep", encoding="utf-8")

    assert find_empty_folder_candidates(str(root)) == [
        os.path.abspath(str(parent / "empty-child"))
    ]


def test_hidden_file_and_symlink_make_directory_non_empty(tmp_path):
    root = tmp_path / "root"
    target = root / "target"
    target.mkdir(parents=True)
    (target / ".hidden").write_text("content", encoding="utf-8")
    link = target / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")

    assert os.path.abspath(str(target)) not in find_empty_folder_candidates(str(root))


def test_root_is_never_returned(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    assert find_empty_folder_candidates(str(root)) == []


def test_deletion_removes_selected_candidate_and_retains_scan_root(tmp_path):
    root = tmp_path / "root"
    selected = root / "selected"
    (selected / "nested" / "deepest").mkdir(parents=True)

    success, message = remove_empty_folder_tree(str(selected))

    assert success is True, message
    assert root.is_dir()
    assert not selected.exists()


def test_deletion_reports_file_added_after_scan_without_removing_file(tmp_path, monkeypatch):
    root = tmp_path / "root"
    selected = root / "selected"
    child = selected / "child"
    child.mkdir(parents=True)
    late_file = child / "appeared-after-scan.txt"
    original_rmdir = cleaner.os.rmdir

    def add_file_before_first_removal(path):
        if os.path.abspath(path) == os.path.abspath(str(child)):
            late_file.write_text("keep me", encoding="utf-8")
        return original_rmdir(path)

    monkeypatch.setattr(cleaner.os, "rmdir", add_file_before_first_removal)

    success, message = remove_empty_folder_tree(str(selected))

    assert success is False
    assert late_file.is_file()
    assert child.is_dir()
    assert selected.is_dir()
    assert str(child) in message or str(selected) in message


def test_worker_rejects_root_and_outside_paths(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    worker = EmptyFolderWorker(str(root), "delete", [str(root), str(outside)])
    deleted = []
    failed = []
    worker.deleted.connect(lambda removed, failures: (deleted.append(removed), failed.append(failures)))

    worker.run()

    assert deleted == [[]]
    assert failed and set(failed[0]) == {os.path.abspath(str(root)), os.path.abspath(str(outside))}
    assert root.exists()
    assert outside.exists()


def test_worker_scan_emits_candidates_and_completion(tmp_path):
    root = tmp_path / "root"
    candidate = root / "candidate"
    candidate.mkdir(parents=True)
    worker = EmptyFolderWorker(str(root), "scan")
    found = []
    finished = []
    worker.folders_found.connect(found.append)
    worker.result.connect(lambda success, message: finished.append((success, message)))

    worker.run()

    assert found == [[os.path.abspath(str(candidate))]]
    assert finished and finished[-1][0] is True


def test_worker_delete_emits_deleted_candidates(tmp_path):
    root = tmp_path / "root"
    candidate = root / "candidate"
    (candidate / "nested").mkdir(parents=True)
    worker = EmptyFolderWorker(str(root), "delete", [str(candidate)])
    deleted = []
    failed = []
    worker.deleted.connect(lambda removed, failures: (deleted.append(removed), failed.append(failures)))

    worker.run()

    assert deleted == [[os.path.abspath(str(candidate))]]
    assert failed == [[]]
    assert not candidate.exists()
    assert root.exists()


def test_shared_directory_input_is_used_by_deduplicator(qapp):
    assert DirectoryDropLineEdit is DeduplicatorDirectoryDropLineEdit
    widget = DirectoryDropLineEdit()

    assert widget.isReadOnly()
    assert widget.acceptDrops()


def test_plugin_builds_ui_and_switches_themes(qapp):
    plugin = EmptyFolderCleaner()
    widget = plugin.get_widget()

    assert isinstance(widget, QWidget)
    assert isinstance(plugin.results_tree, QTreeWidget)
    assert plugin.scan_panel is not None
    assert plugin.delete_panel is not None
    plugin.update_theme(Theme.DARK)
    plugin.update_theme(Theme.LIGHT)


def test_delete_panel_uses_light_theme_error_color(qapp):
    plugin = EmptyFolderCleaner()
    plugin.get_widget()

    plugin.update_theme(Theme.LIGHT)

    style = plugin.delete_panel.btn.styleSheet()
    assert f"stop:0 {Theme.LIGHT['error']}" in style
    assert f"stop:1 {Theme.LIGHT['error_gradient_end']}" in style
