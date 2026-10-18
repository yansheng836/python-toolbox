# -*- encoding: utf-8 -*-
"""空文件夹清理插件核心逻辑功能测试（M26）

覆盖递归空目录识别、根目录保留、非空目录不入选、安全删除（只 rmdir 不删文件）、
越界/根目录保护、Worker 扫描与删除结果。直接调用 Worker.run() 或纯函数，
不启动线程、不创建 GUI 窗口。
"""

import os

from plugins.empty_folder_cleaner import (
    EmptyFolderWorker,
    find_empty_folder_candidates,
    _is_safe_candidate,
    remove_empty_folder_tree,
)


def run_worker(worker):
    """同步执行 Worker，返回 (results, folders_found, deleted)"""
    results = []
    found = []
    deleted = []
    worker.result.connect(lambda ok, msg: results.append((ok, msg)))
    worker.folders_found.connect(lambda items: found.extend(items))
    worker.deleted.connect(lambda ok, bad: deleted.append((list(ok), list(bad))))
    worker.run()
    return results, found, deleted


# ==================== 空目录识别 ====================


def test_finds_nested_empty_dirs(tmp_path):
    """识别嵌套空目录，返回最上层候选"""
    empty_tree = tmp_path / "empty_tree"
    (empty_tree / "a" / "b").mkdir(parents=True)
    candidates = find_empty_folder_candidates(str(tmp_path))

    # 整棵空树的最高层只报 empty_tree
    assert candidates == [str(empty_tree)]


def test_non_empty_dir_not_candidate(tmp_path):
    """含文件的目录不是空目录候选"""
    d = tmp_path / "has_file"
    d.mkdir()
    (d / "note.txt").write_text("x", encoding="utf-8")
    assert find_empty_folder_candidates(str(tmp_path)) == []


def test_empty_child_of_nonempty_parent_is_candidate(tmp_path):
    """非空目录内部的空子目录可作为候选"""
    parent = tmp_path / "parent"
    (parent / "empty_child").mkdir(parents=True)
    (parent / "file.txt").write_text("x", encoding="utf-8")

    candidates = find_empty_folder_candidates(str(tmp_path))
    assert candidates == [str(parent / "empty_child")]


def test_root_never_returned(tmp_path):
    """扫描根目录本身始终保留，不进入候选"""
    (tmp_path / "sub").mkdir()
    candidates = find_empty_folder_candidates(str(tmp_path))
    assert str(tmp_path) not in candidates
    assert candidates == [str(tmp_path / "sub")]


def test_hidden_items_treated_as_content(tmp_path):
    """隐藏项视为内容，目录不判空"""
    d = tmp_path / "with_hidden"
    d.mkdir()
    (d / ".hidden").write_text("x", encoding="utf-8")
    assert find_empty_folder_candidates(str(tmp_path)) == []


# ==================== 安全删除 ====================


def test_remove_empty_tree_success(tmp_path):
    """删除空目录树：整棵被移除"""
    tree = tmp_path / "tree"
    (tree / "x" / "y").mkdir(parents=True)
    success, message = remove_empty_folder_tree(str(tree))
    assert success
    assert not tree.exists()


def test_remove_never_deletes_files(tmp_path):
    """目录中若出现文件，删除失败且文件保留（只 rmdir 不删文件）"""
    d = tmp_path / "suddenly_nonempty"
    d.mkdir()
    (d / "keep.txt").write_text("important", encoding="utf-8")

    success, message = remove_empty_folder_tree(str(d))
    assert not success
    assert (d / "keep.txt").exists()  # 文件绝不能被删


def test_remove_missing_dir_is_success(tmp_path):
    """目标已不存在时视为成功（目标已达成）"""
    success, _ = remove_empty_folder_tree(str(tmp_path / "already_gone"))
    assert success


def test_is_safe_candidate_rejects_root_and_outside(tmp_path):
    """安全校验拒绝根目录自身与根外路径"""
    inside = tmp_path / "in"
    inside.mkdir()
    outside = tmp_path.parent / f"out_{os.getpid()}"
    outside.mkdir(exist_ok=True)
    try:
        assert _is_safe_candidate(str(tmp_path), str(inside)) is True
        assert _is_safe_candidate(str(tmp_path), str(tmp_path)) is False
        assert _is_safe_candidate(str(tmp_path), str(outside)) is False
    finally:
        outside.rmdir()


# ==================== Worker 扫描 / 删除 ====================


def test_worker_scan_reports_candidates(tmp_path):
    """扫描 Worker 经 folders_found 上报候选目录"""
    (tmp_path / "e1").mkdir()
    (tmp_path / "e2").mkdir()
    results, found, _ = run_worker(EmptyFolderWorker(str(tmp_path), "scan"))

    assert results[0][0] is True
    assert sorted(found) == sorted([str(tmp_path / "e1"), str(tmp_path / "e2")])


def test_worker_delete_removes_only_checked(tmp_path):
    """删除 Worker 只删除传入的候选，不影响其它目录"""
    to_delete = tmp_path / "to_delete"
    keep = tmp_path / "keep_empty"
    to_delete.mkdir()
    keep.mkdir()

    results, _, deleted = run_worker(
        EmptyFolderWorker(str(tmp_path), "delete", [str(to_delete)])
    )

    assert results[0][0] is True
    assert not to_delete.exists()
    assert keep.exists()  # 未传入的目录保留
    ok, bad = deleted[0]
    assert str(to_delete) in ok
    assert bad == []


def test_worker_delete_rejects_outside_candidate(tmp_path):
    """删除 Worker 拒绝根目录之外的候选（安全校验）"""
    outside = tmp_path.parent / f"outside_empty_{os.getpid()}"
    outside.mkdir(exist_ok=True)
    try:
        results, _, deleted = run_worker(
            EmptyFolderWorker(str(tmp_path), "delete", [str(outside)])
        )
        assert outside.exists()  # 越界目录未被删除
        ok, bad = deleted[0]
        assert ok == []
        assert str(outside) in bad
        assert results[0][0] is False  # 有失败
    finally:
        outside.rmdir()


def test_worker_delete_partial_nonempty_failure(tmp_path):
    """删除时若目录已变为非空，报告失败且保留文件"""
    d = tmp_path / "raced"
    d.mkdir()
    (d / "new_file.txt").write_text("x", encoding="utf-8")

    results, _, deleted = run_worker(
        EmptyFolderWorker(str(tmp_path), "delete", [str(d)])
    )
    assert d.exists()
    assert (d / "new_file.txt").exists()
    ok, bad = deleted[0]
    assert ok == []
    assert results[0][0] is False