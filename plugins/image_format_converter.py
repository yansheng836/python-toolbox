# -*- encoding: utf-8 -*-
"""
图片格式转换插件
批量转换图片格式，支持 JPEG/PNG/WebP/BMP/TIFF/GIF
"""
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QLineEdit, QGridLayout
)

from common.dialog_utils import get_existing_directory
from common.action_panel import ActionPanel
from common.utils import PIL_AVAILABLE
from common.base_worker import BaseWorker

if PIL_AVAILABLE:
    from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, Theme
from config import SPACING_SMALL

from common.file_list_panel import FileListPanel
from common.utils import IMAGE_COLUMNS, get_combo_style, get_lineedit_style

class FormatConvertWorker(BaseWorker):
    """图片格式转换工作线程"""
    # 继承 BaseWorker 的标准信号：progress, status, finished

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
            # ========= 预检查：输出目录是否可写 =========
            from common.utils import check_dir_writable
            out_dir = self.output_dir or (
                os.path.dirname(self.files[0]) if self.files else '.'
            )
            writable, err_msg = check_dir_writable(out_dir)
            if not writable:
                self.finished.emit(False, err_msg)
                return

            processed = 0
            pil_fmt, ext = self.FORMAT_MAP[self.target_fmt]
            for i, file_path in enumerate(self.files):
                self.status.emit(f"正在转换: {os.path.basename(file_path)}")
                # 使用上下文管理器确保文件句柄释放，复制后操作避免源文件锁定
                with Image.open(file_path) as src_img:
                    src_img.load()  # 强制加载，提前发现损坏文件
                    img = self._prepare_image(src_img, pil_fmt)
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
                        new_img = img.convert("RGB")
                        img.close()
                        img = new_img
                elif pil_fmt == "TIFF":
                    save_kwargs['compression'] = "tiff_deflate"
                elif pil_fmt == "GIF":
                    save_kwargs['optimize'] = True
                img.save(out_path, pil_fmt, **save_kwargs)
                img.close()  # 释放内存
                processed += 1
                self.progress.emit(i + 1)
            self.finished.emit(True, f"成功转换 {processed} 张图片！")
        except Exception as e:
            print(f"Error in image_format_converter: {e}")
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
                self.fmt_combo.setStyleSheet(get_combo_style(theme))
            if hasattr(self, 'output_path'):
                self.output_path.setStyleSheet(get_lineedit_style(theme))
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
        self.theme = Theme.DARK

        # 标题 + 描述
        self._setup_header(layout, theme=self.theme)

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

        settings_layout.addWidget(SelectableLabel("目标格式:"), 0, 0)
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(self.FORMATS)
        self.fmt_combo.setStyleSheet(get_combo_style(self.theme))
        settings_layout.addWidget(self.fmt_combo, 0, 1)

        settings_layout.addWidget(SelectableLabel("输出目录:"), 1, 0)
        out_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("默认保存到原图目录")
        self.output_path.setStyleSheet(get_lineedit_style(self.theme))
        browse_btn = AnimatedButton("浏览")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_output)
        out_row.addWidget(self.output_path)
        out_row.addWidget(browse_btn)
        settings_layout.addLayout(out_row, 1, 1)
        layout.addWidget(settings_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text="开始转换"
        )
        self.action_panel.clicked.connect(self.start_convert)
        layout.addWidget(self.action_panel)

        # 应用初始主题
        if Theme is not None:
            self.update_theme(Theme.DARK)
        return widget

    def browse_output(self):
        parent = self.widget if self.widget else None
        path = get_existing_directory(parent, "选择输出目录")
        if path:
            self.output_path.setText(path)

    def start_convert(self):
        files = self.file_panel.get_files()
        if not files:
            self._show_empty_warning("请先添加图片！")
            return

        self.action_panel.start_task(len(files), status="")

        self.worker = FormatConvertWorker(
            files,
            self.output_path.text() or None,
            self.fmt_combo.currentText()
        )
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.finished.connect(self.convert_finished)
        self.worker.start()

    def convert_finished(self, success, message):
        self._finish_with_message(self.action_panel, success, message)
