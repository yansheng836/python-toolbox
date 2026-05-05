# -*- encoding: utf-8 -*-
"""
PDF拆分工具插件
将PDF文件拆分为多张图片或单页PDF，支持设置拆分页数
"""
import os
import sys

from common.utils import FITZ_AVAILABLE, PIL_AVAILABLE

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, FONT_WEIGHT_700, Theme

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QComboBox, QSpinBox, QSlider, QRadioButton, QButtonGroup, QFormLayout, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from common.message_utils import show_info, show_error, show_warning
from common.file_list_panel import FileListPanel
from common.action_panel import ActionPanel
from common.utils import PDF_COLUMNS

if FITZ_AVAILABLE:
    import fitz


class PDFSplitWorker(QThread):
    """PDF拆分工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, input_file, output_path, output_format, pages_per_split, image_format, quality):
        super().__init__()
        self.input_file = input_file
        self.output_path = output_path
        self.output_format = output_format
        self.pages_per_split = pages_per_split
        self.image_format = image_format
        self.quality = quality

    def run(self):
        try:
            if not FITZ_AVAILABLE:
                self.finished.emit(False, "PyMuPDF 未安装")
                return

            doc = fitz.open(self.input_file)
            total_pages = len(doc)

            if self.output_format == "pdf":
                # 按页数拆分PDF
                base_name = os.path.splitext(os.path.basename(self.input_file))[0]
                count = 0
                for i in range(0, total_pages, self.pages_per_split):
                    self.status.emit(f"正在拆分: 第 {i+1}-{min(i+self.pages_per_split, total_pages)} 页")
                    new_doc = fitz.open()
                    end = min(i + self.pages_per_split, total_pages)
                    new_doc.insert_pdf(doc, from_page=i, to_page=end-1)
                    output_file = os.path.join(self.output_path, f"{base_name}_part{count+1}.pdf")
                    new_doc.save(output_file)
                    new_doc.close()
                    count += 1
                    self.progress.emit(count)
                msg = f"拆分完成，共生成 {count} 个PDF文件"
            else:
                # 每页输出为图片
                base_name = os.path.splitext(os.path.basename(self.input_file))[0]
                count = 0
                for i in range(total_pages):
                    self.status.emit(f"正在转换: 第 {i+1}/{total_pages} 页")
                    page = doc.load_page(i)
                    mat = fitz.Matrix(self.quality / 100, self.quality / 100)
                    pix = page.get_pixmap(matrix=mat)
                    output_file = os.path.join(self.output_path, f"{base_name}_page{i+1}.{self.image_format.lower()}")
                    pix.save(output_file)
                    pix = None
                    count += 1
                    self.progress.emit(count)
                msg = f"转换完成，共生成 {count} 张图片"

            doc.close()
            self.finished.emit(True, msg)
        except Exception as e:
            self.finished.emit(False, f"拆分失败: {str(e)}")

class PDFSplitterWidget(QWidget):
    """PDF拆分工具主界面"""

    def __init__(self, parent=None, icon="", name="", description=""):
        super().__init__(parent)
        self.icon = icon
        self.name = name
        self.description = description
        self.input_file = ""
        self.worker = None
        self.setup_ui()

        if not FITZ_AVAILABLE:
            self.status_label.setText("错误: 未安装PyMuPDF库，请运行: pip install PyMuPDF")
            self.split_btn.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        self.title_label = SelectableLabel(f"{self.icon} {self.name}")
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        layout.addWidget(self.title_label)

        self.desc_label = SelectableLabel(self.description)
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # PDF文件列表区域（列表模式，参考PDF合并）
        file_card = Card(title="PDF文件列表（仅支持一个文件）")
        file_layout = file_card.content_layout

        self.file_panel = FileListPanel(
            columns=PDF_COLUMNS,
            file_filter="PDF文件 (*.pdf);;所有文件 (*.*)",
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear"],
            table_min_height=100
        )
        self.file_panel.files_changed.connect(self.auto_set_output_dir)
        file_layout.addWidget(self.file_panel)
        layout.addWidget(file_card)

        settings_card = Card(title="拆分设置")
        settings_layout = QFormLayout()
        settings_layout.setSpacing(12)

        self.format_group = QButtonGroup(self)
        format_layout = QHBoxLayout()
        self.pdf_radio = QRadioButton("单页PDF")
        self.pdf_radio.setChecked(True)
        self.image_radio = QRadioButton("图片")
        self.format_group.addButton(self.pdf_radio)
        self.format_group.addButton(self.image_radio)
        format_layout.addWidget(self.pdf_radio)
        format_layout.addWidget(self.image_radio)
        format_layout.addStretch()
        self.pdf_radio.toggled.connect(self.on_format_changed)
        settings_layout.addRow("输出格式:", format_layout)

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 1000)
        self.pages_spin.setValue(1)
        self.pages_spin.setSuffix(" 页/文件")
        settings_layout.addRow("拆分页数:", self.pages_spin)

        self.image_format_combo = QComboBox()
        self.image_format_combo.addItems(["JPG", "JPEG", "PNG", "WebP"])
        self.image_format_combo.setVisible(False)
        settings_layout.addRow("图片格式:", self.image_format_combo)

        # 图片质量：滚动条 + 百分比标签（参考图片压缩功能）
        quality_widget = QWidget()
        quality_h_layout = QHBoxLayout(quality_widget)
        quality_h_layout.setContentsMargins(0, 0, 0, 0)
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(85)
        self.quality_label = QLabel("85%")
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"{v}%")
        )
        quality_h_layout.addWidget(self.quality_slider)
        quality_h_layout.addWidget(self.quality_label)
        self.quality_widget = quality_widget
        settings_layout.addRow("图片质量:", self.quality_widget)
        self.quality_widget.setVisible(False)

        settings_card.content_layout.addLayout(settings_layout)
        layout.addWidget(settings_card)

        output_card = Card(title="输出设置")
        output_layout = QHBoxLayout()
        self.output_label = QLabel("输出目录:")
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("默认原文件目录")
        self.browse_btn = AnimatedButton("浏览")
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        output_card.content_layout.addLayout(output_layout)
        layout.addWidget(output_card)

        # 操作面板（按钮 + 进度条 + 状态标签，参考PDF合并）
        # 使用Theme中定义的统一action渐变颜色
        self.action_panel = ActionPanel(
            button_text="开始拆分"
        )
        self.action_panel.clicked.connect(self.start_split)
        layout.addWidget(self.action_panel)

        layout.addStretch()

        # 应用初始主题
        if Theme is not None:
            self.apply_theme(Theme.DARK)

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
        if hasattr(self, 'output_label'):
            self.output_label.setStyleSheet(f"color: {theme['text']};")
        if hasattr(self, 'pdf_radio'):
            self.pdf_radio.setStyleSheet(f"color: {theme['text']};")
            self.image_radio.setStyleSheet(f"color: {theme['text']};")
        if hasattr(self, 'image_format_combo'):
            self.image_format_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {theme['bg']};
                    border: 1px solid {theme['surface']};
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
                    selection-color: {theme['text']};
                    padding: 4px;
                    border: none;
                }}
            """)
        if hasattr(self, 'pages_spin'):
            self.pages_spin.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {theme['bg']};
                    border: 1px solid {theme['surface']};
                    border-radius: 6px;
                    padding: 4px;
                    color: {theme['text']};
                }}
            """)
        if hasattr(self, 'quality_label'):
            self.quality_label.setStyleSheet(f"color: {theme['text']};")
        if hasattr(self, 'action_panel'):
            self.action_panel.update_theme(theme)

    def on_format_changed(self):
        """输出格式改变时更新UI"""
        is_image = self.image_radio.isChecked()
        self.image_format_combo.setVisible(is_image)
        self.quality_widget.setVisible(is_image)
        self.pages_spin.setEnabled(self.pdf_radio.isChecked())
        if not self.pdf_radio.isChecked():
            self.pages_spin.setValue(1)

    def browse_output(self):
        """选择输出目录"""
        default_dir = self.output_path.text() or (
            os.path.dirname(self.file_panel.get_files()[0])
            if self.file_panel.get_files() else ""
        )
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            default_dir
        )
        if dir_path:
            self.output_path.setText(dir_path)

    def auto_set_output_dir(self):
        """自动设置输出目录为PDF原文件目录"""
        if self.output_path.text():
            return
        files = self.file_panel.get_files()
        if files:
            self.output_path.setText(os.path.dirname(files[0]))

    def start_split(self):
        """开始拆分"""
        files = self.file_panel.get_files()
        if not files:
            show_warning(self, "警告", "请先添加PDF文件！")
            return
        if len(files) > 1:
            show_warning(self, "警告", "拆分功能仅支持一个PDF文件！")
            return

        input_file = files[0]

        if not self.output_path.text():
            show_warning(self, "警告", "请选择输出目录！")
            return

        if not FITZ_AVAILABLE:
            show_error(self, "错误", "请先安装 PyMuPDF: pip install PyMuPDF")
            return

        if self.image_radio.isChecked() and not PIL_AVAILABLE:
            show_error(self, "错误", "输出图片需要 Pillow 库: pip install Pillow")
            return

        output_format = "pdf" if self.pdf_radio.isChecked() else "image"
        pages_per_split = self.pages_spin.value() if output_format == "pdf" else 1
        image_format = self.image_format_combo.currentText()
        quality = self.quality_slider.value()

        # 计算总任务数
        try:
            doc = fitz.open(input_file)
            total = len(doc)
            doc.close()
            if output_format == "pdf":
                total = (total + pages_per_split - 1) // pages_per_split
        except Exception:
            total = 100

        # 启动任务
        self.action_panel.start_task(total, status="正在拆分...")

        self.worker = PDFSplitWorker(
            input_file,
            self.output_path.text(),
            output_format,
            pages_per_split,
            image_format,
            quality
        )
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.finished.connect(self.split_finished)
        self.worker.start()

    def split_finished(self, success, message):
        """拆分完成回调"""
        self.action_panel.finish_task(message)

        if success:
            show_info(self, "完成", message)
        else:
            show_error(self, "错误", message)


class PDFSplitter(ToolPlugin):
    """PDF拆分插件"""

    def update_theme(self, theme):
        """更新主题"""
        if hasattr(self, 'widget') and hasattr(self.widget, 'apply_theme'):
            self.widget.apply_theme(theme)

    def create_ui(self):
        """创建UI"""
        self.widget = PDFSplitterWidget(icon=self.icon, name=self.name, description=self.description)
        # 将 Widget 的标签属性复制到插件实例，统一访问入口
        self.title_label = self.widget.title_label
        self.desc_label = self.widget.desc_label
        return self.widget
