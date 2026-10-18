# -*- encoding: utf-8 -*-
"""
文件去重工具插件
按内容Hash查找重复文件，支持预览后选择规则删除
"""
import os
import re
import hashlib
from collections import defaultdict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QHBoxLayout, QCheckBox
)

from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, FONT_WEIGHT_700, Theme
from common.message_utils import show_info, show_error, show_warning, show_question
from common.action_panel import ActionPanel
from common.utils import get_create_time, get_modify_time, WINDOWS_RESERVED_NAMES, get_combo_style
from common.base_worker import BaseWorker
from common.directory_drop_line_edit import DirectoryDropLineEdit
from common.i18n import t, bind_combo

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QBrush
from PyQt6.QtWidgets import QSizePolicy

try:
    from send2trash import send2trash
    SEND2TRASH_AVAILABLE = True
except ImportError as exc:
    print(f"send2trash 未安装，回收站功能不可用: {exc}")
    SEND2TRASH_AVAILABLE = False
    send2trash = None


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


def _is_within_root(root_path: str, target_path: str) -> bool:
    """判断 target_path 的真实路径是否位于 root_path 真实路径之内"""
    try:
        root_real = os.path.normcase(os.path.realpath(os.path.abspath(root_path)))
        target_real = os.path.normcase(os.path.realpath(os.path.abspath(target_path)))
        if target_real == root_real:
            return False
        return os.path.commonpath([root_real, target_real]) == root_real
    except (OSError, ValueError) as exc:
        print(f"无法校验路径 {target_path}: {exc}")
        return False


