# 空文件夹清理插件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一个独立 PyQt6 插件，扫描用户选定根目录下完全为空的目录，按最上层候选展示并在确认后安全递归删除，同时保留根目录和所有目录内容。

**Architecture:** 在 `plugins/empty_folder_cleaner.py` 中集中实现目录扫描/删除算法、`BaseWorker` 后台线程和插件 UI。扫描将“只包含空子目录的目录树”视为递归为空，并将连续空目录压缩为最上层候选；删除阶段自底向上仅调用 `os.rmdir`，因此不会递归删除文件。插件通过 `config.py` 和 `toolbox.spec` 接入现有动态加载、主题和打包体系。

**Tech Stack:** Python 3、PyQt6、pytest、pytest-qt、`os.scandir`/`os.rmdir`、现有 `ToolPlugin`/`BaseWorker`/`ActionPanel`/`Theme` 组件。

## Global Constraints

- 选择的根目录始终保留，即使它本身为空。
- 目录内任何条目都表示非空，包括点开头的隐藏文件、隐藏目录和符号链接；扫描不跟随符号链接。
- 多层连续空目录只展示最上层候选，删除时递归移除其空子目录。
- 删除阶段只使用 `os.rmdir`，不删除文件；扫描完成后新增文件时必须保留文件并报告目录删除失败。
- 长时间扫描和删除必须运行在 `BaseWorker` 线程中，不能阻塞 Qt 主线程。
- 所有用户可读文本优先使用 `SelectableLabel`；所有颜色来自 `Theme`；布局使用可扩展策略，不在插件根布局末尾添加 `addStretch()`。
- 修改的 Python 文件必须使用 UTF-8、LF 行尾、模块编码行和模块 docstring，并运行 `python -m py_compile` 与导入检查。
- Windows 路径扫描必须跳过保留设备名；文件删除前检查存在性；目录遍历和删除异常必须报告到结果而不是静默吞掉。
- 只提交与本功能相关的文件；不修改或删除现有用户文件。

---

### Task 1: 建立可测试的目录扫描与删除核心逻辑

**Files:**
- Create: `common/directory_drop_line_edit.py`
- Create: `plugins/empty_folder_cleaner.py`
- Modify: `plugins/file_deduplicator.py`
- Create: `test/test_empty_folder_cleaner.py`

**Interfaces:**
- Produces the shared `DirectoryDropLineEdit(QLineEdit)` in `common/directory_drop_line_edit.py`; it emits `directory_dropped(str)` for local directories and is imported by both directory-based plugins.
- Produces `find_empty_folder_candidates(root_path: str) -> list[str]`，返回根目录内部可删除的最上层递归空目录绝对路径，结果稳定按路径排序；根目录不返回。
- Produces `remove_empty_folder_tree(folder_path: str) -> tuple[bool, str]`，只尝试删除仍为空的目录树，返回成功标志和可展示的结果文本；目录中出现文件或其他条目时不删除任何条目。
- Produces `EmptyFolderWorker(BaseWorker)`，构造函数接收 `root_path: str`、`operation: str`（`"scan"` 或 `"delete"`）以及 `folder_paths: list[str] | None = None`；扫描通过 `folders_found = pyqtSignal(list)` 发出候选，删除通过 `deleted = pyqtSignal(list, list)` 发出成功/失败路径。

- [ ] **Step 1: Write failing tests for scanning semantics**

