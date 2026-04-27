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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QProgressBar, QMessageBox, QComboBox, QTreeWidget, QTreeWidgetItem,
    QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# 导入主程序中的ToolPlugin基类和相关组件
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin, Card, AnimatedButton, TITLE_STYLES, FONT_SIZE_12, FONT_SIZE_16, FONT_SIZE_20, FONT_WEIGHT_600, FONT_WEIGHT_700, FONT_WEIGHT_800
except ImportError:
    # 如果导入失败，定义简化的基类
    class ToolPlugin:
        name = "Base Tool"
        icon = "🔧"

        def create_ui(self):
            raise NotImplementedError("Subclasses must implement create_ui()")

    class Card:
        def __init__(self, parent=None, title=""):
            self.content_layout = QVBoxLayout()

    class AnimatedButton:
        def __init__(self, *args, **kwargs):
            pass


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
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标题
        self.title_label = QLabel("🗑️ 文件去重工具")
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        layout.addWidget(self.title_label)

        # 描述
        self.desc_label = QLabel("按内容Hash查找重复文件，支持预览后选择规则删除")
        self.desc_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.desc_label)

        # 文件夹选择卡片
        folder_card = Card(title="选择扫描文件夹")
        folder_layout = QHBoxLayout()
        self.folder_display = QLineEdit()
        self.folder_display.setPlaceholderText("选择要扫描的文件夹...")
        self.folder_display.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        self.browse_btn = AnimatedButton("浏览")
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.folder_display)
        folder_layout.addWidget(self.browse_btn)
        folder_card.content_layout.addLayout(folder_layout)

        # 扫描按钮
        self.scan_btn = AnimatedButton("开始扫描")
        self.scan_btn.setMinimumHeight(48)
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #2563eb);
                color: white; border: none; border-radius: 8px;
                font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #60a5fa, stop:1 #3b82f6);
            }}
            QPushButton:disabled {{ background: #334155; color: #64748b; }}
        """)
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setEnabled(False)
        folder_card.content_layout.addWidget(self.scan_btn)
        layout.addWidget(folder_card)

        # 进度卡片
        progress_card = Card(title="扫描进度")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0f172a;
                border-radius: 6px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 6px;
            }
        """)
        progress_card.content_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("请选择文件夹开始扫描")
        self.status_label.setStyleSheet("color: #94a3b8;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_card.content_layout.addWidget(self.status_label)

        self.cancel_btn = AnimatedButton("取消扫描")
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: #ef4444;
                color: white; border: none; border-radius: 8px;
                font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{ background: #f87171; }}
            QPushButton:disabled {{ background: #334155; color: #64748b; }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_scan)
        self.cancel_btn.setVisible(False)
        progress_card.content_layout.addWidget(self.cancel_btn)
        layout.addWidget(progress_card)

        # 结果卡片
        results_card = Card(title="重复文件列表")
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["文件信息", "大小", "修改时间"])
        self.results_tree.setColumnWidth(0, 400)
        self.results_tree.setColumnWidth(1, 100)
        self.results_tree.setColumnWidth(2, 200)
        self.results_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f1f5f9;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 6px;
            }
            QTreeWidget::item:selected {
                background-color: #3b82f6;
            }
        """)
        results_card.content_layout.addWidget(self.results_tree)

        # 统计标签
        self.stats_label = QLabel("未扫描")
        self.stats_label.setStyleSheet(f"color: #94a3b8; font-size: {FONT_SIZE_12};")
        results_card.content_layout.addWidget(self.stats_label)
        layout.addWidget(results_card)

        # 删除规则卡片
        deletion_card = Card(title="删除规则设置")
        deletion_layout = QHBoxLayout()
        deletion_layout.addWidget(QLabel("删除规则:"))
        self.rule_combo = QComboBox()
        self.rule_combo.addItems([
            "按文件名升序排序（A→Z，保留首个，删除后续）",
            "按修改时间升序排序（旧→新，保留首个，删除后续）",
            "按修改时间降序排序（新→旧，保留首个，删除后续）"
        ])
        self.rule_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        deletion_layout.addWidget(self.rule_combo)
        deletion_layout.addStretch()
        deletion_card.content_layout.addLayout(deletion_layout)

        # 删除按钮
        self.delete_btn = AnimatedButton("删除重复文件")
        self.delete_btn.setMinimumHeight(48)
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ef4444, stop:1 #dc2626);
                color: white; border: none; border-radius: 8px;
                font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f87171, stop:1 #ef4444);
            }}
            QPushButton:disabled {{ background: #334155; color: #64748b; }}
        """)
        self.delete_btn.clicked.connect(self.delete_duplicates)
        self.delete_btn.setEnabled(False)
        deletion_card.content_layout.addWidget(self.delete_btn)
        layout.addWidget(deletion_card)

        layout.addStretch()

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
            self.scan_btn.setEnabled(True)
            self.status_label.setText(f"已选择文件夹: {dir_path}")

    def start_scan(self):
        """开始扫描"""
        if not self.selected_folder or not os.path.exists(self.selected_folder):
            QMessageBox.warning(self, "警告", "请先选择有效的文件夹！")
            return

        self.scan_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在扫描...")
        self.results_tree.clear()
        self.stats_label.setText("扫描中...")
        self.delete_btn.setEnabled(False)
        self.duplicates = {}

        self.worker = FileDeduplicationWorker(self.selected_folder)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.duplicates_found.connect(self.show_duplicates)
        self.worker.finished.connect(self.scan_finished)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def cancel_scan(self):
        """取消扫描"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            self.status_label.setText("扫描已取消")
            self.scan_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            self.progress_bar.setVisible(False)

    def update_progress(self, scanned, total):
        """更新进度条"""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(scanned)
            self.status_label.setText(f"已扫描 {scanned}/{total} 个文件...")

    def update_status(self, message):
        """更新状态标签"""
        self.status_label.setText(message)

    def show_duplicates(self, duplicates):
        """显示重复文件"""
        self.duplicates = duplicates
        self.results_tree.clear()
        total_duplicates = 0
        total_savings = 0

        for file_hash, file_list in duplicates.items():
            # 创建重复组顶级项
            group_item = QTreeWidgetItem(self.results_tree)
            group_item.setText(0, f"重复组: {file_hash[:8]}... (共 {len(file_list)} 个文件)")
            group_item.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            group_item.setBackground(0, Qt.GlobalColor.darkBlue)

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
                # 文件大小
                try:
                    size = os.path.getsize(file_path)
                    file_item.setText(1, self.format_size(size))
                except:
                    file_item.setText(1, "未知")
                # 修改时间
                try:
                    mtime = os.path.getmtime(file_path)
                    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                    file_item.setText(2, time_str)
                except:
                    file_item.setText(2, "未知")
                total_duplicates += 1

        self.stats_label.setText(
            f"找到 {len(duplicates)} 组重复文件，共 {total_duplicates} 个重复文件，可节省空间: {self.format_size(total_savings)}"
        )
        self.delete_btn.setEnabled(True)

    def format_size(self, bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} TB"

    def scan_finished(self, success, message):
        """扫描完成回调"""
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.scan_btn.setEnabled(True)
        if success:
            self.status_label.setText(message)
            if not self.duplicates:
                QMessageBox.information(self, "完成", "未找到重复文件")
        else:
            self.status_label.setText("扫描失败")
            QMessageBox.critical(self, "错误", message)

    def show_error(self, error_msg):
        """显示错误"""
        self.status_label.setText(error_msg)

    def delete_duplicates(self):
        """删除重复文件"""
        if not self.duplicates:
            QMessageBox.warning(self, "警告", "没有可删除的重复文件！")
            return

        # 根据规则收集待删除文件
        rule = self.rule_combo.currentIndex()
        files_to_delete = []

        for file_hash, file_list in self.duplicates.items():
            if len(file_list) <= 1:
                continue
            # 按规则排序
            if rule == 0:  # 文件名升序
                sorted_files = sorted(file_list, key=lambda x: os.path.basename(x).lower())
            elif rule == 1:  # 修改时间升序（旧→新）
                sorted_files = sorted(file_list, key=lambda x: os.path.getmtime(x))
            else:  # 修改时间降序（新→旧）
                sorted_files = sorted(file_list, key=lambda x: os.path.getmtime(x), reverse=True)
            # 保留第一个，删除后续
            files_to_delete.extend(sorted_files[1:])

        if not files_to_delete:
            QMessageBox.information(self, "提示", "没有需要删除的文件")
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

        reply = QMessageBox.question(
            self,
            "确认删除",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 执行删除
            deleted = 0
            failed = 0
            failed_files = []
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted += 1
                except Exception as e:
                    failed += 1
                    failed_files.append(f"{file_path}: {str(e)}")

            # 显示结果
            result_msg = f"删除完成: 成功 {deleted} 个，失败 {failed} 个"
            if failed_files:
                result_msg += "\n\n失败文件:\n" + "\n".join(failed_files[:5])
                if len(failed_files) > 5:
                    result_msg += f"\n... 还有 {len(failed_files)-5} 个失败文件"
            QMessageBox.information(self, "删除结果", result_msg)
            # 重新扫描刷新结果
            self.start_scan()


class FileDeduplicator(ToolPlugin):
    """文件去重插件"""
    icon = "🗑️"
    name = "文件去重"

    def update_theme(self, theme):
        """更新主题"""
        if not hasattr(self, 'widget'):
            return
        w = self.widget

        # 标题和描述
        if hasattr(w, 'title_label'):
            w.title_label.setStyleSheet(
                f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700}; color: {theme['text']};"
            )
        if hasattr(w, 'desc_label'):
            w.desc_label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: 13px;"
            )

        # 文件夹输入框
        if hasattr(w, 'folder_display'):
            w.folder_display.setStyleSheet(f"""
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

        # 扫描按钮
        if hasattr(w, 'scan_btn'):
            w.scan_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {theme['primary']}, stop:1 {theme['primary_hover']});
                    color: white; border: none; border-radius: 8px;
                    font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {theme['primary_hover']}, stop:1 {theme['primary']});
                }}
                QPushButton:disabled {{ background: {theme['surface']}; color: {theme['text_secondary']}; }}
            """)

        # 进度条
        if hasattr(w, 'progress_bar'):
            w.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {theme['bg']};
                    border-radius: 6px;
                    text-align: center;
                    color: {theme['text']};
                }}
                QProgressBar::chunk {{
                    background-color: {theme['primary']};
                    border-radius: 6px;
                }}
            """)

        # 状态标签
        if hasattr(w, 'status_label'):
            w.status_label.setStyleSheet(f"color: {theme['text_secondary']};")
            w.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 取消按钮
        if hasattr(w, 'cancel_btn'):
            w.cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {theme['error']};
                    color: white; border: none; border-radius: 8px;
                    font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};
                }}
                QPushButton:hover {{ background: {theme['error']}cc; }}
                QPushButton:disabled {{ background: {theme['surface']}; color: {theme['text_secondary']}; }}
            """)

        # 结果树状列表
        if hasattr(w, 'results_tree'):
            w.results_tree.setStyleSheet(f"""
                QTreeWidget {{
                    background-color: {theme['bg']};
                    border: 1px solid {theme['border']};
                    border-radius: 6px;
                    color: {theme['text']};
                    padding: 4px;
                }}
                QTreeWidget::item {{
                    padding: 6px;
                }}
                QTreeWidget::item:selected {{
                    background-color: {theme['primary']};
                }}
                QTreeWidget::item:hover {{
                    background-color: {theme['surface']};
                }}
            """)

        # 统计标签
        if hasattr(w, 'stats_label'):
            w.stats_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_12};")

        # 下拉框
        if hasattr(w, 'rule_combo'):
            w.rule_combo.setStyleSheet(f"""
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

        # 删除按钮
        if hasattr(w, 'delete_btn'):
            w.delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {theme['error']}, stop:1 {theme['error']}cc);
                    color: white; border: none; border-radius: 8px;
                    font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {theme['error']}cc, stop:1 {theme['error']});
                }}
                QPushButton:disabled {{ background: {theme['surface']}; color: {theme['text_secondary']}; }}
            """)

    def create_ui(self):
        """创建UI"""
        self.widget = FileDeduplicatorWidget()
        return self.widget