def _iter_regular_files(root_path):
    """递归遍历 root_path 下的真实文件

    使用 os.scandir 并跳过符号链接 / junction（含目录与文件），避免
    进入指向外部的 junction 造成死循环或越界扫描，同时跳过 Windows
    保留设备名。
    """
    stack = [root_path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                entries = list(it)
        except OSError as exc:
            print(f"无法扫描目录 {current}: {exc}")
            continue
        for entry in entries:
            if _is_link_like(entry):
                # 跳过符号链接 / junction，避免越界或死循环
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
            except OSError as exc:
                print(f"无法检查目录条目 {entry.path}: {exc}")
                continue
            # 跳过 Windows 保留设备名（如 con.log），open() 会阻塞
            if os.path.splitext(entry.name)[0].upper() in WINDOWS_RESERVED_NAMES:
                continue
            yield entry.path


class FileDeduplicationWorker(BaseWorker):
    """文件去重工作线程"""
    progress = pyqtSignal(int, int)  # 已扫描文件数, 总文件数
    # 继承 BaseWorker 的 status 和 result 信号
    duplicates_found = pyqtSignal(dict)  # {hash: [file_paths]}
    sizes_found = pyqtSignal(dict)  # {file_path: 扫描时大小}，用于删除前 TOCTOU 复核
    error = pyqtSignal(str)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.cancel_requested = False

    # Windows 保留设备名称定义在 common/utils.py 的 WINDOWS_RESERVED_NAMES 中

    def run(self):
        try:
            self.status.emit(t("plugin.file_deduplicator.msg.scanning_folder"))
            # 第一遍：收集所有文件及大小（os.scandir，跳过符号链接/junction）
            all_files = []
            for file_path in _iter_regular_files(self.folder_path):
                if self.cancel_requested:
                    self.result.emit(False, t("plugin.file_deduplicator.msg.scan_cancelled"))
                    return
                if _is_link_path(file_path):
                    # 链接文件不纳入去重，防止删除操作误伤真实数据文件
                    continue
                try:
                    file_size = os.path.getsize(file_path)
                except OSError as exc:
                    print(f"无法获取文件大小 {file_path}: {exc}")
                    continue
                all_files.append((file_path, file_size))
            total_files = len(all_files)
            self.status.emit(t("plugin.file_deduplicator.msg.found_files", count=total_files))

            # 按文件大小分组，只保留大小相同的文件（大小唯一不可能重复）
            all_files.sort(key=lambda x: x[1])
            size_candidates = []
            i = 0
            while i < len(all_files):
                j = i + 1
                while j < len(all_files) and all_files[j][1] == all_files[i][1]:
                    j += 1
                if j - i > 1:
                    size_candidates.extend(fp for fp, _ in all_files[i:j])
                i = j

            candidate_count = len(size_candidates)
            self.status.emit(
                t("plugin.file_deduplicator.msg.size_filter_done",
                  count=candidate_count, total=total_files)
            )

            # 第二轮：快速Hash（首尾各64KB + 文件大小），排除明显不同的文件
            quick_hash_to_files = defaultdict(list)
            scanned = 0
            for file_path in size_candidates:
                if self.cancel_requested:
                    self.result.emit(False, t("plugin.file_deduplicator.msg.scan_cancelled"))
                    return
                try:
                    quick_hash = self.compute_quick_hash(file_path)
                    if quick_hash:
                        quick_hash_to_files[quick_hash].append(file_path)
                except OSError as e:
                    print(f"compute_quick_hash error: {e}")
                    self.error.emit(
                        t("plugin.file_deduplicator.error.read_failed",
                          path=file_path, error=str(e))
                    )
                scanned += 1
                self.progress.emit(scanned, candidate_count)

            # 只对快速Hash相同的文件计算完整Hash
            full_hash_candidates = []
            for quick_hash, files in quick_hash_to_files.items():
                if len(files) > 1:
                    full_hash_candidates.extend(files)

            full_count = len(full_hash_candidates)
            if full_count > 0:
                self.status.emit(
                    t("plugin.file_deduplicator.msg.quick_hash_done",
                      count=full_count, total=candidate_count)
                )

            # 第三轮：完整Hash
            hash_to_files = defaultdict(list)
            scanned = 0
            for file_path in full_hash_candidates:
                if self.cancel_requested:
                    self.result.emit(False, t("plugin.file_deduplicator.msg.scan_cancelled"))
                    return
                try:
                    file_hash = self.compute_file_hash(file_path)
                    if file_hash:
                        hash_to_files[file_hash].append(file_path)
                except OSError as e:
                    print(f"compute_file_hash error: {e}")
                    self.error.emit(
                        t("plugin.file_deduplicator.error.read_failed",
                          path=file_path, error=str(e))
                    )
                scanned += 1
                self.progress.emit(scanned, full_count)

            # 过滤出重复文件（Hash对应多个文件）
            duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
            # 保留第一遍扫描时的大小，删除前用于 TOCTOU 复核（文件可能被替换）
            size_map = dict(all_files)
            self.sizes_found.emit({
                fp: size_map[fp]
                for files in duplicates.values()
                for fp in files
                if fp in size_map
            })
            self.duplicates_found.emit(duplicates)
            self.result.emit(
                True,
                t("plugin.file_deduplicator.msg.scan_done", count=len(duplicates))
            )
        except Exception as e:
            print(f"Error in FileDeduplicator: {e}")
            self.result.emit(
                False,
                t("plugin.file_deduplicator.error.scan_failed", error=str(e))
            )

    def compute_file_hash(self, file_path, chunk_size=65536):
        """计算文件的完整SHA-256哈希值

        读取失败时抛出 OSError，由调用方统一上报，避免不可读文件被无声排除。
        取消时返回 None。
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                if self.cancel_requested:
                    return None
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def compute_quick_hash(self, file_path, head_size=65536):
        """快速Hash：读取首尾各head_size字节 + 文件大小，用于初筛

        读取失败时抛出 OSError，由调用方统一上报。
        """
        file_size = os.path.getsize(file_path)
        hash_obj = hashlib.sha256()
        hash_obj.update(str(file_size).encode())
        with open(file_path, 'rb') as f:
            head = f.read(head_size)
            hash_obj.update(head)
            if file_size > head_size:
                f.seek(-head_size, 2)
                tail = f.read(head_size)
                hash_obj.update(tail)
        return hash_obj.hexdigest()

    def cancel(self):
        self.cancel_requested = True


class FileDeletionWorker(BaseWorker):
    """重复文件删除工作线程

    在后台线程逐个删除文件，进度经 progress 上报，响应 cancel_requested。
    删除前校验目标位于扫描根目录内，防止越界删除。
    """
    progress = pyqtSignal(int, int)  # 已处理数, 总数

    def __init__(self, file_paths, root_path, expected_sizes=None, use_trash=False):
        super().__init__()
        self.file_paths = list(file_paths)
        self.root_path = root_path
        self.expected_sizes = dict(expected_sizes or {})
        self.use_trash = bool(use_trash and SEND2TRASH_AVAILABLE)
        self.cancel_requested = False

    def _delete_one(self, file_path):
        """删除单个文件，返回 (结果, 说明)

        结果为 "deleted" / "missing" / "changed" / "failed"。
        """
        expected = self.expected_sizes.get(file_path)
        if expected is not None:
            try:
                actual = os.path.getsize(file_path)
            except FileNotFoundError:
                return "missing", ""
            except OSError as exc:
                return "failed", str(exc)
            if actual != expected:
                # 扫描与删除间隔内内容被替换，跳过以免误删
                return "changed", t("plugin.file_deduplicator.msg.file_changed_skipped")
        if not os.path.exists(file_path):
            return "missing", ""
        try:
            if self.use_trash:
                send2trash(file_path)
            else:
                os.remove(file_path)
            return "deleted", ""
        except OSError as exc:
            print(f"delete error: {exc}")
            return "failed", str(exc)

    def run(self):
        try:
            total = len(self.file_paths)
            deleted = 0
            missing = 0
            failed = 0
            failed_files = []
            for index, file_path in enumerate(self.file_paths, start=1):
                if self.cancel_requested:
                    message = t(
                        "plugin.file_deduplicator.msg.delete_done",
                        count=deleted, failed_count=failed
                    ) + t("plugin.file_deduplicator.msg.scan_cancelled")
                    self.result.emit(False, message)
                    return
                self.status.emit(
                    t("plugin.file_deduplicator.msg.deleting_path", path=file_path)
                )
                if not _is_within_root(self.root_path, file_path):
                    # 目标越出扫描根目录（可能为链接/被替换），拒绝删除
                    failed += 1
                    failed_files.append(f"{file_path}: {t('plugin.file_deduplicator.msg.outside_root')}")
                elif _is_link_path(file_path):
                    failed += 1
                    failed_files.append(f"{file_path}: {t('plugin.file_deduplicator.msg.is_link_skipped')}")
                else:
                    outcome, detail = self._delete_one(file_path)
                    if outcome == "deleted":
                        deleted += 1
                    elif outcome == "missing":
                        # 文件已不存在：与"实际删除"区分统计，避免口径误导
                        missing += 1
                    else:
                        failed += 1
                        failed_files.append(f"{file_path}: {detail}")
                self.progress.emit(index, total)

            message = t(
                "plugin.file_deduplicator.msg.delete_done",
                count=deleted, failed_count=failed
            )
            if missing:
                message += t(
                    "plugin.file_deduplicator.msg.delete_missing_skipped",
                    count=missing
                )
            if failed_files:
                message += t("plugin.file_deduplicator.msg.failures_header")
                message += "\n".join(failed_files[:5])
                if len(failed_files) > 5:
                    message += t(
                        "plugin.file_deduplicator.msg.more_failures",
                        count=len(failed_files) - 5
                    )
            self.result.emit(True, message)
        except Exception as e:
            print(f"Error in FileDeletionWorker: {e}")
            self.result.emit(
                False,
                t("plugin.file_deduplicator.error.scan_failed", error=str(e))
            )

    def cancel(self):
        self.cancel_requested = True


class FileDeduplicatorWidget(QWidget):
    """文件去重工具主界面"""

    def __init__(self, parent=None, icon="", name="", description="", theme=None):
        super().__init__(parent)
        self.icon = icon
        self.name = name
        self.description = description
        self.theme = theme or Theme.DARK
        self.selected_folder = ""
        self.worker = None
        self.duplicates = {}  # {hash: [file_paths]}
        self.scan_sizes = {}  # {file_path: 扫描时大小}，删除前 TOCTOU 复核
        self.setup_ui()

    def setup_ui(self):
        self.group_bg_color = QColor(self.theme['surface'])  # 默认分组背景色，apply_theme 会覆盖
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标题（使用词典中的 icon + name）
        self.title_label = SelectableLabel(
            f"{self.icon} {t('plugin.file_deduplicator.name')}"
        )
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # 描述（使用词典）
        self.desc_label = SelectableLabel(
            t("plugin.file_deduplicator.description")
        )
        self.desc_label.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: {FONT_SIZE_14};")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # 文件夹选择卡片
        self.folder_card = Card(title=t("plugin.file_deduplicator.card.select_folder"))
        folder_layout = QHBoxLayout()
        self.folder_display = DirectoryDropLineEdit()
        self.folder_display.setPlaceholderText(
            t("plugin.file_deduplicator.placeholder.folder")
        )
        self.folder_display.directory_dropped.connect(self.on_folder_dropped)
        folder_layout.addWidget(self.folder_display)

        self.browse_btn = AnimatedButton(t("plugin.file_deduplicator.button.browse"))
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.browse_btn)
        self.folder_card.content_layout.addLayout(folder_layout)

        # 扫描操作面板（按钮 + 进度条 + 状态）
        self.scan_panel = ActionPanel(
            button_text=t("plugin.file_deduplicator.button.scan"),
            use_gradient=True,
            status_text=t("plugin.file_deduplicator.msg.select_folder_hint")
        )
        self.scan_panel.clicked.connect(self.start_scan)
        self.scan_panel.btn.setEnabled(False)
        self.folder_card.content_layout.addWidget(self.scan_panel)

        # 扫描取消按钮（扫描期间显示）
        self.cancel_scan_btn = AnimatedButton(
            t("plugin.file_deduplicator.button.cancel_scan")
        )
        self.cancel_scan_btn.setMaximumWidth(120)
        self.cancel_scan_btn.clicked.connect(self.cancel_scan)
        self.cancel_scan_btn.setVisible(False)
        self.folder_card.content_layout.addWidget(self.cancel_scan_btn)

        layout.addWidget(self.folder_card)

        # 结果卡片
        self.results_card = Card(title=t("plugin.file_deduplicator.card.results"))
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels([
            t("plugin.file_deduplicator.column.file_info"),
            t("plugin.file_deduplicator.column.size"),
            t("plugin.file_deduplicator.column.created"),
            t("plugin.file_deduplicator.column.modified"),
        ])
        self.results_tree.setColumnWidth(0, 580)
        self.results_tree.setColumnWidth(1, 80)
        self.results_tree.setColumnWidth(2, 140)
        self.results_tree.setColumnWidth(3, 140)
        self.results_tree.setMinimumHeight(400)
        self.results_tree.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.results_card.content_layout.addWidget(self.results_tree)

        # 统计标签
        self.stats_label = SelectableLabel(t("plugin.file_deduplicator.msg.not_scanned"))
        self.stats_label.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: {FONT_SIZE_14};")
        self.results_card.content_layout.addWidget(self.stats_label)
        layout.addWidget(self.results_card)

        # 删除规则卡片
        self.deletion_card = Card(title=t("plugin.file_deduplicator.card.deletion_rules"))

        rule_row_layout = QHBoxLayout()

        # 左半：删除规则下拉框 + 删除到回收站选项
        left_half = QHBoxLayout()
        self.rule_label = SelectableLabel(t("plugin.file_deduplicator.label.rule"))
        left_half.addWidget(self.rule_label)
        self.rule_combo = QComboBox()
        bind_combo(self.rule_combo, [
            ("plugin.file_deduplicator.combo.rule_ctime_asc", 0),
            ("plugin.file_deduplicator.combo.rule_ctime_desc", 1),
            ("plugin.file_deduplicator.combo.rule_name_asc", 2),
            ("plugin.file_deduplicator.combo.rule_name_desc", 3),
            ("plugin.file_deduplicator.combo.rule_smart_asc", 4),
            ("plugin.file_deduplicator.combo.rule_smart_desc", 5),
        ])
        # 限制最小宽度按 16 字符计算，避免长英文文案撑爆布局
        self.rule_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.rule_combo.setMinimumContentsLength(16)
        left_half.addWidget(self.rule_combo, 1)
        self.rule_combo.currentIndexChanged.connect(self._sort_by_rule)

        # 删除到回收站（紧接删除规则；send2trash 可用时默认勾选，不可用时禁用）
        self.use_trash_label = SelectableLabel(
            t("plugin.file_deduplicator.label.use_trash")
        )
        left_half.addWidget(self.use_trash_label)
        self.use_trash_checkbox = QCheckBox()
        self.use_trash_checkbox.setChecked(SEND2TRASH_AVAILABLE)
        if not SEND2TRASH_AVAILABLE:
            self.use_trash_checkbox.setEnabled(False)
            self.use_trash_label.setText(
                t("plugin.file_deduplicator.label.use_trash")
                + t("plugin.file_deduplicator.msg.trash_unavailable")
            )
        left_half.addWidget(self.use_trash_checkbox)

        # 右半：删除后是否自动扫描（文字在前，勾选框在后，与"启用压缩"样式一致）
        right_half = QHBoxLayout()
        self.auto_rescan_label = SelectableLabel(t("plugin.file_deduplicator.label.auto_rescan"))
        right_half.addWidget(self.auto_rescan_label)
        self.auto_rescan_checkbox = QCheckBox()
        self.auto_rescan_checkbox.setChecked(False)
        right_half.addWidget(self.auto_rescan_checkbox)
        right_half.addStretch()

        rule_row_layout.addLayout(left_half, 1)
        rule_row_layout.addLayout(right_half, 1)
        self.deletion_card.content_layout.addLayout(rule_row_layout)

        # 全选/取消全选按钮
        select_btn_layout = QHBoxLayout()
        self.select_all_btn = AnimatedButton(t("plugin.file_deduplicator.button.select_all"))
        self.select_all_btn.setMaximumWidth(80)
        self.select_all_btn.clicked.connect(self._select_all)
        select_btn_layout.addWidget(self.select_all_btn)
        self.deselect_all_btn = AnimatedButton(t("plugin.file_deduplicator.button.deselect_all"))
        self.deselect_all_btn.setMaximumWidth(80)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        select_btn_layout.addWidget(self.deselect_all_btn)

        self.toggle_expand_btn = AnimatedButton(t("plugin.file_deduplicator.button.collapse"))
        self.toggle_expand_btn.setMaximumWidth(80)
        self.toggle_expand_btn.clicked.connect(self._toggle_expand)
        select_btn_layout.addWidget(self.toggle_expand_btn)

        self.sort_by_rule_btn = AnimatedButton(t("plugin.file_deduplicator.button.sort_by_rule"))
        self.sort_by_rule_btn.setMaximumWidth(100)
        self.sort_by_rule_btn.clicked.connect(self._sort_by_rule)
        select_btn_layout.addWidget(self.sort_by_rule_btn)

        select_btn_layout.addStretch()
        self.deletion_card.content_layout.addLayout(select_btn_layout)

        # 连接父节点勾选变化信号
        self.results_tree.itemChanged.connect(self._on_parent_checked)

        # 删除操作面板
        self.delete_panel = ActionPanel(
            button_text=t("plugin.file_deduplicator.button.delete_duplicates"),
            use_gradient=True,
            gradient_colors=(Theme.DARK['error'], Theme.DARK['error_gradient_end']),
            gradient_hover_colors=(Theme.DARK['error_hover'], Theme.DARK['error_gradient_end']),
        )
        self.delete_panel.clicked.connect(self.delete_duplicates)
        self.delete_panel.btn.setEnabled(False)
        self.deletion_card.content_layout.addWidget(self.delete_panel)

        layout.addWidget(self.deletion_card)

        # 应用初始主题
        if Theme is not None:
            self.apply_theme(Theme.DARK)

    def apply_theme(self, theme):
        """应用主题到所有组件"""
        # 标题和描述
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(
                f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700}; color: {theme['text']};"
            )
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_14};"
            )

        # 文件夹输入框
        if hasattr(self, 'folder_display'):
            self.folder_display.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {theme['bg']};
                    border: 1px solid {theme['border']};
                    border-radius: 6px;
                    padding: 6px;
                    color: {theme['text']};
                }}
                QLineEdit:hover {{
                    border-color: {theme['text_secondary']};
                }}
            """)

        # 扫描操作面板
        if hasattr(self, 'scan_panel'):
            self.scan_panel.update_theme(theme)

        # 结果树状列表
        if hasattr(self, 'results_tree'):
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
                QTreeWidget::item:hover {{
                    background-color: {theme['surface']};
                    color: {theme['text']};
                }}
                QScrollBar:horizontal {{
                    background: {theme['bg_secondary']};
                    height: 10px;
                    margin: 0;
                    border-radius: 5px;
                    border: 1px solid {theme['border']};
                }}
                QScrollBar::handle:horizontal {{
                    background: {theme['text_secondary']};
                    min-width: 20px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background: {theme['text']};
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    width: 0;
                }}
            """)
            # 同步更新分组背景色，确保文字可读
            self.group_bg_color = QColor(theme['bg_secondary'])

        # 统计标签
        if hasattr(self, 'stats_label'):
            self.stats_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_14};")

        # 下拉框
        if hasattr(self, 'rule_combo'):
            self.rule_combo.setStyleSheet(get_combo_style(theme))

        # 存储当前主题供 show_duplicates 使用
        self.current_theme = theme

        # 删除后自动扫描标签
        if hasattr(self, 'auto_rescan_label'):
            self.auto_rescan_label.setStyleSheet(f"color: {theme['text']};")

        # 回收站选项标签与取消扫描按钮
        if hasattr(self, 'use_trash_label'):
            self.use_trash_label.setStyleSheet(f"color: {theme['text']};")
        if hasattr(self, 'cancel_scan_btn'):
            self.cancel_scan_btn.update_style(theme)

        # 删除操作面板——使用主题错误色更新渐变
        if hasattr(self, 'delete_panel'):
            self.delete_panel.gradient_colors = (theme['error'], theme.get('error_gradient_end', theme['error']))
            self.delete_panel.gradient_hover_colors = (theme['error_hover'], theme.get('error_gradient_end', theme['error']))
            self.delete_panel.update_theme(theme)

        # 记录重复分组的背景色，供 show_duplicates 使用
        self.group_bg_color = QColor(theme['surface'])

        # 存储子节点高亮/普通背景色，供 _on_parent_checked 使用
        self.child_highlight_color = QColor(theme['surface'])
        self.child_normal_color = QColor(theme['bg'])

        # 更新已勾选的父节点下子节点的背景色
        if hasattr(self, 'results_tree'):
            for i in range(self.results_tree.topLevelItemCount()):
                parent = self.results_tree.topLevelItem(i)
                if parent.checkState(0) == Qt.CheckState.Checked:
                    highlight = self.child_highlight_color
                    for j in range(parent.childCount()):
                        child = parent.child(j)
                        child.setBackground(0, highlight)
                        child.setBackground(1, highlight)
                        child.setBackground(2, highlight)
                        child.setBackground(3, highlight)

    def browse_folder(self):
        """选择文件夹"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            t("plugin.file_deduplicator.dialog.select_folder"),
            self.selected_folder if self.selected_folder else ""
        )
        if dir_path:
            self._set_folder(dir_path)
            self.start_scan()

    def on_folder_dropped(self, dir_path):
        """处理拖拽文件夹事件"""
        self._set_folder(dir_path)
        self.start_scan()

    def _set_folder(self, dir_path):
        """设置文件夹路径并更新UI状态"""
        self.selected_folder = dir_path
        self.folder_display.setText(dir_path)
        self.scan_panel.btn.setEnabled(True)
        self.scan_panel.update_status(
            t("plugin.file_deduplicator.msg.folder_selected", dir=dir_path)
        )

    def _is_busy(self):
        """是否有扫描/删除任务正在运行"""
        return bool(self.worker and self.worker.isRunning())

    def _set_inputs_enabled(self, enabled):
        """扫描/删除期间禁用或恢复路径输入控件"""
        self.browse_btn.setEnabled(enabled)
        self.folder_display.setEnabled(enabled)

    def start_scan(self):
        """开始扫描"""
        # 防重入：扫描期间再次触发会覆盖旧 worker 导致崩溃
        if self._is_busy():
            show_warning(
                self,
                t("plugin.file_deduplicator.dialog.warning_title"),
                t("plugin.file_deduplicator.warning.scanning_in_progress"),
            )
            return
        if not self.selected_folder or not os.path.exists(self.selected_folder):
            show_warning(
                self,
                t("plugin.file_deduplicator.dialog.warning_title"),
                t("plugin.file_deduplicator.warning.invalid_folder"),
            )
            return

        self.scan_panel.btn.setEnabled(False)
        self._set_inputs_enabled(False)
        self.scan_panel.start_task(
            maximum=0, status=t("plugin.file_deduplicator.msg.scanning")
        )
        self.results_tree.clear()
        self.stats_label.setText(t("plugin.file_deduplicator.msg.stats_scanning"))
        self.delete_panel.btn.setEnabled(False)
        self.duplicates = {}
        self.scan_sizes = {}
        self.cancel_scan_btn.setEnabled(True)
        self.cancel_scan_btn.setVisible(True)

        self.worker = FileDeduplicationWorker(self.selected_folder)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.sizes_found.connect(self.store_scan_sizes)
        self.worker.duplicates_found.connect(self.show_duplicates)
        self.worker.result.connect(self.scan_finished)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def store_scan_sizes(self, sizes):
        """记录扫描时的文件大小，供删除前 TOCTOU 复核"""
        self.scan_sizes = dict(sizes)

    def cancel_scan(self):
        """请求取消正在运行的扫描"""
        if self.worker and self.worker.isRunning() and hasattr(self.worker, "cancel"):
            self.worker.cancel()
            self.cancel_scan_btn.setEnabled(False)
            self.scan_panel.update_status(
                t("plugin.file_deduplicator.msg.cancelling")
            )

    def update_progress(self, scanned, total):
        """更新进度条"""
        if total > 0:
            self.scan_panel.progress.setMaximum(total)
            self.scan_panel.progress.setValue(scanned)
            self.scan_panel.update_status(
                t("plugin.file_deduplicator.msg.scanned_progress",
                  count=scanned, total=total)
            )

    def update_status(self, message):
        """更新状态标签"""
        self.scan_panel.update_status(message)

    def show_duplicates(self, duplicates, checked_hashes=None, expanded_hashes=None):
        """显示重复文件

        checked_hashes/expanded_hashes 为 None 时使用默认状态（全部未勾选、
        全部展开）；语言切换重放时传入当前状态以保留用户勾选与展开。
        """
        self.duplicates = duplicates
        self.results_tree.clear()
        total_duplicates = 0
        total_savings = 0

        # 获取当前主题的文字颜色
        text_color = self.theme['text']

        for file_hash, file_list in duplicates.items():
            # 创建重复组顶级项（父节点，可勾选）
            group_item = QTreeWidgetItem(self.results_tree)
            group_item.setText(0, t(
                "plugin.file_deduplicator.tree.group_label",
                hash=file_hash[:8], count=len(file_list)
            ))
            group_item.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            group_item.setBackground(0, self.group_bg_color)
            group_item.setForeground(0, QBrush(QColor(text_color)))
            # 设置父节点可勾选；重放时恢复用户原有勾选（在子项创建后设置以联动高亮）
            group_item.setFlags(group_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            is_checked = checked_hashes is not None and file_hash in checked_hashes
            group_item.setCheckState(0, Qt.CheckState.Unchecked)
            # 存储hash到item中，方便删除时查找
            group_item.setData(0, Qt.ItemDataRole.UserRole, file_hash)

            # 计算该组可节省空间
            if file_list:
                try:
                    file_size = os.path.getsize(file_list[0])
                    total_savings += file_size * (len(file_list) - 1)
                except OSError as e:
                    print(f"getsize error: {e}")

            for file_path in file_list:
                file_item = QTreeWidgetItem(group_item)
                file_item.setText(0, file_path)
                # 文件路径存 UserRole，供 _sort_by_rule 建索引，不依赖显示文本前缀
                file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
                file_item.setForeground(0, QBrush(QColor(text_color)))
                # 子节点不可勾选（不设置 ItemIsUserCheckable）
                # 文件大小
                try:
                    size = os.path.getsize(file_path)
                    file_item.setText(1, self.format_size(size))
                    file_item.setForeground(1, QBrush(QColor(text_color)))
                except OSError as e:
                    print(f"getsize error: {e}")
                    file_item.setText(1, t("plugin.file_deduplicator.tree.unknown"))
                # 创建时间
                file_item.setText(2, get_create_time(file_path))
                file_item.setForeground(2, QBrush(QColor(text_color)))
                # 修改时间
                file_item.setText(3, get_modify_time(file_path))
                file_item.setForeground(3, QBrush(QColor(text_color)))
                total_duplicates += 1

            if is_checked:
                group_item.setCheckState(0, Qt.CheckState.Checked)

        self.stats_label.setText(
            t("plugin.file_deduplicator.msg.stats_duplicates",
              count=len(duplicates),
              total=total_duplicates,
              size=self.format_size(total_savings))
        )
        if hasattr(self, 'toggle_expand_btn'):
            self.toggle_expand_btn.setText(
                t("plugin.file_deduplicator.button.collapse")
            )
        # 扫描完成后，启用删除按钮
        self.delete_panel.btn.setEnabled(bool(duplicates))
        # 按默认规则排序并标记保留/删除（内部会展开全部）
        self._sort_by_rule()
        # 重放时在排序展开之后恢复用户原有展开状态
        if expanded_hashes is not None:
            for i in range(self.results_tree.topLevelItemCount()):
                item = self.results_tree.topLevelItem(i)
                item.setExpanded(
                    item.data(0, Qt.ItemDataRole.UserRole) in expanded_hashes
                )

    def checked_hashes(self):
        """返回当前勾选的重复组 hash 集合"""
        checked = set()
        for i in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                checked.add(item.data(0, Qt.ItemDataRole.UserRole))
        return checked

    def expanded_hashes(self):
        """返回当前处于展开状态的重复组 hash 集合"""
        expanded = set()
        for i in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(i)
            if item.isExpanded():
                expanded.add(item.data(0, Qt.ItemDataRole.UserRole))
        return expanded

    def _on_parent_checked(self, item, column):
        """父节点勾选状态变化，联动子节点背景色"""
        # 只处理父节点（顶级项），忽略子节点变化
        if item.parent() is not None:
            return
        # 只处理第0列（复选框所在列）
        if column != 0:
            return

        checked = item.checkState(0) == Qt.CheckState.Checked
        highlight = self.child_highlight_color if checked else self.child_normal_color
        for i in range(item.childCount()):
            child = item.child(i)
            child.setBackground(0, highlight)
            child.setBackground(1, highlight)
            child.setBackground(2, highlight)
            child.setBackground(3, highlight)

    def _select_all(self):
        """全选所有父节点"""
        for i in range(self.results_tree.topLevelItemCount()):
            parent = self.results_tree.topLevelItem(i)
            parent.setCheckState(0, Qt.CheckState.Checked)
            parent.setExpanded(True)

    def _deselect_all(self):
        """取消全选所有父节点"""
        for i in range(self.results_tree.topLevelItemCount()):
            parent = self.results_tree.topLevelItem(i)
            parent.setCheckState(0, Qt.CheckState.Unchecked)

    def _toggle_expand(self):
        """切换展开/折叠所有分组"""
        expanded = self.results_tree.topLevelItemCount() > 0 and self.results_tree.topLevelItem(0).isExpanded()
        if expanded:
            self.results_tree.collapseAll()
            self.toggle_expand_btn.setText(t("plugin.file_deduplicator.button.expand"))
        else:
            self.results_tree.expandAll()
            self.toggle_expand_btn.setText(t("plugin.file_deduplicator.button.collapse"))

    @staticmethod
    def _safe_stat_time(path, getter):
        """读取文件时间，失败时回退为 0，避免 OSError 从排序槽函数逃逸"""
        try:
            return getter(path)
        except OSError as exc:
            print(f"无法读取时间信息 {path}: {exc}")
            return 0.0

    def _get_sorted_files(self, file_list, rule):
        """按指定规则排序文件列表，返回排序后的列表"""
        if rule == 0:
            return sorted(file_list, key=lambda x: (
                self._safe_stat_time(x, os.path.getctime),
                self._safe_stat_time(x, os.path.getmtime),
                1 if self._has_copy_keyword(os.path.basename(x)) else 0
            ))
        elif rule == 1:
            return sorted(file_list, key=lambda x: (
                -self._safe_stat_time(x, os.path.getctime),
                -self._safe_stat_time(x, os.path.getmtime),
                1 if self._has_copy_keyword(os.path.basename(x)) else 0
            ))
        elif rule == 2:
            return sorted(file_list, key=lambda x: os.path.basename(x).lower())
        elif rule == 3:
            return sorted(file_list, key=lambda x: os.path.basename(x).lower(), reverse=True)
        elif rule == 4:
            return sorted(file_list, key=lambda x: (
                1 if self._has_copy_keyword(os.path.basename(x)) else 0,
                self._safe_stat_time(x, os.path.getctime),
                self._safe_stat_time(x, os.path.getmtime),
            ))
        elif rule == 5:
            return sorted(file_list, key=lambda x: (
                1 if self._has_copy_keyword(os.path.basename(x)) else 0,
                -self._safe_stat_time(x, os.path.getctime),
                -self._safe_stat_time(x, os.path.getmtime),
            ))
        return file_list

    def _sort_by_rule(self):
        """按当前选择的删除规则重排树节点，并标记保留/删除"""
        if not self.duplicates:
            return
        rule = self.rule_combo.currentData()
        theme = self.current_theme if hasattr(self, 'current_theme') else self.theme

        for i in range(self.results_tree.topLevelItemCount()):
            parent = self.results_tree.topLevelItem(i)
            file_hash = parent.data(0, Qt.ItemDataRole.UserRole)
            if file_hash not in self.duplicates:
                continue
            file_list = self.duplicates[file_hash]
            if len(file_list) <= 1:
                continue

            sorted_files = self._get_sorted_files(file_list, rule)

            # 收集现有子项（按 UserRole 中存的文件路径索引，不依赖显示前缀）
            child_map = {}
            for j in range(parent.childCount()):
                child = parent.child(j)
                child_map[child.data(0, Qt.ItemDataRole.UserRole)] = child

            # 按排序顺序重建子项顺序
            for idx, file_path in enumerate(sorted_files):
                child = child_map.get(file_path)
                if child is None:
                    continue
                # 移到第 idx 位
                parent.removeChild(child)
                parent.insertChild(idx, child)
                # 标记保留/删除
                if idx == 0:
                    child.setText(0, t(
                        "plugin.file_deduplicator.tree.keep", path=file_path
                    ))
                    child.setForeground(0, QBrush(QColor(theme['success'])))
                else:
                    child.setText(0, t(
                        "plugin.file_deduplicator.tree.delete", path=file_path
                    ))
                    child.setForeground(0, QBrush(QColor(theme['error'])))

        self.results_tree.expandAll()
        if hasattr(self, 'toggle_expand_btn'):
            self.toggle_expand_btn.setText(
                t("plugin.file_deduplicator.button.collapse")
            )

    def format_size(self, bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} TB"

    def _has_copy_keyword(self, filename):
        """检查文件名是否包含副本/备份关键字，返回 (是否包含, 优先级)"""
        keywords = [
            r'\(\d+\)',       # (1), (2), (3)...
            '_copy',
            '_backup',
            '-copy',
            '-backup',
            '_副本',
            '-副本',
            ' - 副本',
            '_备份',
            '-备份',
            '_copy_',
            '-copy-',
            '.temp',
        ]
        for kw in keywords:
            if re.search(kw, filename, re.IGNORECASE):
                return True
        return False

    def scan_finished(self, success, message):
        """扫描完成回调"""
        self.scan_panel.finish_task(message)
        self.scan_panel.btn.setEnabled(True)
        self._set_inputs_enabled(True)
        self.cancel_scan_btn.setVisible(False)
        if success:
            if not self.duplicates:
                show_info(
                    self,
                    t("plugin.file_deduplicator.dialog.done_title"),
                    t("plugin.file_deduplicator.msg.no_duplicates"),
                )
        else:
            show_error(
                self, t("plugin.file_deduplicator.dialog.error_title"), message
            )

    def show_error(self, error_msg):
        """显示错误"""
        self.scan_panel.update_status(error_msg)

    def delete_duplicates(self):
        """删除重复文件（只处理勾选的组）"""
        if not self.duplicates:
            show_warning(
                self,
                t("plugin.file_deduplicator.dialog.warning_title"),
                t("plugin.file_deduplicator.warning.nothing_to_delete"),
            )
            return

        # 收集待删除文件（只处理勾选的父节点）
        rule = self.rule_combo.currentData()
        files_to_delete = []

        for i in range(self.results_tree.topLevelItemCount()):
            parent = self.results_tree.topLevelItem(i)
            # 跳过未勾选的组
            if parent.checkState(0) != Qt.CheckState.Checked:
                continue
            # 从item的UserRole数据中获取hash
            file_hash = parent.data(0, Qt.ItemDataRole.UserRole)
            if file_hash not in self.duplicates:
                continue
            file_list = self.duplicates[file_hash]
            if len(file_list) <= 1:
                continue
            # 按规则排序
            sorted_files = self._get_sorted_files(file_list, rule)
            # 保留第一个，删除后续
            files_to_delete.extend(sorted_files[1:])

        if not files_to_delete:
            show_info(
                self,
                t("plugin.file_deduplicator.dialog.hint_title"),
                t("plugin.file_deduplicator.msg.nothing_to_delete"),
            )
            return

        # 确认删除对话框
        confirm_msg = t(
            "plugin.file_deduplicator.msg.confirm_intro", count=len(files_to_delete)
        )
        confirm_msg += t(
            "plugin.file_deduplicator.msg.confirm_rule",
            rule=self.rule_combo.currentText()
        )
        confirm_msg += t("plugin.file_deduplicator.msg.confirm_file_list_header")
        for i, file in enumerate(files_to_delete[:10]):
            confirm_msg += f"{i+1}. {file}\n"
        if len(files_to_delete) > 10:
            confirm_msg += t(
                "plugin.file_deduplicator.msg.confirm_more_files",
                count=len(files_to_delete) - 10
            )
        confirm_msg += t("plugin.file_deduplicator.msg.confirm_irreversible")
        if self.use_trash_checkbox.isChecked():
            confirm_msg += t("plugin.file_deduplicator.msg.confirm_trash_note")

        reply = show_question(
            self, t("plugin.file_deduplicator.dialog.confirm_delete"), confirm_msg
        )

        if reply:
            # 执行删除（后台 Worker，避免 UI 冻结；防重入）
            if self._is_busy():
                show_warning(
                    self,
                    t("plugin.file_deduplicator.dialog.warning_title"),
                    t("plugin.file_deduplicator.warning.scanning_in_progress"),
                )
                return
            self.delete_panel.start_task(
                maximum=len(files_to_delete),
                status=t("plugin.file_deduplicator.msg.deleting")
            )
            self.delete_panel.btn.setEnabled(False)
            self.scan_panel.btn.setEnabled(False)
            self._set_inputs_enabled(False)
            self.worker = FileDeletionWorker(
                files_to_delete,
                self.selected_folder,
                expected_sizes=self.scan_sizes,
                use_trash=self.use_trash_checkbox.isChecked(),
            )
            self.worker.progress.connect(self.update_delete_progress)
            self.worker.status.connect(self.update_status)
            self.worker.result.connect(self.delete_finished)
            self.worker.start()

    def update_delete_progress(self, done, total):
        """更新删除进度条"""
        if total > 0:
            self.delete_panel.progress.setMaximum(total)
            self.delete_panel.progress.setValue(done)
            self.delete_panel.update_status(
                t("plugin.file_deduplicator.msg.deleting_progress",
                  count=done, total=total)
            )

    def delete_finished(self, success, message):
        """删除完成回调"""
        self.delete_panel.finish_task(message)
        self.scan_panel.btn.setEnabled(True)
        self._set_inputs_enabled(True)
        show_info(
            self,
            t("plugin.file_deduplicator.dialog.delete_result"),
            message,
        )
        # 根据勾选状态决定是否自动重新扫描
        if self.auto_rescan_checkbox.isChecked():
            self.start_scan()
        else:
            # 清空重复文件列表和扫描信息（避免数据不对应）
            self.results_tree.clear()
            self.duplicates = {}
            self.stats_label.setText(
                t("plugin.file_deduplicator.msg.deleted_rescan")
            )
            self.delete_panel.btn.setEnabled(False)


class FileDeduplicator(ToolPlugin):
    """文件去重插件"""

    def update_theme(self, theme):
        """更新主题"""
        if hasattr(self, 'widget') and hasattr(self.widget, 'apply_theme'):
            self.widget.apply_theme(theme)

    def create_ui(self):
        """创建UI"""
        self.widget = FileDeduplicatorWidget(icon=self.icon, name=self.name, description=self.description, theme=Theme.DARK)
        # 将 Widget 的标签属性复制到插件实例，统一访问入口
        self.title_label = self.widget.title_label
        self.desc_label = self.widget.desc_label
        return self.widget

    def retranslate_ui(self):
        """语言切换后重放文件去重页全部静态文本"""
        widget = getattr(self, 'widget', None)
        if widget is None:
            return

        widget.title_label.setText(f"{widget.icon} {t('plugin.file_deduplicator.name')}")
        widget.desc_label.setText(t("plugin.file_deduplicator.description"))
        widget.folder_card.title_label.setText(
            t("plugin.file_deduplicator.card.select_folder")
        )
        widget.folder_display.setPlaceholderText(
            t("plugin.file_deduplicator.placeholder.folder")
        )
        widget.browse_btn.setText(t("plugin.file_deduplicator.button.browse"))
        widget.scan_panel.btn.setText(t("plugin.file_deduplicator.button.scan"))
        widget.cancel_scan_btn.setText(
            t("plugin.file_deduplicator.button.cancel_scan")
        )
        widget.scan_panel.status_label.setText(
            t("plugin.file_deduplicator.msg.select_folder_hint")
        )
        widget.results_card.title_label.setText(
            t("plugin.file_deduplicator.card.results")
        )
        widget.results_tree.setHeaderLabels([
            t("plugin.file_deduplicator.column.file_info"),
            t("plugin.file_deduplicator.column.size"),
            t("plugin.file_deduplicator.column.created"),
            t("plugin.file_deduplicator.column.modified"),
        ])
        widget.stats_label.setText(
            t("plugin.file_deduplicator.msg.not_scanned")
        )
        widget.deletion_card.title_label.setText(
            t("plugin.file_deduplicator.card.deletion_rules")
        )
        widget.rule_label.setText(t("plugin.file_deduplicator.label.rule"))
        widget.auto_rescan_label.setText(
            t("plugin.file_deduplicator.label.auto_rescan")
        )
        trash_label = t("plugin.file_deduplicator.label.use_trash")
        if not SEND2TRASH_AVAILABLE:
            trash_label += t("plugin.file_deduplicator.msg.trash_unavailable")
        widget.use_trash_label.setText(trash_label)
        widget.select_all_btn.setText(
            t("plugin.file_deduplicator.button.select_all")
        )
        widget.deselect_all_btn.setText(
            t("plugin.file_deduplicator.button.deselect_all")
        )
        widget.sort_by_rule_btn.setText(
            t("plugin.file_deduplicator.button.sort_by_rule")
        )
        widget.delete_panel.btn.setText(
            t("plugin.file_deduplicator.button.delete_duplicates")
        )
        # 组合框由 bind_combo 自动重放

        # 结果树中的分组标签与保留/删除前缀：有数据时按当前语言重建，
        # 同时保留用户已勾选的组与展开状态
        if widget.duplicates:
            widget.show_duplicates(
                widget.duplicates,
                checked_hashes=widget.checked_hashes(),
                expanded_hashes=widget.expanded_hashes(),
            )

        # 展开/折叠按钮文字跟随当前树状态
        tree = widget.results_tree
        expanded = (
            tree.topLevelItemCount() > 0 and tree.topLevelItem(0).isExpanded()
        )
        widget.toggle_expand_btn.setText(
            t("plugin.file_deduplicator.button.expand") if not expanded
            else t("plugin.file_deduplicator.button.collapse")
        )
