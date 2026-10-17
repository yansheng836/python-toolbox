# -*- encoding: utf-8 -*-
"""
空文件夹清理插件

递归查找完全为空的文件夹（只包含空子目录的目录树也算空），
按最上层候选目录展示，用户勾选后安全递归删除空目录。
扫描根目录始终保留，删除过程只使用 os.rmdir，不会删除文件。
"""

import os
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QHeaderView, QSizePolicy, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from toolbox import (
    AnimatedButton, Card, FONT_SIZE_14, FONT_WEIGHT_700, SelectableLabel,
    TITLE_STYLES, Theme, ToolPlugin,
)
from common.action_panel import ActionPanel
from common.base_worker import BaseWorker
from common.directory_drop_line_edit import DirectoryDropLineEdit
from common.message_utils import show_error, show_info, show_question, show_warning
from common.utils import WINDOWS_RESERVED_NAMES, get_lineedit_style


def _is_reserved_name(name: str) -> bool:
    """判断文件名是否为 Windows 保留设备名"""
    return os.path.splitext(name)[0].upper() in WINDOWS_RESERVED_NAMES


def _is_junction(entry) -> bool:
    """判断目录项是否为 Windows junction（旧版本 Python 不支持时返回 False）"""
    checker = getattr(entry, "is_junction", None)
    return bool(checker and checker())


def _is_link_like(entry) -> bool:
    """判断目录项是否为符号链接或 junction"""
    try:
        return entry.is_symlink() or _is_junction(entry)
    except OSError as exc:
        print(f"无法检查链接状态 {entry.path}: {exc}")
        return True


def _is_link_path(path: str) -> bool:
    """判断路径本身是否为符号链接或 junction"""
    if os.path.islink(path):
        return True
    checker = getattr(os.path, "isjunction", None)
    try:
        return bool(checker and checker(path))
    except OSError as exc:
        print(f"无法检查路径链接状态 {path}: {exc}")
        return True


def _scan_directory(directory: str) -> tuple[bool, list[str]]:
    """递归判断目录是否为空，并收集其内部的最高层空目录候选

    Returns:
        (是否递归为空, 最高层空目录候选列表)。返回的候选列表不包含
        当前目录自身；当前目录是否作为候选由调用方决定。
    """
    try:
        with os.scandir(directory) as entries:
            entries = list(entries)
    except OSError as exc:
        print(f"无法扫描目录 {directory}: {exc}")
        return False, []

    has_content = False
    empty_children = []
    candidates = []

    for entry in entries:
        if entry.name.startswith(".") or _is_reserved_name(entry.name):
            # 隐藏项和保留设备名一律视为内容，且不进入
            has_content = True
            continue
        if _is_link_like(entry):
            has_content = True
            continue

        try:
            is_directory = entry.is_dir(follow_symlinks=False)
        except OSError as exc:
            print(f"无法检查目录条目 {entry.path}: {exc}")
            has_content = True
            continue

        if not is_directory:
            has_content = True
            continue

        child_empty, child_candidates = _scan_directory(entry.path)
        if child_empty:
            empty_children.append(os.path.abspath(entry.path))
        else:
            has_content = True
            candidates.extend(child_candidates)

    if not has_content:
        # 当前目录整棵子树均为空，由更高层决定是否作为候选
        return True, []

    # 当前目录非空，其空子目录和更深处发现的候选都可以删除
    candidates.extend(empty_children)
    return False, candidates


def find_empty_folder_candidates(root_path: str) -> list[str]:
    """查找根目录内部可删除的最高层递归空目录

    根目录本身始终保留，不会出现在结果中。结果路径为绝对路径且排序稳定。
    """
    root = os.path.abspath(os.fspath(root_path))
    if _is_link_path(root) or not os.path.isdir(root):
        raise ValueError(f"扫描根目录不是有效目录: {root_path}")

    try:
        with os.scandir(root) as entries:
            entries = list(entries)
    except OSError as exc:
        print(f"无法读取根目录 {root}: {exc}")
        raise ValueError(f"无法读取扫描根目录: {root_path}") from exc

    candidates = []
    for entry in entries:
        if entry.name.startswith(".") or _is_reserved_name(entry.name):
            continue
        if _is_link_like(entry):
            continue

        try:
            if not entry.is_dir(follow_symlinks=False):
                continue
        except OSError as exc:
            print(f"无法检查目录条目 {entry.path}: {exc}")
            continue

        child_empty, child_candidates = _scan_directory(entry.path)
        if child_empty:
            candidates.append(os.path.abspath(entry.path))
        else:
            candidates.extend(child_candidates)

    return sorted(set(candidates))


