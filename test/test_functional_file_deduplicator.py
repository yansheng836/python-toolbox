# -*- encoding: utf-8 -*-
"""文件去重插件核心逻辑功能测试（M26）

覆盖哈希去重正确性、三阶段扫描、删除决策 / TOCTOU、symlink / junction 安全、
异常上报等安全关键逻辑。Worker 直接调用 run() 同步执行，不启动线程。
"""

import os
import pytest

from plugins.file_deduplicator import (
    FileDeduplicationWorker,
    FileDeletionWorker,
    _is_within_root,
    _iter_regular_files,
)


def run_scan(worker):
    """同步执行去重扫描 Worker，返回 (results, errors, duplicates, sizes)"""
    results = []
    errors = []
    duplicates = {}
    sizes = {}
    worker.result.connect(lambda ok, msg: results.append((ok, msg)))
    worker.error.connect(errors.append)
    worker.duplicates_found.connect(lambda d: duplicates.update(d))
    worker.sizes_found.connect(lambda s: sizes.update(s))
    worker.run()
    return results, errors, duplicates, sizes


def run_delete(worker):
    """同步执行删除 Worker，返回 (results,)"""
    results = []
    worker.result.connect(lambda ok, msg: results.append((ok, msg)))
    worker.run()
    return results


# ==================== 哈希去重正确性 ====================


def test_finds_true_duplicates_only(tmp_path):
    """只报告内容完全相同的文件；大小不同/内容不同的文件不误判"""
    (tmp_path / "a.txt").write_text("duplicate content", encoding="utf-8")
    (tmp_path / "b.txt").write_text("duplicate content", encoding="utf-8")
    (tmp_path / "c.txt").write_text("different content", encoding="utf-8")

    results, errors, duplicates, _ = run_scan(
        FileDeduplicationWorker(str(tmp_path))
    )

    assert errors == []
    assert results[0][0] is True
    # 只有 a 与 b 是同内容，应归入同一分组
    assert len(duplicates) == 1
    files = sorted(duplicates.values())[0]
    basenames = [os.path.basename(p) for p in files]
    assert "a.txt" in basenames
    assert "b.txt" in basenames
    # c.txt 内容不同，绝不出现
    assert not any("c.txt" in p for files in duplicates.values() for p in files)


def test_same_size_diff_content_not_removed(tmp_path):
    """相同大小但内容不同（快速哈希不同）不应判定为重复"""
    (tmp_path / "x.bin").write_bytes(b"AAAA" * 1000)
    (tmp_path / "y.bin").write_bytes(b"BBBB" * 1000)
    assert os.path.getsize(tmp_path / "x.bin") == os.path.getsize(tmp_path / "y.bin")

    results, _, duplicates, _ = run_scan(
        FileDeduplicationWorker(str(tmp_path))
    )

    assert results[0][0] is True
    assert duplicates == {}


# ==================== 三阶段扫描逻辑 ====================


def test_size_unique_file_excluded(tmp_path):
    """大小唯一的文件在第一阶段就被排除，不进入重复候选"""
    (tmp_path / "unique.txt").write_text("only one of this size", encoding="utf-8")
    results, _, duplicates, _ = run_scan(
        FileDeduplicationWorker(str(tmp_path))
    )
    assert duplicates == {}


def test_duplicates_span_subdirectories(tmp_path):
    """递归扫描能跨子目录识别重复"""
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "sub" / "b.txt").write_text("hello", encoding="utf-8")

    _, _, duplicates, _ = run_scan(FileDeduplicationWorker(str(tmp_path)))

    assert len(duplicates) == 1
    paths = duplicates[list(duplicates)[0]]
    assert len(paths) == 2


# ==================== 删除决策 / TOCTOU ====================


def test_delete_normal(tmp_path):
    """正常删除：文件被移除，统计为 deleted"""
    f = tmp_path / "dup.txt"
    f.write_text("data", encoding="utf-8")

    results = run_delete(
        FileDeletionWorker([str(f)], str(tmp_path), expected_sizes={str(f): 4})
    )

    assert not f.exists()
    assert results[0][0] is True
    from common.i18n import t
    # 无 missing / failed 后缀
    assert t("plugin.file_deduplicator.msg.delete_missing_skipped", count=1) not in results[0][1].split("\n")[0]


def test_delete_missing_counted_separately(tmp_path):
    """文件不存在（missing）不记为 deleted，消息含"已不存在"统计"""
    missing = str(tmp_path / "gone.txt")
    results = run_delete(
        FileDeletionWorker([missing], str(tmp_path))
    )

    from common.i18n import t
    assert results[0][0] is True
    # 消息明确提示有已不存在的文件，而非声称删除成功
    assert t("plugin.file_deduplicator.msg.delete_missing_skipped", count=1) in results[0][1]


