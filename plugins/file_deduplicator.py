"""
文件去重工具插件
按内容Hash查找重复文件，支持预览后选择规则删除
"""
import os
import sys
import hashlib
import time
from collections import defaultdict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QLineEdit, QHBoxLayout
)

from toolbox import ToolPlugin, Card, AnimatedButton, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, FONT_WEIGHT_700, Theme
from common.message_utils import show_info, show_error, show_warning, show_question
from common.action_panel import ActionPanel
from common.utils import get_create_time, get_modify_time

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QBrush
from PyQt6.QtWidgets import QSizePolicy


class FileDeduplicationWorker(QThread):
    """文件去重工作线程"""
    progress = pyqtSignal(int, int)  # 已扫描文件数, 总文件数
    status = pyqtSignal(str)
    duplicates_found = pyqtSignal(dict)  # {hash: [file_paths]}
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.cancel_requested = False

    def run(self):
        try:
            self.status.emit("正在扫描文件夹...")
            # 第一遍：收集所有文件
            all_files = []
            for root, dirs, files in os.walk(self.folder_path):
                if self.cancel_requested:
                    self.finished.emit(False, "扫描已取消")
                    return
                for file in files:
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)
            total_files = len(all_files)
            self.status.emit(f"找到 {total_files} 个文件，开始计算Hash...")

            # 第二遍：计算每个文件的Hash
            hash_to_files = defaultdict(list)
            scanned = 0
            for file_path in all_files:
                if self.cancel_requested:
                    self.finished.emit(False, "扫描已取消")
                    return
                try:
                    file_hash = self.compute_file_hash(file_path)
                    if file_hash:
                        hash_to_files[file_hash].append(file_path)
                except Exception as e:
                    self.error.emit(f"无法读取文件 {file_path}: {str(e)}")
                scanned += 1
                self.progress.emit(scanned, total_files)

            # 过滤出重复文件（Hash对应多个文件）
            duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
            self.duplicates_found.emit(duplicates)
            self.finished.emit(True, f"扫描完成，找到 {len(duplicates)} 组重复文件")
        except Exception as e:
            self.finished.emit(False, f"扫描失败: {str(e)}")

    def compute_file_hash(self, file_path, chunk_size=65536):
        """计算文件的SHA-256哈希值"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    if self.cancel_requested:
                        return None
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return None

    def cancel(self):
        self.cancel_requested = True


class FileDeduplicatorWidget(QWidget):
    """文件去重工具主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_folder = ""
        self.worker = None
        self.duplicates = {}  # {hash: [file_paths]}
        self.setup_ui()

    def setup_ui(self):
        self.group_bg_color = QColor('#334155')  # 默认分组背景色，apply_theme 会覆盖
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标题
        self.title_label = QLabel("🗑️ 文件去重工具")
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        layout.addWidget(self.title_label)

        # 描述
        self.desc_label = QLabel("按内容Hash查找重复文件，支持预览后选择规则删除")
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # 文件夹选择卡片
        folder_card = Card(title="选择扫描文件夹")
        folder_layout = QHBoxLayout()
        self.folder_display = QLineEdit()
        self.folder_display.setPlaceholderText("选择要扫描的文件夹...")
        folder_layout.addWidget(self.folder_display)

        self.browse_btn = AnimatedButton("浏览")
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.browse_btn)
        folder_card.content_layout.addLayout(folder_layout)

        # 扫描操作面板（按钮 + 进度条 + 状态）
        self.scan_panel = ActionPanel(
            button_text="开始扫描",
            use_gradient=True,
            status_text="请选择文件夹开始扫描"
        )
        self.scan_panel.clicked.connect(self.start_scan)
        self.scan_panel.btn.setEnabled(False)
        folder_card.content_layout.addWidget(self.scan_panel)

        layout.addWidget(folder_card)

        # 结果卡片
        results_card = Card(title="重复文件列表")
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["文件信息", "大小", "创建时间", "修改时间"])
        self.results_tree.setColumnWidth(0, 580)
        self.results_tree.setColumnWidth(1, 80)
        self.results_tree.setColumnWidth(2, 140)
        self.results_tree.setColumnWidth(3, 140)
        self.results_tree.setMinimumHeight(400)
        self.results_tree.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        results_card.content_layout.addWidget(self.results_tree)

        # 统计标签
        self.stats_label = QLabel("未扫描")
        self.stats_label.setStyleSheet(f"color: #94a3b8; font-size: {FONT_SIZE_14};")
        results_card.content_layout.addWidget(self.stats_label)
        layout.addWidget(results_card)

        # 删除规则卡片
        deletion_card = Card(title="删除规则设置")
        deletion_layout = QHBoxLayout()
        deletion_layout.addWidget(QLabel("删除规则:"))
        self.rule_combo = QComboBox()
        self.rule_combo.addItems([
            "按创建时间升序排序（旧→新，保留首个，删除后续）",
            "按创建时间降序排序（新→旧，保留首个，删除后续）",
            "按文件名升序排序（A→Z，保留首个，删除后续）",
            "按文件名降序排序（Z→A，保留首个，删除后续）"
        ])
        deletion_layout.addWidget(self.rule_combo, 1)
        deletion_card.content_layout.addLayout(deletion_layout)

        # 全选/取消全选按钮
        select_btn_layout = QHBoxLayout()
        self.select_all_btn = AnimatedButton("全选")
        self.select_all_btn.setMaximumWidth(80)
        self.select_all_btn.clicked.connect(self._select_all)
        select_btn_layout.addWidget(self.select_all_btn)
        self.deselect_all_btn = AnimatedButton("取消全选")
        self.deselect_all_btn.setMaximumWidth(80)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        select_btn_layout.addWidget(self.deselect_all_btn)
        select_btn_layout.addStretch()
        deletion_card.content_layout.addLayout(select_btn_layout)

        # 连接父节点勾选变化信号
        self.results_tree.itemChanged.connect(self._on_parent_checked)

        # 删除操作面板
        self.delete_panel = ActionPanel(
            button_text="删除重复文件",
            use_gradient=True,
            gradient_colors=(Theme.DARK['error'], Theme.DARK['error_gradient_end']),
            gradient_hover_colors=(Theme.DARK['error_hover'], Theme.DARK['error_gradient_end']),
        )
        self.delete_panel.clicked.connect(self.delete_duplicates)
        self.delete_panel.btn.setEnabled(False)
        deletion_card.content_layout.addWidget(self.delete_panel)

        layout.addWidget(deletion_card)

        layout.addStretch()

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
            self.rule_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {theme['bg']};
                    border: 1px solid {theme['border']};
                    border-radius: 6px;
                    padding: 6px;
                    color: {theme['text']};
                }}
                QComboBox::drop-down {{
                    border: none;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {theme['bg_secondary']};
                    color: {theme['text']};
                    selection-background-color: {theme['primary']};
                }}
            """)

        # 存储当前主题供 show_duplicates 使用
        self.current_theme = theme

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
            from PyQt6.QtGui import QBrush
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
            "选择要扫描的文件夹",
            self.selected_folder if self.selected_folder else ""
        )
        if dir_path:
            self.selected_folder = dir_path
            self.folder_display.setText(dir_path)
            self.scan_panel.btn.setEnabled(True)
            self.scan_panel.update_status(f"已选择文件夹: {dir_path}")

    def start_scan(self):
        """开始扫描"""
        if not self.selected_folder or not os.path.exists(self.selected_folder):
            show_warning(self, "警告", "请先选择有效的文件夹！")
            return

        self.scan_panel.btn.setEnabled(False)
        self.scan_panel.start_task(maximum=0, status="正在扫描...")
        self.results_tree.clear()
        self.stats_label.setText("扫描中...")
        self.delete_panel.btn.setEnabled(False)
        self.duplicates = {}

        self.worker = FileDeduplicationWorker(self.selected_folder)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.duplicates_found.connect(self.show_duplicates)
        self.worker.finished.connect(self.scan_finished)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def update_progress(self, scanned, total):
        """更新进度条"""
        if total > 0:
            self.scan_panel.progress.setMaximum(total)
            self.scan_panel.progress.setValue(scanned)
            self.scan_panel.update_status(f"已扫描 {scanned}/{total} 个文件...")

    def update_status(self, message):
        """更新状态标签"""
        self.scan_panel.update_status(message)

    def show_duplicates(self, duplicates):
        """显示重复文件"""
        self.duplicates = duplicates
        self.results_tree.clear()
        total_duplicates = 0
        total_savings = 0

        # 获取当前主题的文字颜色
        text_color = self.current_theme['text'] if hasattr(self, 'current_theme') else '#f1f5f9'

        for file_hash, file_list in duplicates.items():
            # 创建重复组顶级项（父节点，可勾选）
            group_item = QTreeWidgetItem(self.results_tree)
            group_item.setText(0, f"重复组: {file_hash[:8]}... (共 {len(file_list)} 个文件)")
            group_item.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            group_item.setBackground(0, self.group_bg_color)
            group_item.setForeground(0, QBrush(QColor(text_color)))
            # 设置父节点可勾选
            group_item.setFlags(group_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            group_item.setCheckState(0, Qt.CheckState.Unchecked)
            # 存储hash到item中，方便删除时查找
            group_item.setData(0, Qt.ItemDataRole.UserRole, file_hash)

            # 计算该组可节省空间
            if file_list:
                try:
                    file_size = os.path.getsize(file_list[0])
                    total_savings += file_size * (len(file_list) - 1)
                except:
                    pass

            for file_path in file_list:
                file_item = QTreeWidgetItem(group_item)
                file_item.setText(0, file_path)
                file_item.setForeground(0, QBrush(QColor(text_color)))
                # 子节点不可勾选（不设置 ItemIsUserCheckable）
                # 文件大小
                try:
                    size = os.path.getsize(file_path)
                    file_item.setText(1, self.format_size(size))
                    file_item.setForeground(1, QBrush(QColor(text_color)))
                except:
                    file_item.setText(1, "未知")
                # 创建时间
                file_item.setText(2, get_create_time(file_path))
                file_item.setForeground(2, QBrush(QColor(text_color)))
                # 修改时间
                file_item.setText(3, get_modify_time(file_path))
                file_item.setForeground(3, QBrush(QColor(text_color)))
                total_duplicates += 1

        self.stats_label.setText(
            f"找到 {len(duplicates)} 组重复文件，共 {total_duplicates} 个重复文件，可节省空间: {self.format_size(total_savings)}"
        )
        # 扫描完成后，启用删除按钮
        self.delete_panel.btn.setEnabled(bool(duplicates))

    def _on_parent_checked(self, item, column):
        """父节点勾选状态变化，联动子节点背景色"""
        # 只处理父节点（顶级项），忽略子节点变化
        if item.parent() is not None:
            return
        # 只处理第0列（复选框所在列）
        if column != 0:
            return

        from PyQt6.QtGui import QBrush
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
            parent.setExpanded(False)

    def format_size(self, bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} TB"

    def scan_finished(self, success, message):
        """扫描完成回调"""
        self.scan_panel.finish_task(message)
        self.scan_panel.btn.setEnabled(True)
        if success:
            if not self.duplicates:
                show_info(self, "完成", "未找到重复文件")
        else:
            show_error(self, "错误", message)

    def show_error(self, error_msg):
        """显示错误"""
        self.scan_panel.update_status(error_msg)

    def delete_duplicates(self):
        """删除重复文件（只处理勾选的组）"""
        if not self.duplicates:
            show_warning(self, "警告", "没有可删除的重复文件！")
            return

        # 收集待删除文件（只处理勾选的父节点）
        rule = self.rule_combo.currentIndex()
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
            if rule == 0:  # 创建时间升序（旧→新）
                sorted_files = sorted(file_list, key=lambda x: os.path.getctime(x))
            elif rule == 1:  # 创建时间降序（新→旧）
                sorted_files = sorted(file_list, key=lambda x: os.path.getctime(x), reverse=True)
            elif rule == 2:  # 文件名升序
                sorted_files = sorted(file_list, key=lambda x: os.path.basename(x).lower())
            else:  # 文件名降序
                sorted_files = sorted(file_list, key=lambda x: os.path.basename(x).lower(), reverse=True)
            # 保留第一个，删除后续
            files_to_delete.extend(sorted_files[1:])

        if not files_to_delete:
            show_info(self, "提示", "没有需要删除的文件")
            return

        # 确认删除对话框
        confirm_msg = f"即将删除 {len(files_to_delete)} 个重复文件，是否继续？\n\n"
        confirm_msg += f"删除规则: {self.rule_combo.currentText()}\n\n"
        confirm_msg += "删除文件列表（前10个）:\n"
        for i, file in enumerate(files_to_delete[:10]):
            confirm_msg += f"{i+1}. {file}\n"
        if len(files_to_delete) > 10:
            confirm_msg += f"... 还有 {len(files_to_delete)-10} 个文件未显示\n"
        confirm_msg += "\n此操作不可恢复，请确认！"

        reply = show_question(self, "确认删除", confirm_msg)

        if reply:
            # 执行删除
            self.delete_panel.start_task(maximum=len(files_to_delete), status="正在删除...")
            deleted = 0
            failed = 0
            failed_files = []
            for i, file_path in enumerate(files_to_delete):
                try:
                    os.remove(file_path)
                    deleted += 1
                except Exception as e:
                    failed += 1
                    failed_files.append(f"{file_path}: {str(e)}")
                self.delete_panel.update_progress(i + 1)

            # 显示结果
            result_msg = f"删除完成: 成功 {deleted} 个，失败 {failed} 个"
            if failed_files:
                result_msg += "\n\n失败文件:\n" + "\n".join(failed_files[:5])
                if len(failed_files) > 5:
                    result_msg += f"\n... 还有 {len(failed_files)-5} 个失败文件"
            self.delete_panel.finish_task(result_msg)
            show_info(self, "删除结果", result_msg)
            # 重新扫描刷新结果
            self.start_scan()


class FileDeduplicator(ToolPlugin):
    """文件去重插件"""
    icon = "🗑️"
    name = "文件去重"
    order = 200

    def update_theme(self, theme):
        """更新主题"""
        if hasattr(self, 'widget') and hasattr(self.widget, 'apply_theme'):
            self.widget.apply_theme(theme)

    def create_ui(self):
        """创建UI"""
        self.widget = FileDeduplicatorWidget()
        return self.widget