```python
from pathlib import Path

from plugins.empty_folder_cleaner import find_empty_folder_candidates


def test_returns_only_top_level_empty_folder(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    nested = root / "outer" / "inner"
    nested.mkdir(parents=True)
    (root / "empty").mkdir()

    assert find_empty_folder_candidates(str(root)) == [
        str(root / "empty"),
        str(root / "outer"),
    ]


def test_hidden_file_and_symlink_make_directory_non_empty(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    hidden_file_dir = root / "hidden-file"
    hidden_file_dir.mkdir()
    (hidden_file_dir / ".keep").write_text("x", encoding="utf-8")
    link_dir = root / "link-entry"
    link_dir.mkdir()
    target = root / "target"
    target.mkdir()
    (link_dir / "target-link").symlink_to(target, target_is_directory=True)

    candidates = find_empty_folder_candidates(str(root))

    assert str(hidden_file_dir) not in candidates
    assert str(link_dir) not in candidates
    assert str(target) in candidates


def test_root_is_never_a_candidate(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    assert find_empty_folder_candidates(str(root)) == []
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest -q test/test_empty_folder_cleaner.py`

Expected: collection fails because `plugins.empty_folder_cleaner` and `find_empty_folder_candidates` do not exist yet.

- [ ] **Step 3: Write failing tests for safe deletion semantics**

```python
from plugins.empty_folder_cleaner import remove_empty_folder_tree


def test_removes_nested_empty_directories_without_removing_parent_root(tmp_path):
    root = tmp_path / "root"
    target = root / "outer" / "inner"
    target.mkdir(parents=True)

    success, message = remove_empty_folder_tree(str(target))

    assert success is True
    assert not target.exists()
    assert not (root / "outer").exists()
    assert root.exists()
    assert "成功" in message


def test_does_not_remove_file_when_tree_becomes_non_empty(tmp_path):
    root = tmp_path / "root"
    target = root / "outer"
    target.mkdir(parents=True)
    (target / "new.txt").write_text("keep", encoding="utf-8")

    success, message = remove_empty_folder_tree(str(target))

    assert success is False
    assert (target / "new.txt").exists()
    assert target.exists()
    assert "非空" in message or "失败" in message
```

- [ ] **Step 4: Run the focused tests to confirm the second failure**

Run: `pytest -q test/test_empty_folder_cleaner.py`

Expected: import or attribute failures for the deletion API.

- [ ] **Step 5: Implement the minimal core algorithms**

Implement `find_empty_folder_candidates` with `os.scandir` recursion. Treat a directory as recursively empty when it contains no files, symlinks, or other non-directory entries and every real child directory is recursively empty; a directory containing only empty child directories is therefore a candidate. Inspect every `DirEntry` without following links, recurse only into real directories, and add only the highest directory in each recursively empty tree. Normalize the root with `os.path.abspath`, reject a non-directory root with a `ValueError`, and skip entries whose basename without extension is in `WINDOWS_RESERVED_NAMES` before any open/stat operation.

Implement `remove_empty_folder_tree` by collecting the target and real child directories bottom-up with `os.walk(..., topdown=False, followlinks=False)`, then calling `os.rmdir` only on each path. Never call `shutil.rmtree` or remove files. Continue after a child fails so independent empty descendants can still be removed, record every failed path and return a message that includes them; an `OSError` is meaningful because it represents a permission, lock, or newly non-empty directory condition.

- [ ] **Step 6: Run the focused tests and verify they pass**

Run: `pytest -q test/test_empty_folder_cleaner.py`

Expected: all core scanning and deletion tests pass.

- [ ] **Step 7: Run syntax and import checks for the new module**

Run: `python -m py_compile plugins/empty_folder_cleaner.py` and `python -c "from plugins.empty_folder_cleaner import find_empty_folder_candidates, remove_empty_folder_tree"`

Expected: both commands exit with code 0.

- [ ] **Step 8: Commit the core logic and tests**

```bash
git add plugins/empty_folder_cleaner.py test/test_empty_folder_cleaner.py
git commit -m "feat: 添加空文件夹扫描与安全删除逻辑"
```

---

### Task 2: Add worker signals and plugin UI

**Files:**
- Modify: `plugins/empty_folder_cleaner.py`
- Modify: `test/test_empty_folder_cleaner.py`