def test_delete_toctou_sizes_mismatch_skipped(tmp_path):
    """扫描后大小已变化的文件被跳过并计入失败（TOCTOU 防护）"""
    f = tmp_path / "changed.txt"
    f.write_text("original", encoding="utf-8")

    from common.i18n import t
    results = run_delete(
        FileDeletionWorker(
            [str(f)], str(tmp_path), expected_sizes={str(f): 9999}
        )
    )
    assert f.exists()  # 不应被删除
    assert results[0][0] is True
    # 失败明细含"内容已变化"说明
    assert t("plugin.file_deduplicator.msg.file_changed_skipped") in results[0][1]


def test_delete_skips_outside_root(tmp_path):
    """越界文件（不在扫描根目录内）拒绝删除并计入失败"""
    outside = tmp_path.parent / f"outside_dup_{os.getpid()}.txt"
    outside.write_text("data", encoding="utf-8")
    try:
        from common.i18n import t
        results = run_delete(
            FileDeletionWorker([str(outside)], str(tmp_path))
        )
        assert outside.exists()  # 拒绝删除
        assert results[0][0] is True
        assert t("plugin.file_deduplicator.msg.outside_root") in results[0][1]
    finally:
        outside.unlink(missing_ok=True)


def test_delete_skips_symlink_file(tmp_path):
    """链接文件被拒绝删除，防止误删真实目标"""
    target = tmp_path / "real.txt"
    target.write_text("real data", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        os.symlink(str(target), str(link))
    except (OSError, NotImplementedError):
        pytest.skip("当前平台不支持创建符号链接")

    from common.i18n import t
    results = run_delete(
        FileDeletionWorker([str(link)], str(tmp_path))
    )
    assert os.path.islink(link)  # 链接本身不应被删除
    assert target.exists()  # 真实目标不得被动到
    assert results[0][0] is True
    assert t("plugin.file_deduplicator.msg.is_link_skipped") in results[0][1]


# ==================== symlink / junction 安全 ====================


def test_scan_skips_symlink_file(tmp_path):
    """扫描不把符号链接文件纳入去重"""
    target = tmp_path / "real.txt"
    target.write_text("data", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        os.symlink(str(target), str(link))
    except (OSError, NotImplementedError):
        pytest.skip("当前平台不支持创建符号链接")

    _, _, duplicates, _ = run_scan(FileDeduplicationWorker(str(tmp_path)))
    # 唯一真实文件不构成重复
    assert duplicates == {}


def test_scan_does_not_follow_symlink_dir(tmp_path):
    """扫描不进入符号链接指向的目录（防止越界/死循环）"""
    outside_root = tmp_path.parent / f"dedup_test_outer_{os.getpid()}"
    outside_root.mkdir(exist_ok=True)
    try:
        (outside_root / "dup.txt").write_text("same", encoding="utf-8")
        inside = tmp_path / "inner"
        inside.mkdir()
        (inside / "a.txt").write_text("same", encoding="utf-8")
        linkdir = tmp_path / "linkdir"
        try:
            os.symlink(str(outside_root), str(linkdir))
        except (OSError, NotImplementedError):
            pytest.skip("当前平台不支持创建符号链接")

        files = list(_iter_regular_files(str(tmp_path)))
        # 不应包含经符号链接进入的外部目录里的文件
        assert not any(
            os.path.normpath(f).startswith(str(outside_root)) for f in files
        )
        # 应包含真实的内部文件
        assert any("a.txt" in f for f in files)
    finally:
        import shutil
        shutil.rmtree(outside_root, ignore_errors=True)


def test_is_within_root_check(tmp_path):
    """_is_within_root 校验：根内 True，越界 False"""
    inside = tmp_path / "a.txt"
    inside.write_text("x", encoding="utf-8")
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("y", encoding="utf-8")

    assert _is_within_root(str(tmp_path), str(inside)) is True
    assert _is_within_root(str(tmp_path), str(outside)) is False
    # 目标等于根目录本身也应拒绝
    assert _is_within_root(str(tmp_path), str(tmp_path)) is False


# ==================== 异常 / 权限 ====================


def test_unreadable_file_reports_error_not_silent(tmp_path, monkeypatch):
    """不可读文件通过 error 信号上报，而不是被无声排除"""
    (tmp_path / "a.txt").write_text("same", encoding="utf-8")
    (tmp_path / "b.txt").write_text("same", encoding="utf-8")

    real_open = open

    def failing_open(path, *args, **kwargs):
        if str(path).endswith("a.txt"):
            raise OSError("permission denied")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", failing_open)
    results, errors, duplicates, _ = run_scan(
        FileDeduplicationWorker(str(tmp_path))
    )

    assert errors  # error 信号被触发（非死代码）
    assert results  # 有完成结果