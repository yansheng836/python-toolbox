"""
PDF拆分工具插件
将PDF文件拆分为多张图片或单页PDF，支持设置拆分页数
"""
import os
import sys
import io

# 导入PyMuPDF用于PDF拆分
try:
    import fitz

    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

# 导入PIL用于图片处理
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 导入主程序中的ToolPlugin基类和相关组件
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin, Card, AnimatedButton, TITLE_STYLES, FONT_SIZE_12, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, FONT_WEIGHT_700, Theme
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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QLineEdit,
    QComboBox, QSpinBox, QSlider,
    QRadioButton, QButtonGroup, QFormLayout
)

from common.message_utils import show_info, show_error, show_warning
from common.file_list_panel import FileListPanel
from common.action_panel import ActionPanel
from common.utils import get_file_size, get_create_time, get_pdf_pages
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class PDFSplitWorker(QThread):
    """PDF拆分工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, input_file, output_dir,
                 output_format="pdf", pages_per_split=1,
                 image_format="PNG", image_quality=95):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.output_format = output_format
        self.pages_per_split = pages_per_split
        self.image_format = image_format
        self.image_quality = image_quality

    def run(self):
        try:
            if not FITZ_AVAILABLE:
                self.finished.emit(False, "错误: 未安装PyMuPDF库，请运行: pip install PyMuPDF")
                return

            self.status.emit("正在打开PDF文件...")

            doc = fitz.open(self.input_file)

            total_pages = len(doc)
            self.status.emit(f"PDF共 {total_pages} 页，开始拆分...")

            os.makedirs(self.output_dir, exist_ok=True)

            base_name = os.path.splitext(os.path.basename(self.input_file))[0]
            output_count = 0

            if self.output_format == "pdf":
                for i in range(0, total_pages, self.pages_per_split):
                    end_page = min(i + self.pages_per_split, total_pages)

                    new_doc = fitz.open()
                    new_doc.insert_pdf(doc, from_page=i, to_page=end_page - 1)

                    output_file = os.path.join(
                        self.output_dir,
                        f"{base_name}_part{output_count + 1}_pages_{i + 1}-{end_page}.pdf"
                    )
                    new_doc.save(output_file, garbage=0, deflate=False)
                    new_doc.close()

                    output_count += 1
                    self.progress.emit(output_count)

                doc.close()
                self.finished.emit(True, f"成功拆分PDF为 {output_count} 个文件！\n保存位置: {self.output_dir}")

            else:
                fmt = self.image_format.upper()

                # PNG and WebP need PIL for compression control
                if fmt in ("PNG", "WEBP") and not PIL_AVAILABLE:
                    doc.close()
                    self.finished.emit(False, f"错误: 输出{fmt}需要Pillow库，请运行: pip install Pillow")
                    return

                # Zoom proportional to quality: 1.0x at quality=50, 2.0x at quality=100
                zoom = max(1.0, self.image_quality / 50.0)
                mat = fitz.Matrix(zoom, zoom)

                # Map image_quality to PNG compress_level: quality 100->level 9, quality 1->level 1
                # Avoid level 0 (no compression, huge files)
                png_compress_level = max(1, min(9, int(self.image_quality / 100.0 * 9)))

                for page_num in range(total_pages):
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=mat)

                    output_file = os.path.join(
                        self.output_dir,
                        f"{base_name}_page_{page_num + 1}.{self.image_format.lower()}"
                    )

                    if fmt == "PNG":
                        # Use PIL to control compress_level for smaller files
                        img = Image.open(io.BytesIO(pix.tobytes("ppm")))
                        img.save(output_file, "PNG", compress_level=png_compress_level, optimize=True)
                    elif fmt in ("JPEG", "JPG"):
                        pix.save(output_file, output="JPEG", jpg_quality=self.image_quality)
                    elif fmt == "WEBP":
                        img = Image.open(io.BytesIO(pix.tobytes("ppm")))
                        if img.mode not in ("RGB", "L"):
                            img = img.convert("RGB")
                        img.save(output_file, "WEBP", quality=self.image_quality, method=4, optimize=True)

                    output_count += 1
                    self.progress.emit(output_count)

                doc.close()
                self.finished.emit(True, f"成功转换 {output_count} 页为图片！\n保存位置: {self.output_dir}")

        except Exception as e:
            import traceback
            self.finished.emit(False, f"拆分失败: {str(e)}\n{traceback.format_exc()}")


class PDFSplitterWidget(QWidget):
    """PDF拆分工具主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_file = ""
        self.worker = None
        self.setup_ui()

        if not FITZ_AVAILABLE:
            self.status_label.setText("错误: 未安装PyMuPDF库，请运行: pip install PyMuPDF")
            self.split_btn.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        self.title_label = QLabel("📐 PDF拆分工具")
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        layout.addWidget(self.title_label)

        self.desc_label = QLabel("将PDF拆分为图片或单页PDF，支持设置拆分页数")
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # PDF文件列表区域（列表模式，参考PDF合并）
        file_card = Card(title="PDF文件列表（仅支持一个文件）")
        file_layout = file_card.content_layout

        PDF_COLUMNS = [
            ("文件名", lambda f: os.path.basename(f)),
            ("大小", get_file_size),
            ("页数", get_pdf_pages),
            ("创建时间", get_create_time)
        ]

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
        from PyQt6.QtWidgets import QWidget
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
            button_text="开始拆分",
            use_gradient=True,
            status_text=""
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
    icon = "📐"
    name = "PDF拆分"
    order = 105

    def update_theme(self, theme):
        """更新主题"""
        if hasattr(self, 'widget') and hasattr(self.widget, 'apply_theme'):
            self.widget.apply_theme(theme)

    def create_ui(self):
        """创建UI"""
        self.widget = PDFSplitterWidget()
        return self.widget
