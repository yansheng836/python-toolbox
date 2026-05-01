"""
图片格式转换插件
批量转换图片格式，支持 JPEG/PNG/WebP/BMP/TIFF/GIF
"""
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QComboBox, QLineEdit, QGridLayout
)

from common.message_utils import show_info, show_error, show_warning
from PyQt6.QtCore import Qt, QThread, pyqtSignal

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 导入主程序中的基类和组件
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin, Card, AnimatedButton, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, Theme
    from config import SPACING_SMALL, SPACING_MEDIUM
except ImportError:
    ToolPlugin = object
    Card = None
    AnimatedButton = None
    Theme = None
    SPACING_SMALL = 8
    SPACING_MEDIUM = 20

from common.file_list_panel import FileListPanel
from common.utils import IMAGE_COLUMNS


class FormatConvertWorker(QThread):
    """图片格式转换工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    FORMAT_MAP = {
        "JPEG": ("JPEG", "jpg"),
        "PNG": ("PNG", "png"),
        "WebP": ("WEBP", "webp"),
        "BMP": ("BMP", "bmp"),
        "TIFF": ("TIFF", "tiff"),
        "GIF": ("GIF", "gif"),
    }

    def __init__(self, files, output_dir, target_fmt):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.target_fmt = target_fmt

    def run(self):
        try:
            processed = 0
            pil_fmt, ext = self.FORMAT_MAP[self.target_fmt]
            for i, file_path in enumerate(self.files):
                self.status.emit(f"正在转换: {os.path.basename(file_path)}")
                img = Image.open(file_path)
                img.load()  # 强制加载，提前发现损坏文件
                img = self._prepare_image(img, pil_fmt)
                base = os.path.splitext(os.path.basename(file_path))[0]
                out_dir = self.output_dir or os.path.dirname(file_path)
                out_path = os.path.join(out_dir, f"{base}.{ext}")
                # 为各格式添加压缩参数，避免文件变大
                save_kwargs = {}
                if pil_fmt == "JPEG":
                    save_kwargs['quality'] = 85
                    save_kwargs['optimize'] = True
                    # 去除 ICC 配置，避免某些图片报 "broken data stream" 错误
                    if 'icc_profile' in img.info:
                        del img.info['icc_profile']
                elif pil_fmt == "PNG":
                    save_kwargs['compress_level'] = 6
                    save_kwargs['optimize'] = True
                elif pil_fmt == "BMP":
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                elif pil_fmt == "TIFF":
                    save_kwargs['compression'] = "tiff_deflate"
                elif pil_fmt == "GIF":
                    save_kwargs['optimize'] = True
                img.save(out_path, pil_fmt, **save_kwargs)
                processed += 1
                self.progress.emit(i + 1)
            self.finished.emit(True, f"成功转换 {processed} 张图片！")
        except Exception as e:
            self.finished.emit(False, f"转换失败: {str(e)}")

    def _prepare_image(self, img, pil_fmt):
        """处理模式兼容性，JPEG/BMP 不支持透明通道"""
        if pil_fmt in ("JPEG", "BMP"):
            # P 模式先转 RGBA 以保留可能的透明信息，再统一去透明
            if img.mode == "P":
                img = img.convert("RGBA")
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
            return img
        if pil_fmt == "GIF":
            # GIF 仅支持 P/L/RGB 模式
            if img.mode not in ("P", "L", "RGB"):
                img = img.convert("P")
            return img
        # PNG/WebP/TIFF 支持透明，直接保留
        return img


class FormatConverter(ToolPlugin):
    """图片格式批量转换工具"""
    name = "图片格式转换"
    description = "批量转换图片格式，支持 JPEG/PNG/WebP/BMP/TIFF/GIF"
    icon = "🔄"
    order = 10

    FORMATS = ["JPEG", "PNG", "WebP", "BMP", "TIFF", "GIF"]

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
            if hasattr(self, 'fmt_combo'):
                self.fmt_combo.setStyleSheet(f"""
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
        except RuntimeError:
            pass  # C++ object already deleted

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        self.title_label = QLabel("🔄 图片格式批量转换")
        self.title_label.setStyleSheet(
            f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']};"
        )
        layout.addWidget(self.title_label)

        self.desc_label = QLabel("纯格式转换，保持原始质量，支持 JPEG / PNG / WebP / BMP / TIFF / GIF")
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # 文件选择区域
        file_card = Card(title="选择图片")
        self.file_panel = FileListPanel(
            columns=IMAGE_COLUMNS,
            file_filter="图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif *.gif)",
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear"]
        )
        file_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(file_card)

        # 转换设置
        settings_card = Card(title="转换设置")
        settings_layout = QGridLayout()
        settings_layout.setSpacing(SPACING_SMALL)
        settings_card.content_layout.addLayout(settings_layout)

        settings_layout.addWidget(QLabel("目标格式:"), 0, 0)
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(self.FORMATS)
        self.fmt_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        settings_layout.addWidget(self.fmt_combo, 0, 1)

        settings_layout.addWidget(QLabel("输出目录:"), 1, 0)
        out_row = QHBoxLayout()
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
        browse_btn = AnimatedButton("浏览")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_output)
        out_row.addWidget(self.output_path)
        out_row.addWidget(browse_btn)
        settings_layout.addLayout(out_row, 1, 1)
        layout.addWidget(settings_card)

        # 进度和操作
        action_card = Card()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        action_card.content_layout.addWidget(self.progress_bar)

        self.start_btn = AnimatedButton("开始转换")
        self.start_btn.setMinimumHeight(40)
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
        self.start_btn.clicked.connect(self.start_convert)
        action_card.content_layout.addWidget(self.start_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #94a3b8;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_card.content_layout.addWidget(self.status_label)
        layout.addWidget(action_card)
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

    def start_convert(self):
        files = self.file_panel.get_files()
        if not files:
            parent = self.widget if self.widget else None
            show_warning(parent, "警告", "请先添加图片！")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(files))
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)

        self.worker = FormatConvertWorker(
            files,
            self.output_path.text() or None,
            self.fmt_combo.currentText()
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.convert_finished)
        self.worker.start()

    def convert_finished(self, success, message):
        self.start_btn.setEnabled(True)
        self.status_label.setText("")
        self.progress_bar.setVisible(False)
        if success:
            show_info(None, "完成", message)
        else:
            show_error(None, "错误", message)
