"""
PDF合并工具插件
将多个PDF文件合并为一个PDF文件，支持拖拽和顺序调整
"""
import os
import sys
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
    from toolbox import ToolPlugin, Card, AnimatedButton, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, FONT_WEIGHT_700, Theme
except ImportError:
    # 如果导入失败，定义简化的基类
    Theme = None
    class ToolPlugin:
        name = "Base Tool"
        icon = "🔧"

        def __init__(self, parent=None):
            self.parent = parent
            self.widget = None

        def create_ui(self):
            raise NotImplementedError("Subclasses must implement create_ui()")

        def get_widget(self):
            if self.widget is None:
                self.widget = self.create_ui()
            return self.widget

    class Card:
        def __init__(self, parent=None, title=""):
            pass

    class AnimatedButton:
        def __init__(self, *args, **kwargs):
            pass

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QLineEdit
)

from common.message_utils import show_info, show_error, show_warning
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from common.file_list_panel import FileListPanel
from common.utils import get_create_time, get_file_size
from common.action_panel import ActionPanel


PDF_COLUMNS = [
    ("文件名", lambda f: os.path.basename(f)),
    ("大小", get_file_size),
    ("创建时间", get_create_time)
]


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
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        layout.addWidget(self.title_label)

        # 说明
        self.desc_label = QLabel("将多个PDF文件合并为一个，支持拖拽排序")
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # PDF文件列表区域
        file_card = Card(title="PDF文件列表（顺序即为合并顺序）")
        file_layout = file_card.content_layout

        self.file_panel = FileListPanel(
            columns=PDF_COLUMNS,
            file_filter="PDF文件 (*.pdf);;所有文件 (*.*)",
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear", "up", "down", "sort_name", "sort_time"]
        )

        # 调整"创建时间"列宽（完整显示 "YYYY-MM-DD HH:MM" 需要约 140px）
        header = self.file_panel.table.horizontalHeader()
        create_time_col = len(PDF_COLUMNS) - 1  # "创建时间"列索引
        header.resizeSection(create_time_col, 140)

        file_layout.addWidget(self.file_panel)
        layout.addWidget(file_card)

        # 输出设置
        output_card = Card(title="输出设置")
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出文件:"))
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
        browse_btn = AnimatedButton("浏览")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_btn)
        output_card.content_layout.addLayout(output_layout)
        layout.addWidget(output_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text="开始合并",
            use_gradient=True,
            gradient_colors=("#10b981", "#059669"),
            gradient_hover_colors=("#34d399", "#10b981"),
            progress_chunk_color='#10b981',
            status_text=""
        )
        self.action_panel.clicked.connect(self.start_merge)
        layout.addWidget(self.action_panel)

        layout.addStretch()

        # 应用初始主题
        if Theme is not None:
            self.apply_theme(Theme.DARK)

    def browse_output(self):
        """选择输出文件路径"""
        # 默认使用第一个输入文件的目录
        files = self.file_panel.get_files()
        default_name = "merged.pdf"
        if files:
            default_dir = os.path.dirname(files[0])
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

    def start_merge(self):
        """开始合并PDF"""
        files = self.file_panel.get_files()
        if len(files) < 2:
            show_warning(self, "警告", "请至少添加 2 个PDF文件！")
            return

        output = self.output_path.text()
        if not output:
            self.browse_output()
            output = self.output_path.text()
            if not output:
                return

        if not FITZ_AVAILABLE:
            show_error(self, "错误", "请先安装 PyMuPDF: pip install PyMuPDF")
            return

        # 开始任务
        self.action_panel.start_task(len(files), status="正在合并...")

        # 创建工作线程
        self.worker = PDFMergeWorker(files, output)
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.finished.connect(self.merge_finished)
        self.worker.start()

    def merge_finished(self, success, message):
        """合并完成回调"""
        self.action_panel.finish_task(message)

        if success:
            show_info(self, "完成", message)
        else:
            show_error(self, "错误", message)

    def apply_theme(self, theme):
        """应用主题到所有组件"""
        if hasattr(self, 'file_panel'):
            self.file_panel.update_theme(theme)
        if hasattr(self, 'output_path'):
            self.output_path.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {theme['bg']};
                    border: 1px solid {theme['surface']};
                    border-radius: 6px;
                    padding: 6px;
                    color: {theme['text']};
                }}
            """)
        if hasattr(self, 'action_panel'):
            self.action_panel.update_theme(theme)


class PDFMerger(ToolPlugin):
    """PDF合并插件"""
    icon = "📑"
    name = "PDF合并"
    order = 100

    def update_theme(self, theme):
        """更新主题"""
        if hasattr(self, 'widget') and hasattr(self.widget, 'apply_theme'):
            self.widget.apply_theme(theme)

    def create_ui(self):
        """创建UI"""
        self.widget = PDFMergerWidget()
        return self.widget