**Interfaces:**
- Consumes `find_empty_folder_candidates` and `remove_empty_folder_tree` from Task 1.
- Produces `EmptyFolderCleanerWidget(QWidget)` with `folder_display`, `scan_panel`, `results_tree`, `delete_panel`, and `selected_folder` attributes; `EmptyFolderCleaner(ToolPlugin)` delegates `create_ui()` and `update_theme()` to the widget.

- [ ] **Step 1: Write failing worker and UI tests**

```python
from PyQt6.QtWidgets import QTreeWidget, QWidget

from plugins.empty_folder_cleaner import EmptyFolderCleaner, EmptyFolderWorker


def test_worker_scan_emits_candidates(tmp_path, qtbot):
    root = tmp_path / "root"
    (root / "empty" / "nested").mkdir(parents=True)
    worker = EmptyFolderWorker(str(root), "scan")
    found = []
    worker.folders_found.connect(found.append)
    with qtbot.waitSignal(worker.finished, timeout=3000):
        worker.start()
    assert found == [[str(root / "empty")]]


def test_plugin_builds_expected_ui(qapp):
    plugin = EmptyFolderCleaner()
    widget = plugin.get_widget()
    assert isinstance(widget, QWidget)
    assert isinstance(plugin.results_tree, QTreeWidget)
    assert plugin.scan_panel is not None
    assert plugin.delete_panel is not None
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run: `pytest -q test/test_empty_folder_cleaner.py::test_worker_scan_emits_candidates test/test_empty_folder_cleaner.py::test_plugin_builds_expected_ui`

Expected: failures because worker/UI classes and attributes are not implemented.

- [ ] **Step 3: Implement worker behavior**

`EmptyFolderWorker.run()` must emit status text, run the selected operation, emit `progress` as directories are processed, emit `folders_found` for scans, emit `deleted` with separate success/failure lists for deletes, and finish with `finished(True, message)` unless the root/operation is invalid or an unexpected scan error occurs. Keep exception handling narrow and print/report caught errors through the standard `finished` message.

- [ ] **Step 4: Implement directory selection and result UI**

Add a read-only `QLineEdit` subclass with `directory_dropped` signal, matching the existing directory-drop behavior. The widget must provide a browse button, a scan `ActionPanel`, a multi-selection `QTreeWidget`/list result view containing only candidate paths, select-all and clear-selection controls, and a delete `ActionPanel`. The selected root is set by browse/drop and scanning starts explicitly or after selection according to existing plugin conventions.

Use `SelectableLabel` for title, description, labels, and status text. Use `Theme` in `apply_theme`, `get_lineedit_style` where applicable, and responsive `QSizePolicy.Policy.Expanding` for the result list. Do not add a layout-ending stretch. Disable delete until a scan has produced candidates; disable scan/delete while their worker runs.

- [ ] **Step 5: Implement confirmation and deletion UI flow**

On delete, gather checked paths, show a confirmation using `show_question`, run a delete worker, update progress/status, then clear or refresh the result list. Present successful and failed counts and up to five failed paths via `show_info` or `show_error` as appropriate. If the directory became non-empty after scanning, leave it in place and show its failure path.

- [ ] **Step 6: Run focused worker and UI tests**

Run: `pytest -q test/test_empty_folder_cleaner.py`

Expected: all core, worker, and UI tests pass.

- [ ] **Step 7: Run Python validation**

Run: `python -m py_compile plugins/empty_folder_cleaner.py` and `python -m pyflakes plugins/empty_folder_cleaner.py`.

Expected: no syntax errors and no undefined-name diagnostics.

- [ ] **Step 8: Commit the worker and UI**

```bash
git add plugins/empty_folder_cleaner.py test/test_empty_folder_cleaner.py
git commit -m "feat: 添加空文件夹清理界面和后台任务"
```

---

### Task 3: Register the plugin and package it

**Files:**
- Modify: `config.py:20-94`
- Modify: `toolbox.spec:74-82`
- Modify: `test/test_plugins.py:21-35`

**Interfaces:**
- Consumes `EmptyFolderCleaner` from `plugins.empty_folder_cleaner`.
- Produces a registered plugin named `空文件夹清理` with a unique order value after `文件去重` and a hidden import entry for PyInstaller.

- [ ] **Step 1: Extend the plugin registration test**

Add `"空文件夹清理"` to `expected_names` in `test/test_plugins.py` and add an assertion that `plugins.empty_folder_cleaner` occurs in `toolbox.spec` hidden imports.

- [ ] **Step 2: Run the registration tests and verify the expected failure**

Run: `pytest -q test/test_plugins.py::TestPluginLoading::test_specific_plugins_present`

Expected: failure because the configuration does not yet load the new plugin.

- [ ] **Step 3: Register the plugin in `config.py`**

Add a `PLUGIN_MODULES` entry with name `空文件夹清理`, a folder-cleaning icon, a description that states it finds and removes completely empty nested folders, a unique order after `文件去重`, module `plugins.empty_folder_cleaner`, and class `EmptyFolderCleaner`. Keep `FEATURE_MODULES` derived from this list.

- [ ] **Step 4: Add the PyInstaller hidden import**

Add `'plugins.empty_folder_cleaner'` beside the other dynamically loaded plugin modules in `toolbox.spec`.

- [ ] **Step 5: Run registration and packaging checks**

Run: `pytest -q test/test_plugins.py`, `python -m py_compile config.py`, and `python verify_packaging.py`.

Expected: plugin loading/UI/theme tests pass, config compiles, and packaging verification reports the new module as present.

- [ ] **Step 6: Commit registration changes**

```bash
git add config.py toolbox.spec test/test_plugins.py
git commit -m "feat: 注册空文件夹清理插件"
```

---

### Task 4: Full verification and UI smoke test

**Files:**
- Modify only files needed to fix verified failures from Tasks 1–3.

- [ ] **Step 1: Run the complete pytest suite using the repository's actual test directory**

Run: `pytest -q test`

Expected: all collected tests pass; if collection remains empty, record the repository pytest discovery issue and run each `test/test_*.py` file through the configured test runner.

- [ ] **Step 2: Run syntax checks across all modified Python files**

Run: `python -m py_compile plugins/empty_folder_cleaner.py test/test_empty_folder_cleaner.py config.py test/test_plugins.py`.

Expected: all commands exit with code 0 and no `IndentationError`/`SyntaxError` output.

- [ ] **Step 3: Run static import checks**

Run: `python -c "from plugins.empty_folder_cleaner import EmptyFolderCleaner, EmptyFolderWorker; from config import PLUGIN_MODULES"` and `python verify_packaging.py`.

Expected: imports succeed and the packaging verifier passes.

- [ ] **Step 4: Launch the application and exercise the golden path**

Run: `QT_QPA_PLATFORM=offscreen python -c "from PyQt6.QtWidgets import QApplication; from plugins.empty_folder_cleaner import EmptyFolderCleaner; app=QApplication([]); plugin=EmptyFolderCleaner(); plugin.get_widget(); print('ui ok')"`.

Then manually verify with a temporary directory: nested empty folders appear as one top-level candidate, a hidden file prevents a candidate, selecting and deleting removes only empty folders, and the selected root remains. Check both `Theme.DARK` and `Theme.LIGHT` by calling `plugin.update_theme(...)` in the same smoke test.

- [ ] **Step 5: Review final diff and status**

Run: `git diff main...HEAD --stat`, `git diff main...HEAD --check`, and `git status --short`.

Expected: only the design document, implementation, tests, configuration, and packaging files are present; no generated build artifacts or user files are included.

- [ ] **Step 6: Commit any verified fixes as a new commit**

```bash
git add <only-files-changed-by-the-fix>
git commit -m "fix: 修复空文件夹清理插件验证问题"
```

Do not amend earlier commits; preserve each completed task as a separate commit.
