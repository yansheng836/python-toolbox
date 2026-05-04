# -*- encoding: utf-8 -*-
"""
图片压缩插件
批量压缩图片，支持JPG/PNG/WebP格式
"""
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QComboBox, QSlider, QLineEdit, QGridLayout,
    QFileDialog
)

from common.message_utils import show_info, show_error, show_warning
from common.dialog_utils import get_existing_directory
from common.action_panel import ActionPanel
from common.utils import PIL_AVAILABLE
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

# 导入主程序中的基类和组件
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, Theme
from config import SPACING_SMALL, SPACING_MEDIUM

from common.file_list_panel import FileListPanel
from common.utils import IMAGE_COLUMNS


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

                # 确定输出格式及扩展名
                # Pillow 格式映射（JPG/JPEG 底层都是 JPEG）
                format_map = {'JPG': 'JPEG', 'JPEG': 'JPEG', 'PNG': 'PNG', 'WebP': 'WEBP'}
                # 原扩展名 → Pillow 格式
                ext_map = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG',
                            '.webp': 'WEBP', '.bmp': 'BMP'}
                # 输出扩展名：JPG→jpg，JPEG→jpeg，其余用对应小写
                out_ext_map = {'JPG': 'jpg', 'JPEG': 'jpeg', 'PNG': 'png',
                               'WebP': 'webp'}

                if self.format_str == "保持原格式":
                    # 保留原扩展名（区分 jpg/jpeg）
                    orig_ext = os.path.splitext(file_path)[1].lstrip('.')
                    if orig_ext.lower() in ('jpg', 'jpeg'):
                        fmt = 'JPEG'
                        output_ext = orig_ext  # 保留原始大小写风格
                    elif orig_ext.lower() == 'png':
                        fmt = 'PNG'
                        output_ext = orig_ext
                    elif orig_ext.lower() == 'webp':
                        fmt = 'WEBP'
                        output_ext = orig_ext
                    else:
                        fmt = img.format if img.format else 'JPEG'
                        output_ext = fmt.lower()
                else:
                    fmt = format_map[self.format_str]
                    output_ext = out_ext_map[self.format_str]

                # 确定输出路径
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                if self.output_dir:
                    output_path = os.path.join(self.output_dir, f"{base_name}_compressed.{output_ext}")
                else:
                    dir_name = os.path.dirname(file_path)
                    output_path = os.path.join(dir_name, f"{base_name}_compressed.{output_ext}")

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
                    # quality 1-100 映射到 compress_level 9-0（值越小压缩越弱）
                    save_kwargs['compress_level'] = max(0, min(9, int(10 - self.quality / 10)))
                    save_kwargs['optimize'] = True

                img.save(output_path, fmt, **save_kwargs)
                processed += 1
                self.progress.emit(i + 1)

            self.finished.emit(True, f"成功压缩 {processed} 张图片！")
        except Exception as e:
            print(f"Error in image_compressor: {e}")
            self.finished.emit(False, f"压缩失败: {str(e)}")


class ImageCompressor(ToolPlugin):
    """图片压缩工具"""

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
        layout.setSpacing(10)
        self.theme = Theme.DARK

        # 标题（使用 PLUGIN_MODULES 配置中的 icon + name）
        self.title_label = QLabel(f"{self.icon} {self.name}")
        self.title_label.setStyleSheet(
            f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']};"
        )
        layout.addWidget(self.title_label)

        # 说明（使用 PLUGIN_MODULES 配置中的 description）
        self.desc_label = QLabel(self.description)
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # 文件选择区域
        file_card = Card(title="选择图片")
        self.file_panel = FileListPanel(
            columns=IMAGE_COLUMNS,
            file_filter="图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.gif)",
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear"]
        )
        file_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(file_card)

        # 设置区域
        settings_card = Card(title="压缩设置")
        settings_layout = QGridLayout()
        settings_layout.setSpacing(SPACING_SMALL)
        settings_card.content_layout.addLayout(settings_layout)

        settings_layout.addWidget(QLabel("输出格式:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["保持原格式", "JPG", "JPEG", "PNG", "WebP"])
        self.format_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme['bg']};
                border: 1px solid {self.theme['surface']};
                border-radius: 6px;
                padding: 4px;
                color: {self.theme['text']};
            }}
        """)
        settings_layout.addWidget(self.format_combo, 0, 1)

        settings_layout.addWidget(QLabel("压缩质量:"), 1, 0)
        quality_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(75)
        self.quality_label = QLabel("75%")
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"{v}%")
        )
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        settings_layout.addLayout(quality_layout, 1, 1)

        settings_layout.addWidget(QLabel("输出目录:"), 2, 0)
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("默认保存到原图目录（图片压缩后带 _compressed 后缀）")
        self.output_path.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme['bg']};
                border: 1px solid {self.theme['surface']};
                border-radius: 6px;
                padding: 4px;
                color: {self.theme['text']};
            }}
        """)
        self.browse_btn = AnimatedButton("浏览")
        self.browse_btn.clicked.connect(self.browse_output)
        self.browse_btn.setMaximumWidth(80)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(output_layout, 2, 1)

        layout.addWidget(settings_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text="开始压缩"
        )
        self.action_panel.clicked.connect(self.start_compression)
        layout.addWidget(self.action_panel)

        layout.addStretch()

        # 应用初始主题
        if Theme is not None:
            self.update_theme(Theme.DARK)
        return widget

    def browse_output(self):
        parent = self.widget if self.widget else None
        path = get_existing_directory(parent, "选择输出目录")
        if path:
            self.output_path.setText(path)

    def start_compression(self):
        files = self.file_panel.get_files()
        if not files:
            parent = self.widget if self.widget else None
            show_warning(parent, "警告", "请先添加图片！")
            return

        if not PIL_AVAILABLE:
            parent = self.widget if self.widget else None
            show_error(parent, "错误", "请先安装 Pillow: pip install Pillow")
            return

        self.action_panel.start_task(len(files), status="")

        self.worker = CompressionWorker(
            files,
            self.output_path.text() or None,
            self.format_combo.currentText(),
            self.quality_slider.value()
        )
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.finished.connect(self.compression_finished)
        self.worker.start()

    def compression_finished(self, success, message):
        self.action_panel.finish_task(message)
        parent = self.widget if self.widget else None
        if success:
            show_info(parent, "完成", message)
        else:
            show_error(parent, "错误", message)