def _collect_real_directories(directory: str) -> list[str]:
    """自底向上收集目录及其真实子目录，不跟随符号链接/junction"""
    with os.scandir(directory) as entries:
        entries = list(entries)

    collected = []
    for entry in entries:
        if _is_reserved_name(entry.name):
            continue
        if _is_link_like(entry):
            continue
        try:
            is_directory = entry.is_dir(follow_symlinks=False)
        except OSError as exc:
            print(f"无法检查目录条目 {entry.path}: {exc}")
            raise
        if is_directory:
            collected.extend(_collect_real_directories(entry.path))

    collected.append(directory)
    return collected


def _remove_empty_folder_tree_details(folder_path: str) -> tuple[bool, str, list[str]]:
    """删除候选目录及其中的空子目录，返回 (是否成功, 消息, 失败路径)"""
    folder = os.path.abspath(os.fspath(folder_path))

    if _is_link_path(folder):
        message = f"目标目录是符号链接或 junction，已跳过：\n{folder}"
        return False, message, [folder]
    if not os.path.exists(folder):
        return True, f"目录已不存在：\n{folder}", []
    if not os.path.isdir(folder):
        message = f"目标路径不是目录：\n{folder}"
        return False, message, [folder]

    try:
        directories = _collect_real_directories(folder)
    except OSError as exc:
        print(f"无法扫描待删除目录 {folder}: {exc}")
        message = f"无法扫描目录，已保留：\n{folder}\n{exc}"
        return False, message, [folder]

    failed = []
    for directory in directories:
        try:
            os.rmdir(directory)
        except OSError as exc:
            print(f"删除目录失败 {directory}: {exc}")
            failed.append(directory)

    if failed:
        message = (
            "以下目录无法删除（可能已变为非空、被占用或权限不足）：\n"
            + "\n".join(failed)
        )
        return False, message, failed

    return True, f"已删除空目录：\n{folder}", []


def remove_empty_folder_tree(folder_path: str) -> tuple[bool, str]:
    """安全删除候选空目录树

    只对目录调用 os.rmdir，绝不删除文件。扫描后新增文件或目录被占用时，
    相关目录会保留并作为失败报告。
    """
    success, message, _failed = _remove_empty_folder_tree_details(folder_path)
    return success, message


def _is_safe_candidate(root: str, candidate: str) -> bool:
    """判断候选目录是否位于扫描根目录内部且不是根目录自身"""
    try:
        root_norm = os.path.normcase(os.path.abspath(root))
        candidate_norm = os.path.normcase(os.path.abspath(candidate))
        if candidate_norm == root_norm:
            return False
        return os.path.commonpath([root_norm, candidate_norm]) == root_norm
    except (OSError, ValueError) as exc:
        print(f"无法校验候选目录 {candidate}: {exc}")
        return False


