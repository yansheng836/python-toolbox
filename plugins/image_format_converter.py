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

from common.i18n import t
from common.dialog_utils import get_existing_directory
from common.action_panel import ActionPanel
from common.utils import PIL_AVAILABLE, load_oriented_image
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
    # 继承 BaseWorker 的标准信号：progress, status, result

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
                self.result.emit(False, err_msg)
                return

            pil_fmt, ext = self.FORMAT_MAP[self.target_fmt]
            # 归一化源文件路径集合，用于输出防覆盖判断（H3）
            self._source_paths = {
                os.path.normcase(os.path.abspath(f)) for f in self.files
            }
            processed = 0
            failed = 0
            failed_files = []
            for i, file_path in enumerate(self.files):
                try:
                    self._convert_one(file_path, pil_fmt, ext)
                    processed += 1
                except Exception as e:
                    # per-file 捕获：单个坏文件不再中止整批（H8）
                    print(f"convert error {file_path}: {e}")
                    failed += 1
                    failed_files.append(f"{file_path}: {str(e)}")
                self.progress.emit(i + 1)

            self._emit_result(processed, failed, failed_files)
        except Exception as e:
            print(f"Error in image_format_converter: {e}")
            self.result.emit(False, t(
                "plugin.image_format_converter.error.convert_failed", error=str(e)))

    def _convert_one(self, file_path, pil_fmt, ext):
        """转换单张图片；异常向上抛出，由 run() 汇总为失败列表"""
        self.status.emit(t(
            "plugin.image_format_converter.msg.converting",
            name=os.path.basename(file_path),
        ))
        # 校正 EXIF 方向后返回独立副本，保存时不受源文件句柄生命周期影响
        src_img = load_oriented_image(file_path)
        # 保存前捕获 EXIF：模式转换（convert / 白底合成）会清空 info（H9）
        exif = src_img.info.get('exif')
        img = self._prepare_image(src_img, pil_fmt)
        try:
            base = os.path.splitext(os.path.basename(file_path))[0]
            out_dir = self.output_dir or os.path.dirname(file_path)
            out_path = os.path.join(out_dir, f"{base}.{ext}")
            # 防覆盖（H3）：目标路径若与任一待处理源文件相同（含自身，如 a.jpg→JPEG、
            # a.png→JPEG 落在既有的 a.jpg 上），追加后缀，避免就地覆盖或覆盖待处理文件
            out_abs = os.path.normcase(os.path.abspath(out_path))
            if out_abs in self._source_paths:
                out_path = os.path.join(out_dir, f"{base}_converted.{ext}")

            # 为各格式添加压缩参数，避免文件变大
            save_kwargs = {}
            if pil_fmt == "JPEG":
                save_kwargs['quality'] = 85
                save_kwargs['optimize'] = True
                # 主动移除 ICC：部分源图的 ICC 会触发 Pillow "broken data stream" 错误。
                # 无损保留需重写 ICC 流，超出本次修复范围，维持既有降级策略（见 H9）
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

            # 仅对支持 EXIF 的格式传入（BMP/GIF 不支持）
            if exif and pil_fmt in ("JPEG", "PNG", "WEBP", "TIFF"):
                save_kwargs['exif'] = exif

            img.save(out_path, pil_fmt, **save_kwargs)
        finally:
            img.close()  # 释放内存

    def _emit_result(self, success_count, failed, failed_files):
        """汇总成功/失败结果；失败文件明细附在消息中（H8）"""
        if failed == 0:
            self.result.emit(True, t(
                "plugin.image_format_converter.msg.success", count=success_count))
            return
        msg = t("plugin.image_format_converter.msg.convert_summary",
                success=success_count, failed=failed)
        msg += t("plugin.file_deduplicator.msg.failures_header")
        msg += "\n".join(failed_files[:5])
        if len(failed_files) > 5:
            msg += t("plugin.file_deduplicator.msg.more_failures",
                     count=len(failed_files) - 5)
        self.result.emit(False, msg)

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

    def retranslate_ui(self):
        """语言切换后重放全部用户可见文本"""
        self.title_label.setText(
            f"{self.icon} {t('plugin.image_format_converter.name')}")
        self.desc_label.setText(
            t("plugin.image_format_converter.description"))
        self.file_card.title_label.setText(
            t("plugin.image_format_converter.card.select_images"))
        self.settings_card.title_label.setText(
            t("plugin.image_format_converter.card.settings"))
        self.target_format_label.setText(
            t("plugin.image_format_converter.label.target_format"))
        self.output_dir_label.setText(
            t("plugin.image_format_converter.label.output_dir"))
        self.output_path.setPlaceholderText(
            t("plugin.image_format_converter.placeholder.output_dir"))
        self.browse_btn.setText(
            t("plugin.image_format_converter.button.browse"))
        self.action_panel.btn.setText(
            t("plugin.image_format_converter.button.start"))
        # FileListPanel 内部按钮/水印属于共享组件，此处只同步本插件传入的过滤器
        self.file_panel.file_filter = t(
            "plugin.image_format_converter.filter.images")
        self.file_panel.retranslate_ui()

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        self.theme = Theme.DARK

        # 标题 + 描述
        self._setup_header(
            layout,
            title=f"{self.icon} {t('plugin.image_format_converter.name')}",
            desc=t("plugin.image_format_converter.description"),
            theme=self.theme,
        )

        # 文件选择区域
        self.file_card = Card(title=t("plugin.image_format_converter.card.select_images"))
        self.file_panel = FileListPanel(
            columns=IMAGE_COLUMNS,
            file_filter=t("plugin.image_format_converter.filter.images"),
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear"]
        )
        self.file_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(self.file_card)

        # 转换设置
        self.settings_card = Card(title=t("plugin.image_format_converter.card.settings"))
        settings_layout = QGridLayout()
        settings_layout.setSpacing(SPACING_SMALL)
        self.settings_card.content_layout.addLayout(settings_layout)

        self.target_format_label = SelectableLabel(
            t("plugin.image_format_converter.label.target_format"))
        settings_layout.addWidget(self.target_format_label, 0, 0)
        self.fmt_combo = QComboBox()
        for fmt in self.FORMATS:
            self.fmt_combo.addItem(fmt, fmt)
        self.fmt_combo.setStyleSheet(get_combo_style(self.theme))
        settings_layout.addWidget(self.fmt_combo, 0, 1)

        self.output_dir_label = SelectableLabel(
            t("plugin.image_format_converter.label.output_dir"))
        settings_layout.addWidget(self.output_dir_label, 1, 0)
        out_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText(
            t("plugin.image_format_converter.placeholder.output_dir"))
        self.output_path.setStyleSheet(get_lineedit_style(self.theme))
        self.browse_btn = AnimatedButton(
            t("plugin.image_format_converter.button.browse"))
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_output)
        out_row.addWidget(self.output_path)
        out_row.addWidget(self.browse_btn)
        settings_layout.addLayout(out_row, 1, 1)
        layout.addWidget(self.settings_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text=t("plugin.image_format_converter.button.start")
        )
        self.action_panel.clicked.connect(self.start_convert)
        layout.addWidget(self.action_panel)

        # 应用初始主题
        if Theme is not None:
            self.update_theme(Theme.DARK)
        return widget

    def browse_output(self):
        parent = self.widget if self.widget else None
        path = get_existing_directory(
            parent, t("plugin.image_format_converter.dialog.select_output_dir"))
        if path:
            self.output_path.setText(path)

    def start_convert(self):
        files = self.file_panel.get_files()
        if not files:
            self._show_empty_warning(t("plugin.image_format_converter.warning.no_files"))
            return

        self.action_panel.start_task(len(files), status="")

        self.worker = FormatConvertWorker(
            files,
            self.output_path.text() or None,
            self.fmt_combo.currentData()
        )
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.result.connect(self.convert_finished)
        self.worker.start()

    def convert_finished(self, success, message):
        self._finish_with_message(self.action_panel, success, message)
