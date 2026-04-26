"""
PDF合并工具插件
将多个PDF文件合并为一个PDF文件，支持拖拽和顺序调整
"""
import os
import sys
from pathlib import Path
from typing import List

# 导入PyMuPDF用于PDF合并
try:
    import fitz

    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

# 导入主程序中的ToolPlugin基类和相关组件
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin, Card, AnimatedButton, DragDropHandler
except ImportError:
    # 如果导入失败，定义简化的基类
    class ToolPlugin:
        name = "Base Tool"
        icon = "🔧"

        def create_ui(self):
            raise NotImplementedError("Subclasses must implement create_ui()")

    class Card:
        def __init__(self, parent=None, title=""):
            pass

    class AnimatedButton:
        def __init__(self, *args, **kwargs):
            pass

    class DragDropHandler:
        @staticmethod
        def setup_drag_drop(widget, files_list):
            pass

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class PDFMergeWorker(QThread):
    """PDF合并工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, input_files: List[str], output_path: str):
        super().__init__()
        self.input_files = input_files
        self.output_path = output_path

    def run(self):
        try:
            if not FITZ_AVAILABLE:
                self.finished.emit(False, "错误: 未安装PyMuPDF库，请运行: pip install PyMuPDF")
                return

            self.status.emit("正在准备合并...")

            # 创建一个新的PDF文档
            merged_doc = fitz.open()

            total = len(self.input_files)
            for i, pdf_path in enumerate(self.input_files):
                self.status.emit(f"正在处理: {os.path.basename(pdf_path)}")

                # 打开源PDF
                src_doc = fitz.open(pdf_path)

                # 插入到合并文档中
                merged_doc.insert_pdf(src_doc)

                # 关闭源文档
                src_doc.close()

                # 更新进度
                self.progress.emit(i + 1)

            # 保存合并后的文档
            self.status.emit("正在保存...")
            merged_doc.save(self.output_path)
            merged_doc.close()

            self.finished.emit(True, f"成功合并 {total} 个PDF文件！\n保存位置: {self.output_path}")

        except Exception as e:
            self.finished.emit(False, f"合并失败: {str(e)}")


class PDFMergerWidget(QWidget):
    """PDF合并工具主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_files = []
        self.worker = None
        self.setup_ui()

        # 检查PyMuPDF是否可用
        if not FITZ_AVAILABLE:
            self.status_label.setText("错误: 未安装PyMuPDF库，请运行: pip install PyMuPDF")
            self.merge_btn.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标题
        self.title_label = QLabel("📑 PDF合并工具")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(self.title_label)

        # 说明
        self.desc_label = QLabel("将多个PDF文件合并为一个，支持拖拽排序")
        self.desc_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.desc_label)

        # PDF文件列表区域
        file_card = Card(title="PDF文件列表（顺序即为合并顺序）")
        file_layout = file_card.content_layout

        # 使用QTableWidget显示文件列表
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["文件名", "大小", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                border: 2px dashed #334155;
                border-radius: 8px;
                color: #f1f5f9;
                gridline-color: #334155;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 8px;
                border: none;
                font-weight: 600;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAcceptDrops(True)

        # 设置拖拽事件
        self.table.dragEnterEvent = self.drag_enter_event
        self.table.dropEvent = self.drop_event

        file_layout.addWidget(self.table)

        # 按钮布局
        btn_layout = QHBoxLayout()
        self.add_btn = AnimatedButton("添加PDF")
        self.add_btn.clicked.connect(self.add_files)
        self.remove_btn = AnimatedButton("移除选中")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.up_btn = AnimatedButton("↑ 上移")
        self.up_btn.clicked.connect(self.move_up)
        self.down_btn = AnimatedButton("↓ 下移")
        self.down_btn.clicked.connect(self.move_down)
        self.clear_btn = AnimatedButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_files)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.up_btn)
        btn_layout.addWidget(self.down_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        layout.addWidget(file_card)

        # 输出设置
        output_card = Card(title="输出设置")
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择输出文件路径...")
        self.output_path.setStyleSheet("""
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
        self.browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        output_card.content_layout.addLayout(output_layout)
        layout.addWidget(output_card)

        # 操作区
        action_card = Card()
        button_layout = QHBoxLayout()

        self.merge_btn = AnimatedButton("开始合并")
        self.merge_btn.setMinimumHeight(48)
        self.merge_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white; border: none; border-radius: 8px;
                font-size: 16px; font-weight: 600;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #34d399, stop:1 #10b981); }
            QPushButton:disabled { background: #334155; color: #64748b; }
        """)
        self.merge_btn.clicked.connect(self.start_merge)
        self.merge_btn.setEnabled(False)
        button_layout.addWidget(self.merge_btn)

        self.cancel_btn = AnimatedButton("取消")
        self.cancel_btn.setMinimumHeight(48)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ef4444, stop:1 #dc2626);
                color: white; border: none; border-radius: 8px;
                font-size: 16px; font-weight: 600;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f87171, stop:1 #ef4444); }
            QPushButton:disabled { background: #334155; color: #64748b; }
        """)
        self.cancel_btn.clicked.connect(self.cancel_merge)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)

        action_card.content_layout.addLayout(button_layout)

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
                background-color: #10b981;
                border-radius: 6px;
            }
        """)
        action_card.content_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #94a3b8;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_card.content_layout.addWidget(self.status_label)

        layout.addWidget(action_card)
        layout.addStretch()

    def drag_enter_event(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否是PDF文件
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith('.pdf'):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def drop_event(self, event):
        """拖放下事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            added = False
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    # 检查是否是PDF文件
                    if file_path.lower().endswith('.pdf'):
                        if file_path not in self.input_files:
                            self.input_files.append(file_path)
                            added = True

            if added:
                self.update_table()
                self.update_merge_button()
                self.status_label.setText(f"已添加PDF文件，共 {len(self.input_files)} 个")

            event.acceptProposedAction()
        else:
            event.ignore()

    def add_files(self):
        """添加PDF文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择PDF文件",
            "",
            "PDF文件 (*.pdf);;所有文件 (*.*)"
        )

        if files:
            added = False
            for file in files:
                if file not in self.input_files:
                    self.input_files.append(file)
                    added = True

            if added:
                self.update_table()
                self.update_merge_button()
                self.status_label.setText(f"已添加PDF文件，共 {len(self.input_files)} 个")

    def remove_selected(self):
        """移除选中的文件"""
        indices = sorted(set([i.row() for i in self.table.selectedIndexes()]), reverse=True)
        if not indices:
            QMessageBox.warning(self, "警告", "请先选择要移除的文件！")
            return

        for i in indices:
            if 0 <= i < len(self.input_files):
                self.input_files.pop(i)

        self.update_table()
        self.update_merge_button()
        self.status_label.setText(f"已移除，剩余 {len(self.input_files)} 个文件")

    def move_up(self):
        """上移选中的文件"""
        row = self.table.currentRow()
        if row > 0:
            self.input_files[row], self.input_files[row - 1] = self.input_files[row - 1], self.input_files[row]
            self.update_table()
            self.table.selectRow(row - 1)

    def move_down(self):
        """下移选中的文件"""
        row = self.table.currentRow()
        if row < len(self.input_files) - 1:
            self.input_files[row], self.input_files[row + 1] = self.input_files[row + 1], self.input_files[row]
            self.update_table()
            self.table.selectRow(row + 1)

    def clear_files(self):
        """清空文件列表"""
        self.input_files.clear()
        self.update_table()
        self.update_merge_button()
        self.status_label.setText("已清空文件列表")

    def update_table(self):
        """更新表格显示"""
        self.table.setRowCount(len(self.input_files))
        for i, f in enumerate(self.input_files):
            name = os.path.basename(f)

            # 获取文件大小
            try:
                size = os.path.getsize(f)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
            except:
                size_str = "未知"

            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(size_str))
            self.table.setItem(i, 2, QTableWidgetItem("就绪"))

    def update_merge_button(self):
        """更新合并按钮状态"""
        self.merge_btn.setEnabled(len(self.input_files) >= 2 and bool(self.output_path.text()))

    def browse_output(self):
        """选择输出文件路径"""
        # 默认使用第一个输入文件的目录
        default_name = "merged.pdf"
        if self.input_files:
            default_dir = os.path.dirname(self.input_files[0])
            default_path = os.path.join(default_dir, default_name)
        else:
            default_path = default_name

        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存合并后的PDF",
            default_path,
            "PDF文件 (*.pdf)"
        )

        if path:
            if not path.endswith('.pdf'):
                path += '.pdf'
            self.output_path.setText(path)
            self.update_merge_button()

    def start_merge(self):
        """开始合并PDF"""
        if len(self.input_files) < 2:
            QMessageBox.warning(self, "警告", "请至少添加 2 个PDF文件！")
            return

        if not self.output_path.text():
            QMessageBox.warning(self, "警告", "请选择输出文件路径！")
            return

        if not FITZ_AVAILABLE:
            QMessageBox.critical(self, "错误", "请先安装 PyMuPDF: pip install PyMuPDF")
            return

        # 禁用按钮，显示进度条
        self.merge_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.input_files))
        self.progress_bar.setValue(0)
        self.status_label.setText("正在合并...")

        # 创建工作线程
        self.worker = PDFMergeWorker(
            self.input_files,
            self.output_path.text()
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.merge_finished)
        self.worker.start()

    def cancel_merge(self):
        """取消合并"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.status_label.setText("已取消")
            self.merge_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.progress_bar.setVisible(False)

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)

    def update_status(self, message):
        """更新状态标签"""
        self.status_label.setText(message)

    def merge_finished(self, success, message):
        """合并完成回调"""
        self.progress_bar.setVisible(False)
        self.merge_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if success:
            QMessageBox.information(self, "完成", message)
            self.status_label.setText("合并完成")
        else:
            QMessageBox.critical(self, "错误", message)
            self.status_label.setText("合并失败")


class PDFMerger(ToolPlugin):
    """PDF合并插件"""
    icon = "📑"
    name = "PDF合并"

    def update_theme(self, theme):
        """更新主题"""
        # 更新标题颜色
        if hasattr(self, 'widget') and hasattr(self.widget, 'title_label'):
            self.widget.title_label.setStyleSheet(
                f"font-size: 24px; font-weight: 700; color: {theme['text']};"
            )

        # 更新描述颜色
        if hasattr(self, 'widget') and hasattr(self.widget, 'desc_label'):
            self.widget.desc_label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: 13px;"
            )

    def create_ui(self):
        """创建UI"""
        self.widget = PDFMergerWidget()
        return self.widget