class EmptyFolderWorker(BaseWorker):
    """空文件夹扫描/删除后台任务"""

    folders_found = pyqtSignal(list)
    deleted = pyqtSignal(list, list)

    def __init__(self, root_path: str, operation: str,
                 folder_paths: Optional[list[str]] = None):
        super().__init__()
        self.root_path = root_path
        self.operation = operation
        self.folder_paths = folder_paths

    def _run_scan(self):
        self.status.emit("正在扫描空目录...")
        folders = find_empty_folder_candidates(self.root_path)
        self.folders_found.emit(folders)
        self.progress.emit(100)
        self.finished.emit(
            True, f"扫描完成，找到 {len(folders)} 个可删除的空目录"
        )

    def _run_delete(self):
        self.status.emit("正在删除空目录...")
        candidates = self.folder_paths or []
        deleted = []
        failed = []
        total = len(candidates)

        for index, candidate in enumerate(candidates, start=1):
            candidate_abs = os.path.abspath(os.fspath(candidate))
            if not _is_safe_candidate(self.root_path, candidate_abs):
                print(f"跳过不安全的候选目录: {candidate_abs}")
                failed.append(candidate_abs)
            else:
                self.status.emit(f"正在删除：{candidate_abs}")
                success, message, failures = _remove_empty_folder_tree_details(
                    candidate_abs
                )
                if success:
                    deleted.append(candidate_abs)
                else:
                    failed.extend(failures or [candidate_abs])
                self.status.emit(message)
            self.progress.emit(int(index * 100 / total) if total else 100)

        self.deleted.emit(deleted, failed)
        message = f"清理完成：成功 {len(deleted)} 个，失败 {len(failed)} 个"
        if failed:
            message += "\n\n失败路径：\n" + "\n".join(failed[:10])
            if len(failed) > 10:
                message += f"\n... 还有 {len(failed) - 10} 个失败路径"
        self.finished.emit(not failed, message)

    def run(self):
        """执行扫描或删除任务"""
        try:
            if self.operation == "scan":
                self._run_scan()
            elif self.operation == "delete":
                self._run_delete()
            else:
                raise ValueError(f"不支持的操作: {self.operation}")
        except (OSError, ValueError) as exc:
            print(f"空文件夹任务失败: {exc}")
            self.finished.emit(False, f"操作失败: {exc}")
        except Exception as exc:
            print(f"空文件夹任务发生未预期错误: {exc}")
            self.finished.emit(False, f"操作失败: {exc}")


