"""
图片压缩插件
批量压缩图片，支持JPG/PNG/WebP格式
"""
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QProgressBar, QComboBox, QSlider, QLineEdit, QGridLayout,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 导入主程序中的基类和组件
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin, Card, AnimatedButton, DragDropHandler, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, Theme
except ImportError:
    ToolPlugin = object
    Card = None
    AnimatedButton = None
    DragDropHandler = None
    Theme = None

from common.file_list_panel import FileListPanel


def _get_image_size(file_path):
    """获取图片尺寸文本"""
    if not PIL_AVAILABLE:
        return "N/A"
    try:
        with Image.open(file_path) as img:
            return f"{img.width} x {img.height}"
    except Exception:
        return "读取失败"


def _get_file_size(file_path):
    """获取文件大小文本"""
    try:
        size = os.path.getsize(file_path)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    except Exception:
        return "未知"


IMAGE_COLUMNS = [
    ("文件名", lambda f: os.path.basename(f)),
    ("尺寸", _get_image_size),
    ("大小", _get_file_size)
]


class CompressionWorker(QThread):
    """图片压缩工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output_dir, format_str, quality):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.format_str = format_str
        self.quality = quality

    def run(self):
        try:
            processed = 0
            for i, file_path in enumerate(self.files):
                self.status.emit(f"正在处理: {os.path.basename(file_path)}")

                img = Image.open(file_path)

                # 确定输出格式
                if self.format_str == "保持原格式":
                    fmt = img.format or 'JPEG'
                else:
                    fmt = {'JPG': 'JPEG', 'PNG': 'PNG', 'WebP': 'WEBP'}[self.format_str]

                # 确定输出路径
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                if self.output_dir:
                    output_path = os.path.join(self.output_dir, f"{base_name}_compressed.{fmt.lower()}")
                else:
                    dir_name = os.path.dirname(file_path)
                    output_path = os.path.join(dir_name, f"{base_name}_compressed.{fmt.lower()}")

                # 处理图片
                if fmt == 'JPEG':
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    elif img.mode == 'P':
                        img = img.convert('RGBA')
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')

                # 保存
                save_kwargs = {}
                if fmt in ('JPEG', 'WEBP'):
                    save_kwargs['quality'] = self.quality
                    save_kwargs['optimize'] = True
                elif fmt == 'PNG':
                    save_kwargs['optimize'] = True

                img.save(output_path, fmt, **save_kwargs)
                processed += 1
                self.progress.emit(i + 1)

            self.finished.emit(True, f"成功压缩 {processed} 张图片！")
        except Exception as e:
            self.finished.emit(False, f"压缩失败: {str(e)}")


class ImageCompressor(ToolPlugin):
    """图片压缩工具"""
    name = "图片压缩"
    description = "批量压缩图片，支持JPG/PNG/WebP格式"
    icon = "🖼️"
    order = 1

    def setup_drag_handler(self):
        """设置拖拽处理器"""
        if hasattr(self, 'file_panel') and DragDropHandler:
            DragDropHandler.setup_drag_drop(self.file_panel.table, self.file_panel.get_files())
            self.file_panel.update_list()

    def update_theme(self, theme):
        """更新主题"""
        try:
            if hasattr(self, 'title_label'):
                self.title_label.setStyleSheet(
                    f"font-size: {TITLE_STYLES['font_size']}; "
                    f"font-weight: {TITLE_STYLES['font_weight']}; "
                    f"color: {theme['text']};"
                )
            if hasattr(self, 'desc_label'):
                self.desc_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_14};")
            if hasattr(self, 'file_panel'):
                self.file_panel.update_theme(theme)
            if hasattr(self, 'format_combo'):
                self.format_combo.setStyleSheet(f"""
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
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setStyleSheet(f"""
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
            if hasattr(self, 'start_btn'):
                self.start_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 {theme['success']}, stop:1 {theme.get('success_gradient_end', theme['success'])});
                        color: {theme['text']};
                        border: none;
                        border-radius: 8px;
                        font-size: {FONT_SIZE_16};
                        font-weight: {FONT_WEIGHT_600};
                    }}
                    QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {theme['success_hover']}, stop:1 {theme.get('success_gradient_end', theme['success'])}); }}
                    QPushButton:disabled {{ background: {theme['surface']}; color: {theme['text_secondary']}; }}
                """)
            if hasattr(self, 'status_label'):
                self.status_label.setStyleSheet(f"color: {theme['text_secondary']};")
            if hasattr(self, 'quality_label'):
                self.quality_label.setStyleSheet(f"color: {theme['text']};")
        except RuntimeError:
            pass  # C++ object already deleted

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # 标题
        self.title_label = QLabel("🖼️ 图片压缩工具")
        self.title_label.setStyleSheet(
            f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']};"
        )
        layout.addWidget(self.title_label)

        # 说明
        self.desc_label = QLabel("支持 JPG、PNG、WebP 格式，可批量处理并调整压缩质量")
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # 文件选择区域
        file_card = Card(title="选择图片")
        self.file_panel = FileListPanel(
            columns=IMAGE_COLUMNS,
            file_filter="图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.gif)",
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "up", "down"]
        )
        file_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(file_card)

        # 设置区域
        settings_card = Card(title="压缩设置")
        settings_layout = QGridLayout()
        settings_card.content_layout.addLayout(settings_layout)

        settings_layout.addWidget(QLabel("输出格式:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["保持原格式", "JPG", "PNG", "WebP"])
        self.format_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        settings_layout.addWidget(self.format_combo, 0, 1)

        settings_layout.addWidget(QLabel("压缩质量:"), 1, 0)
        quality_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(85)
        self.quality_label = QLabel("85%")
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"{v}%")
        )
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        settings_layout.addLayout(quality_layout, 1, 1)

        settings_layout.addWidget(QLabel("输出目录:"), 2, 0)
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("默认保存到原图目录")
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
        self.browse_btn.clicked.connect(self.browse_output)
        self.browse_btn.setMaximumWidth(80)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(output_layout, 2, 1)

        layout.addWidget(settings_card)

        # 进度和操作
        progress_card = Card()
        progress_layout = progress_card.content_layout

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0f172a;
                border-radius: 6px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #6366f1;
                border-radius: 6px;
            }
        """)
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.start_btn = AnimatedButton("开始压缩")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #34d399, stop:1 #10b981); }}
            QPushButton:disabled {{ background: #334155; color: #64748b; }}
        """)
        self.start_btn.clicked.connect(self.start_compression)
        progress_layout.addWidget(self.start_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #94a3b8;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.status_label)

        layout.addWidget(progress_card)
        layout.addStretch()

        # 应用初始主题
        if Theme is not None:
            self.update_theme(Theme.DARK)
        return widget

    def browse_output(self):
        parent = self.widget if self.widget else None
        path = QFileDialog.getExistingDirectory(parent, "选择输出目录")
        if path:
            self.output_path.setText(path)

    def start_compression(self):
        files = self.file_panel.get_files()
        if not files:
            parent = self.widget if self.widget else None
            QMessageBox.warning(parent, "警告", "请先添加图片！")
            return

        if not PIL_AVAILABLE:
            parent = self.widget if self.widget else None
            QMessageBox.critical(parent, "错误", "请先安装 Pillow: pip install Pillow")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(files))
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)

        self.worker = CompressionWorker(
            files,
            self.output_path.text() or None,
            self.format_combo.currentText(),
            self.quality_slider.value()
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.compression_finished)
        self.worker.start()

    def compression_finished(self, success, message):
        self.start_btn.setEnabled(True)
        self.status_label.setText("")
        self.progress_bar.setVisible(False)
        if success:
            QMessageBox.information(None, "完成", message)
        else:
            QMessageBox.critical(None, "错误", message)
