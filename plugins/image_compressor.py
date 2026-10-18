# -*- encoding: utf-8 -*-
"""
图片压缩插件
批量压缩图片，支持JPG/PNG/WebP格式
"""
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QSlider, QLineEdit, QGridLayout
)

from common.i18n import t, bind_combo
from common.dialog_utils import get_existing_directory
from common.action_panel import ActionPanel
from common.utils import PIL_AVAILABLE, load_oriented_image
from common.base_worker import BaseWorker
from PyQt6.QtCore import Qt

if PIL_AVAILABLE:
    from PIL import Image

# 导入主程序中的基类和组件
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, Theme
from config import SPACING_SMALL

from common.file_list_panel import FileListPanel
from common.utils import IMAGE_COLUMNS, get_combo_style, get_lineedit_style


class CompressionWorker(BaseWorker):
    """图片压缩工作线程"""
    # 继承 BaseWorker 的标准信号：progress, status, result

    def __init__(self, files, output_dir, format_code, quality):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.format_code = format_code
        self.quality = quality

    def run(self):
        try:
            # ========= 预检查：输出目录是否可写 =========
            from common.utils import check_dir_writable
            output_dir = self.output_dir or os.path.dirname(self.files[0]) if self.files else '.'
            writable, err_msg = check_dir_writable(output_dir)
            if not writable:
                self.result.emit(False, err_msg)
                return

            processed = 0
            failed = 0
            failed_files = []
            for i, file_path in enumerate(self.files):
                try:
                    self._compress_one(file_path)
                    processed += 1
                except Exception as e:
                    # per-file 捕获：单个坏文件不再中止整批（H8）
                    print(f"compress error {file_path}: {e}")
                    failed += 1
                    failed_files.append(f"{file_path}: {str(e)}")
                self.progress.emit(i + 1)

            self._emit_result(processed, failed, failed_files)
        except Exception as e:
            print(f"Error in image_compressor: {e}")
            self.result.emit(False, t(
                "plugin.image_compressor.error.compress_failed", error=str(e)))

    def _compress_one(self, file_path):
        """压缩单张图片；异常向上抛出，由 run() 汇总为失败列表"""
        self.status.emit(t(
            "plugin.image_compressor.msg.processing",
            name=os.path.basename(file_path)))

        # 将 EXIF 方向落实到像素，避免保存后丢失方向信息
        img = load_oriented_image(file_path)
        # 保存前捕获 EXIF：像素运算（convert / 白底合成）会清空 info（H9）
        exif = img.info.get('exif')
        try:
            # 确定输出格式及扩展名
            # Pillow 格式映射（JPG/JPEG 底层都是 JPEG）
            format_map = {'JPG': 'JPEG', 'JPEG': 'JPEG', 'PNG': 'PNG', 'WebP': 'WEBP'}
            # 输出扩展名：JPG→jpg，JPEG→jpeg，其余用对应小写
            out_ext_map = {'JPG': 'jpg', 'JPEG': 'jpeg', 'PNG': 'png',
                           'WebP': 'webp'}

            if self.format_code == "keep":
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
                    # load_oriented_image 返回新对象，format 恒为 None；
                    # 按源扩展名推断，未知扩展名回退 JPEG
                    src_ext = orig_ext.lower()
                    if src_ext in ('bmp', 'tif', 'tiff', 'gif'):
                        fmt = 'BMP' if src_ext == 'bmp' else src_ext.upper()
                    else:
                        fmt = 'JPEG'
                    output_ext = fmt.lower()
            else:
                fmt = format_map[self.format_code]
                output_ext = out_ext_map[self.format_code]

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
                    img.close()  # 关闭之前的图像
                    img = background
                elif img.mode == 'P':
                    rgba = img.convert('RGBA')
                    img.close()
                    background = Image.new('RGB', rgba.size, (255, 255, 255))
                    background.paste(rgba, mask=rgba.split()[-1])
                    rgba.close()
                    img = background
                elif img.mode != 'RGB':
                    new_img = img.convert('RGB')
                    img.close()
                    img = new_img

            # 保存
            save_kwargs = {}
            if fmt in ('JPEG', 'WEBP'):
                save_kwargs['quality'] = self.quality
                save_kwargs['optimize'] = True
            elif fmt == 'PNG':
                # PNG 为无损格式，quality 滑杆对其无意义；固定较高压缩级别，
                # 避免旧映射在 quality=100 时取到 compress_level=0 反而变大（H10）
                save_kwargs['compress_level'] = 9
                save_kwargs['optimize'] = True

            img.save(output_path, fmt, exif=exif, **save_kwargs)
        finally:
            img.close()  # 释放内存

    def _emit_result(self, success_count, failed, failed_files):
        """汇总成功/失败结果；失败文件明细附在消息中（H8）"""
        if failed == 0:
            self.result.emit(True, t(
                "plugin.image_compressor.msg.compress_done", count=success_count))
            return
        msg = t("plugin.image_compressor.msg.compress_summary",
                success=success_count, failed=failed)
        msg += t("plugin.file_deduplicator.msg.failures_header")
        msg += "\n".join(failed_files[:5])
        if len(failed_files) > 5:
            msg += t("plugin.file_deduplicator.msg.more_failures",
                     count=len(failed_files) - 5)
        self.result.emit(False, msg)


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
                self.format_combo.setStyleSheet(get_combo_style(theme))
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
            if hasattr(self, 'quality_label'):
                self.quality_label.setStyleSheet(f"color: {theme['text']};")
        except RuntimeError:
            pass  # C++ object already deleted

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        self.theme = Theme.DARK

        # 标题 + 描述
        self._setup_header(
            layout,
            title=f"{self.icon} {t('plugin.image_compressor.name')}",
            desc=t("plugin.image_compressor.description"),
            theme=self.theme,
        )

        # 文件选择区域
        self.file_card = Card(title=t("plugin.image_compressor.card.select_images"))
        self.file_panel = FileListPanel(
            columns=IMAGE_COLUMNS,
            file_filter=t("plugin.image_compressor.filter.images"),
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear"]
        )
        self.file_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(self.file_card)

        # 设置区域
        self.settings_card = Card(title=t("plugin.image_compressor.card.settings"))
        settings_layout = QGridLayout()
        settings_layout.setSpacing(SPACING_SMALL)
        self.settings_card.content_layout.addLayout(settings_layout)

        self.format_label = SelectableLabel(t("plugin.image_compressor.label.format"))
        settings_layout.addWidget(self.format_label, 0, 0)
        self.format_combo = QComboBox()
        bind_combo(self.format_combo, [
            ("plugin.image_compressor.combo.keep", "keep"),
            ("JPG", "JPG"),
            ("JPEG", "JPEG"),
            ("PNG", "PNG"),
            ("WebP", "WebP"),
        ])
        self.format_combo.setStyleSheet(get_combo_style(self.theme))
        settings_layout.addWidget(self.format_combo, 0, 1)

        self.quality_caption_label = SelectableLabel(t("plugin.image_compressor.label.quality"))
        settings_layout.addWidget(self.quality_caption_label, 1, 0)
        quality_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(75)
        self.quality_label = SelectableLabel("75%")
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"{v}%")
        )
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        settings_layout.addLayout(quality_layout, 1, 1)

        self.output_dir_label = SelectableLabel(t("plugin.image_compressor.label.output_dir"))
        settings_layout.addWidget(self.output_dir_label, 2, 0)
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText(t("plugin.image_compressor.placeholder.output_dir"))
        self.output_path.setStyleSheet(get_lineedit_style(self.theme))
        self.browse_btn = AnimatedButton(t("plugin.image_compressor.button.browse"))
        self.browse_btn.clicked.connect(self.browse_output)
        self.browse_btn.setMaximumWidth(80)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(output_layout, 2, 1)

        layout.addWidget(self.settings_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text=t("plugin.image_compressor.button.start")
        )
        self.action_panel.clicked.connect(self.start_compression)
        layout.addWidget(self.action_panel)

        # 应用初始主题
        self.update_theme(Theme.DARK)
        return widget

    def retranslate_ui(self):
        """语言切换后重放全部用户可见文本"""
        self.title_label.setText(f"{self.icon} {t('plugin.image_compressor.name')}")
        self.desc_label.setText(t("plugin.image_compressor.description"))
        self.file_card.title_label.setText(t("plugin.image_compressor.card.select_images"))
        # 文件选择过滤器在下次打开对话框时生效（扩展名解析结果不变）
        self.file_panel.file_filter = t("plugin.image_compressor.filter.images")
        self.file_panel.retranslate_ui()
        self.settings_card.title_label.setText(t("plugin.image_compressor.card.settings"))
        self.format_label.setText(t("plugin.image_compressor.label.format"))
        self.quality_caption_label.setText(t("plugin.image_compressor.label.quality"))
        self.output_dir_label.setText(t("plugin.image_compressor.label.output_dir"))
        self.output_path.setPlaceholderText(
            t("plugin.image_compressor.placeholder.output_dir"))
        self.browse_btn.setText(t("plugin.image_compressor.button.browse"))
        self.action_panel.btn.setText(t("plugin.image_compressor.button.start"))
        # 格式下拉框由 bind_combo 自动重放；质量百分比（"75%"）与语言无关

    def browse_output(self):
        parent = self.widget if self.widget else None
        path = get_existing_directory(
            parent, t("plugin.image_compressor.dialog.select_output_dir"))
        if path:
            self.output_path.setText(path)

    def start_compression(self):
        files = self.file_panel.get_files()
        if not files:
            self._show_empty_warning(t("plugin.image_compressor.warning.no_images"))
            return

        if not PIL_AVAILABLE:
            from common.message_utils import show_error
            parent = self.widget if self.widget else None
            show_error(
                parent,
                t("plugin.image_compressor.dialog.error_title"),
                t("plugin.image_compressor.error.need_pillow"))
            return

        self.action_panel.start_task(len(files), status="")

        self.worker = CompressionWorker(
            files,
            self.output_path.text() or None,
            self.format_combo.currentData(),
            self.quality_slider.value()
        )
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.result.connect(self.compression_finished)
        self.worker.start()

    def compression_finished(self, success, message):
        self._finish_with_message(self.action_panel, success, message)