class EmptyFolderCleanerWidget(QWidget):
    """空文件夹清理插件主界面"""

    def __init__(self, parent=None, icon="", name="", description="",
                 theme=None):
        super().__init__(parent)
        self.icon = icon
        self.name = name
        self.description = description
        self.theme = theme or Theme.DARK
        self.selected_folder = ""
        self.candidates = []
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        self.title_label = SelectableLabel(f"{self.icon} {self.name}")
        layout.addWidget(self.title_label)

        self.desc_label = SelectableLabel(self.description)
        layout.addWidget(self.desc_label)

        folder_card = Card(title="选择扫描文件夹（支持拖拽）")
        folder_layout = QHBoxLayout()
        self.folder_display = DirectoryDropLineEdit()
        self.folder_display.setPlaceholderText(
            "选择要清理的根目录，或将文件夹拖拽到此..."
        )
        self.folder_display.directory_dropped.connect(self.on_folder_dropped)
        folder_layout.addWidget(self.folder_display)

        self.browse_btn = AnimatedButton("浏览")
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.browse_btn)
        folder_card.content_layout.addLayout(folder_layout)

        self.scan_panel = ActionPanel(
            button_text="开始扫描",
            use_gradient=True,
            status_text="请选择文件夹开始扫描",
        )
        self.scan_panel.clicked.connect(self.start_scan)
        self.scan_panel.btn.setEnabled(False)
        folder_card.content_layout.addWidget(self.scan_panel)
        layout.addWidget(folder_card)

        results_card = Card(title="可删除的空目录（扫描后勾选）")
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["目录路径"])
        self.results_tree.setColumnCount(1)
        self.results_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.results_tree.setMinimumHeight(220)
        self.results_tree.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.results_tree.setUniformRowHeights(True)
        results_card.content_layout.addWidget(self.results_tree)

        select_layout = QHBoxLayout()
        self.select_all_btn = AnimatedButton("全选")
        self.select_all_btn.setMaximumWidth(80)
        self.select_all_btn.clicked.connect(self.select_all_candidates)
        select_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = AnimatedButton("取消全选")
        self.deselect_all_btn.setMaximumWidth(100)
        self.deselect_all_btn.clicked.connect(self.deselect_all_candidates)
        select_layout.addWidget(self.deselect_all_btn)
        select_layout.addStretch()
        results_card.content_layout.addLayout(select_layout)

        self.stats_label = SelectableLabel("未扫描")
        results_card.content_layout.addWidget(self.stats_label)
        layout.addWidget(results_card)

        delete_card = Card(title="删除操作")
        self.delete_panel = ActionPanel(
            button_text="删除选中目录",
            use_gradient=True,
            gradient_colors=(
                Theme.DARK["error"], Theme.DARK["error_gradient_end"]
            ),
            gradient_hover_colors=(
                Theme.DARK["error_hover"], Theme.DARK["error_gradient_end"]
            ),
            status_text="请先扫描并勾选要删除的目录",
        )
        self.delete_panel.clicked.connect(self.delete_selected)
        self.delete_panel.btn.setEnabled(False)
        delete_card.content_layout.addWidget(self.delete_panel)
        layout.addWidget(delete_card)

        self.apply_theme(self.theme)

    def apply_theme(self, theme):
        """应用主题到所有组件"""
        self.theme = theme

        if hasattr(self, "title_label"):
            self.title_label.setStyleSheet(
                f"font-size: {TITLE_STYLES['font_size']}; "
                f"font-weight: {FONT_WEIGHT_700}; color: {theme['text']};"
            )
        if hasattr(self, "desc_label"):
            self.desc_label.setStyleSheet(
                f"color: {theme['text_secondary']}; "
                f"font-size: {FONT_SIZE_14};"
            )
        if hasattr(self, "folder_display"):
            self.folder_display.setStyleSheet(get_lineedit_style(theme))
        if hasattr(self, "browse_btn"):
            self.browse_btn.update_style(theme)
        if hasattr(self, "scan_panel"):
            self.scan_panel.update_theme(theme)
        if hasattr(self, "results_tree"):
            self.results_tree.setStyleSheet(f"""
                QTreeWidget {{
                    background-color: {theme['bg']};
                    border: 1px solid {theme['border']};
                    border-radius: 6px;
                    color: {theme['text']};
                    padding: 4px;
                }}
                QTreeWidget::item {{
                    padding: 6px;
                    color: {theme['text']};
                }}
                QTreeWidget::item:selected {{
                    background-color: {theme['primary']};
                    color: {theme['text']};
                }}
                QHeaderView::section {{
                    background-color: {theme['bg_secondary']};
                    color: {theme['text_secondary']};
                    padding: 4px 8px;
                    border: none;
                    font-weight: bold;
                }}
            """)
        if hasattr(self, "select_all_btn"):
            self.select_all_btn.update_style(theme)
        if hasattr(self, "deselect_all_btn"):
            self.deselect_all_btn.update_style(theme)
        if hasattr(self, "stats_label"):
            self.stats_label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_14};"
            )
        if hasattr(self, "delete_panel"):
            error_colors = (
                theme["error"], theme.get("error_gradient_end", theme["error"])
            )
            hover_colors = (
                theme["error_hover"],
                theme.get("error_gradient_end", theme["error"]),
            )
            self.delete_panel.gradient_colors = error_colors
            self.delete_panel.gradient_hover_colors = hover_colors
            self.delete_panel.update_theme(theme)

    def browse_folder(self):
        """选择扫描根目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择要清理的根目录", self.selected_folder or ""
        )
        if dir_path:
            self.set_folder(dir_path)
            self.start_scan()

    def on_folder_dropped(self, dir_path):
        """处理拖入的根目录"""
        self.set_folder(dir_path)
        self.start_scan()

    def set_folder(self, dir_path):
        """设置根目录并更新 UI 状态"""
        self.selected_folder = dir_path
        self.folder_display.setText(dir_path)
        self.scan_panel.btn.setEnabled(True)
        self.scan_panel.update_status(f"已选择文件夹: {dir_path}")

    def start_scan(self):
        """启动后台扫描"""
        if not self.selected_folder or not os.path.isdir(self.selected_folder):
            show_warning(self, "警告", "请先选择有效的文件夹！")
            return

        self.scan_panel.btn.setEnabled(False)
        self.scan_panel.start_task(maximum=0, status="正在扫描空目录...")
        self.delete_panel.btn.setEnabled(False)
        self.delete_panel.update_status("扫描完成后可选择要删除的目录")
        self.results_tree.clear()
        self.candidates = []
        self.stats_label.setText("正在扫描...")

        self.worker = EmptyFolderWorker(self.selected_folder, "scan")
        self.worker.folders_found.connect(self.show_candidates)
        self.worker.status.connect(self.scan_panel.update_status)
        self.worker.finished.connect(self.scan_finished)
        self.worker.start()

    def show_candidates(self, candidates):
        """在列表中显示扫描到的空目录"""
        self.candidates = list(candidates)
        self.results_tree.clear()

        for path in self.candidates:
            item = QTreeWidgetItem(self.results_tree)
            item.setText(0, path)
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)

        self.stats_label.setText(
            f"找到 {len(self.candidates)} 个可删除的空目录"
        )
        self.delete_panel.btn.setEnabled(bool(self.candidates))
        if self.candidates:
            self.delete_panel.update_status(
                f"找到 {len(self.candidates)} 个可删除目录，请勾选后删除"
            )
        else:
            self.delete_panel.update_status("未找到可删除的空目录")

    def scan_finished(self, success, message):
        """扫描完成回调"""
        self.scan_panel.finish_task(message)
        self.scan_panel.btn.setEnabled(True)
        if not success:
            self.delete_panel.btn.setEnabled(False)
            show_error(self, "扫描失败", message)
            return
        if not self.candidates:
            show_info(self, "扫描完成", message)

    def get_checked_paths(self):
        """返回用户勾选的目录路径"""
        paths = []
        for index in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(index)
            if item.checkState(0) == Qt.CheckState.Checked:
                path = item.data(0, Qt.ItemDataRole.UserRole)
                if path:
                    paths.append(path)
        return paths

    def select_all_candidates(self):
        """勾选所有候选目录"""
        for index in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(index)
            item.setCheckState(0, Qt.CheckState.Checked)

    def deselect_all_candidates(self):
        """取消勾选所有候选目录"""
        for index in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(index)
            item.setCheckState(0, Qt.CheckState.Unchecked)

    def delete_selected(self):
        """确认并删除勾选的空目录"""
        paths = self.get_checked_paths()
        if not paths:
            show_warning(self, "警告", "请先勾选要删除的目录！")
            return

        confirm_message = f"即将删除 {len(paths)} 个空目录，是否继续？\n\n"
        for index, path in enumerate(paths[:10], start=1):
            confirm_message += f"{index}. {path}\n"
        if len(paths) > 10:
            confirm_message += f"... 还有 {len(paths) - 10} 个目录未显示\n"
        confirm_message += "\n删除操作不可恢复，请确认！"

        if not show_question(self, "确认删除", confirm_message):
            return

        self.scan_panel.btn.setEnabled(False)
        self.delete_panel.start_task(maximum=100, status="正在删除空目录...")

        self.worker = EmptyFolderWorker(
            self.selected_folder, "delete", paths
        )
        self.worker.status.connect(self.delete_panel.update_status)
        self.worker.progress.connect(self.delete_panel.update_progress)
        self.worker.finished.connect(self.delete_finished)
        self.worker.start()

    def delete_finished(self, success, message):
        """删除完成回调"""
        self.delete_panel.finish_task(message)
        self.delete_panel.btn.setEnabled(False)
        self.scan_panel.btn.setEnabled(True)
        self.results_tree.clear()
        self.candidates = []
        self.stats_label.setText("删除完成 — 可重新扫描")
        self.delete_panel.update_status("请重新扫描以刷新结果")
        if success:
            show_info(self, "删除完成", message)
        else:
            show_error(self, "删除结果", message)


class EmptyFolderCleaner(ToolPlugin):
    """空文件夹清理插件"""

    name = "空文件夹清理"
    description = "递归查找并删除完全为空的文件夹，支持多层空目录"
    icon = "🗑️"
    order = 205

    def create_ui(self):
        """创建插件 UI"""
        self.widget = EmptyFolderCleanerWidget(
            icon=self.icon,
            name=self.name,
            description=self.description,
            theme=Theme.DARK,
        )
        self.title_label = self.widget.title_label
        self.desc_label = self.widget.desc_label
        self.results_tree = self.widget.results_tree
        self.scan_panel = self.widget.scan_panel
        self.delete_panel = self.widget.delete_panel
        return self.widget

    def update_theme(self, theme):
        """更新主题"""
        if hasattr(self, "widget") and hasattr(self.widget, "apply_theme"):
            self.widget.apply_theme(theme)
