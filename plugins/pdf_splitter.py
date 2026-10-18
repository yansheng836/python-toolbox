# -*- encoding: utf-8 -*-
"""
PDF拆分工具插件
将PDF文件拆分为多张图片或单页PDF，支持设置拆分页数
"""
import os
import sys
from io import BytesIO

from common.utils import (
    FITZ_AVAILABLE, PIL_AVAILABLE, check_dir_writable, check_file_writable,
)
from common.i18n import t
from common.dialog_utils import get_existing_directory

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, FONT_WEIGHT_700, Theme

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QSpinBox, QSlider, QRadioButton, QButtonGroup, QFormLayout, QLineEdit
)
from PyQt6.QtCore import Qt

from common.message_utils import show_info, show_error, show_warning
from common.file_list_panel import FileListPanel
from common.action_panel import ActionPanel
from common.utils import PDF_COLUMNS, get_lineedit_style, get_combo_style, get_spinbox_style
from common.base_worker import BaseWorker

if FITZ_AVAILABLE:
    import pymupdf as fitz
if PIL_AVAILABLE:
    from PIL import Image


class PDFSplitWorker(BaseWorker):
    """PDF拆分工作线程"""
    # 继承 BaseWorker 的标准信号：progress, status, finished

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
            # ========= 预检查：输出目录是否可写 =========
            if self.output_path:
                writable, err_msg = check_dir_writable(self.output_path)
                if not writable:
                    self.result.emit(False, err_msg)
                    return

            if not FITZ_AVAILABLE:
                self.result.emit(
                    False, t("plugin.pdf_splitter.error.pymupdf_not_installed"))
                return

            if self.output_format != "pdf" and not PIL_AVAILABLE:
                self.result.emit(
                    False, t("plugin.pdf_splitter.error.install_pillow"))
                return

            doc = fitz.open(self.input_file)
            if doc.is_encrypted and doc.needs_pass:
                doc.close()
                self.result.emit(False, t(
                    "plugin.pdf_splitter.error.encrypted",
                    path=self.input_file))
                return
            total_pages = len(doc)

            skipped = 0
            if self.output_format == "pdf":
                # 按页数拆分PDF
                base_name = os.path.splitext(os.path.basename(self.input_file))[0]
                count = 0
                for i in range(0, total_pages, self.pages_per_split):
                    if self.is_cancelled():
                        doc.close()
                        self.result.emit(False, t("common.msg.task_cancelled"))
                        return
                    self.status.emit(t(
                        "plugin.pdf_splitter.msg.splitting_pages",
                        start=i + 1,
                        end=min(i + self.pages_per_split, total_pages)))
                    end = min(i + self.pages_per_split, total_pages)
                    output_file = os.path.join(self.output_path, f"{base_name}_part{count+1}.pdf")
                    writable, err = check_file_writable(output_file)
                    if not writable:
                        print(f"Skip locked output: {output_file}: {err}")
                        skipped += 1
                        continue
                    new_doc = fitz.open()
                    new_doc.insert_pdf(doc, from_page=i, to_page=end-1)
                    new_doc.save(output_file)
                    new_doc.close()
                    count += 1
                    self.progress.emit(count)
                msg = t("plugin.pdf_splitter.msg.split_done", count=count)
            else:
                # 每页输出为图片
                base_name = os.path.splitext(os.path.basename(self.input_file))[0]
                count = 0
                for i in range(total_pages):
                    if self.is_cancelled():
                        doc.close()
                        self.result.emit(False, t("common.msg.task_cancelled"))
                        return
                    self.status.emit(t(
                        "plugin.pdf_splitter.msg.converting_page",
                        index=i + 1,
                        total=total_pages))
                    page = doc.load_page(i)
                    mat = fitz.Matrix(self.quality / 100, self.quality / 100)
                    pix = page.get_pixmap(matrix=mat)
                    output_file = os.path.join(self.output_path, f"{base_name}_page{i+1}.{self.image_format.lower()}")
                    writable, err = check_file_writable(output_file)
                    if not writable:
                        print(f"Skip locked output: {output_file}: {err}")
                        skipped += 1
                        pix = None
                        continue
                    # 统一经 PIL 保存：PyMuPDF 的 Pixmap.save 对 WebP 支持不稳定
                    self._save_pixmap(pix, output_file)
                    pix = None
                    count += 1
                    self.progress.emit(count)
                msg = t("plugin.pdf_splitter.msg.convert_done", count=count)

            doc.close()
            if skipped:
                msg += t("plugin.pdf_splitter.msg.skipped_locked", count=skipped)
            self.result.emit(True, msg)
        except Exception as e:
            self.result.emit(False, t(
                "plugin.pdf_splitter.error.split_failed", error=str(e)))

    def _save_pixmap(self, pix, output_file):
        """将 PyMuPDF Pixmap 经 PIL 保存为目标格式，JPG/WebP 使用固定质量"""
        image = Image.open(BytesIO(pix.tobytes("png")))
        try:
            fmt = self.image_format.upper()
            if fmt in ("JPG", "JPEG"):
                rgb = image.convert("RGB")
                try:
                    rgb.save(output_file, "JPEG", quality=90)
                finally:
                    rgb.close()
            elif fmt == "WEBP":
                image.save(output_file, "WEBP", quality=90)
            else:
                image.save(output_file, "PNG")
        finally:
            image.close()

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
            self.action_panel.status_label.setText(t(
                "plugin.pdf_splitter.error.pymupdf_missing_status"))
            self.action_panel.btn.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        self.title_label = SelectableLabel(
            f"{self.icon} {t('plugin.pdf_splitter.name')}")
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.desc_label = SelectableLabel(t("plugin.pdf_splitter.description"))
        self.desc_label.setStyleSheet(f"color: {Theme.DARK['text_secondary']}; font-size: {FONT_SIZE_14};")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # PDF文件列表区域（列表模式，参考PDF合并）
        self.file_card = Card(title=t("plugin.pdf_splitter.card.file_list"))
        file_layout = self.file_card.content_layout

        self.file_panel = FileListPanel(
            columns=PDF_COLUMNS,
            file_filter=t("plugin.pdf_splitter.filter.add_files"),
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear"],
            table_min_height=100
        )
        self.file_panel.files_changed.connect(self.auto_set_output_dir)
        file_layout.addWidget(self.file_panel)
        layout.addWidget(self.file_card)

        self.settings_card = Card(title=t("plugin.pdf_splitter.card.settings"))
        settings_layout = QFormLayout()
        settings_layout.setSpacing(12)

        self.format_group = QButtonGroup(self)
        format_layout = QHBoxLayout()
        self.pdf_radio = QRadioButton(t("plugin.pdf_splitter.radio.pdf"))
        self.pdf_radio.setChecked(True)
        self.image_radio = QRadioButton(t("plugin.pdf_splitter.radio.image"))
        self.format_group.addButton(self.pdf_radio)
        self.format_group.addButton(self.image_radio)
        format_layout.addWidget(self.pdf_radio)
        format_layout.addWidget(self.image_radio)
        format_layout.addStretch()
        self.pdf_radio.toggled.connect(self.on_format_changed)
        self.format_label = SelectableLabel(
            t("plugin.pdf_splitter.label.output_format"))
        settings_layout.addRow(self.format_label, format_layout)

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 1000)
        self.pages_spin.setValue(1)
        self.pages_spin.setSuffix(t("plugin.pdf_splitter.spin.suffix"))
        self.pages_label = SelectableLabel(
            t("plugin.pdf_splitter.label.pages_per_split"))
        settings_layout.addRow(self.pages_label, self.pages_spin)

        self.image_format_combo = QComboBox()
        for image_format in ("JPG", "JPEG", "PNG", "WebP"):
            self.image_format_combo.addItem(image_format, image_format)
        self.image_format_combo.setVisible(False)
        self.image_format_label = SelectableLabel(
            t("plugin.pdf_splitter.label.image_format"))
        settings_layout.addRow(self.image_format_label, self.image_format_combo)

        # 图片质量：滚动条 + 百分比标签（参考图片压缩功能）
        quality_widget = QWidget()
        quality_h_layout = QHBoxLayout(quality_widget)
        quality_h_layout.setContentsMargins(0, 0, 0, 0)
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(85)
        self.quality_label = SelectableLabel("85%")
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"{v}%")
        )
        quality_h_layout.addWidget(self.quality_slider)
        quality_h_layout.addWidget(self.quality_label)
        self.quality_widget = quality_widget
        self.quality_row_label = SelectableLabel(
            t("plugin.pdf_splitter.label.quality"))
        settings_layout.addRow(self.quality_row_label, self.quality_widget)
        self.quality_widget.setVisible(False)

        settings_card_layout = self.settings_card.content_layout
        settings_card_layout.addLayout(settings_layout)
        layout.addWidget(self.settings_card)

        self.output_card = Card(title=t("plugin.pdf_splitter.card.output"))
        output_layout = QHBoxLayout()
        self.output_label = SelectableLabel(
            t("plugin.pdf_splitter.label.output_dir"))
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText(
            t("plugin.pdf_splitter.placeholder.output_dir"))
        self.browse_btn = AnimatedButton(t("plugin.pdf_splitter.button.browse"))
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        self.output_card.content_layout.addLayout(output_layout)
        layout.addWidget(self.output_card)

        # 操作面板（按钮 + 进度条 + 状态标签，参考PDF合并）
        # 使用Theme中定义的统一action渐变颜色
        self.action_panel = ActionPanel(
            button_text=t("plugin.pdf_splitter.button.start_split")
        )
        self.action_panel.clicked.connect(self.start_split)
        layout.addWidget(self.action_panel)

        # 应用初始主题
        self.apply_theme(Theme.DARK)

    def apply_theme(self, theme):
        """应用主题到所有组件"""
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_14};")
        if hasattr(self, 'file_panel'):
            self.file_panel.update_theme(theme)
        if hasattr(self, 'output_path'):
            self.output_path.setStyleSheet(get_lineedit_style(theme))
        if hasattr(self, 'output_label'):
            self.output_label.setStyleSheet(f"color: {theme['text']};")
        if hasattr(self, 'pdf_radio'):
            self.pdf_radio.setStyleSheet(f"color: {theme['text']};")
            self.image_radio.setStyleSheet(f"color: {theme['text']};")
        if hasattr(self, 'image_format_combo'):
            self.image_format_combo.setStyleSheet(get_combo_style(theme))
        if hasattr(self, 'pages_spin'):
            self.pages_spin.setStyleSheet(get_spinbox_style(theme))
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
        dir_path = get_existing_directory(
            self,
            t("plugin.pdf_splitter.dialog.choose_output_dir"),
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
            show_warning(
                self,
                t("plugin.pdf_splitter.dialog.warning_title"),
                t("plugin.pdf_splitter.warning.no_file"))
            return
        if len(files) > 1:
            show_warning(
                self,
                t("plugin.pdf_splitter.dialog.warning_title"),
                t("plugin.pdf_splitter.warning.only_one_file"))
            return

        input_file = files[0]

        if not self.output_path.text():
            show_warning(
                self,
                t("plugin.pdf_splitter.dialog.warning_title"),
                t("plugin.pdf_splitter.warning.no_output_dir"))
            return

        if not FITZ_AVAILABLE:
            show_error(
                self,
                t("plugin.pdf_splitter.dialog.error_title"),
                t("plugin.pdf_splitter.error.install_pymupdf"))
            return

        if self.image_radio.isChecked() and not PIL_AVAILABLE:
            show_error(
                self,
                t("plugin.pdf_splitter.dialog.error_title"),
                t("plugin.pdf_splitter.error.install_pillow"))
            return

        output_format = "pdf" if self.pdf_radio.isChecked() else "image"
        pages_per_split = self.pages_spin.value() if output_format == "pdf" else 1
        image_format = self.image_format_combo.currentData()
        quality = self.quality_slider.value()

        # 计算总任务数
        try:
            doc = fitz.open(input_file)
            total = len(doc)
            doc.close()
            if output_format == "pdf":
                total = (total + pages_per_split - 1) // pages_per_split
        except Exception as e:
            print(f"页数估算失败，进度按 100 计：{e}")
            total = 100

        # 启动任务
        self.action_panel.start_task(
            total, status=t("plugin.pdf_splitter.msg.starting"))

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
        self.worker.result.connect(self.split_finished)
        self.action_panel.cancelled.connect(self.worker.cancel)
        self.worker.start()

    def split_finished(self, success, message):
        """拆分完成回调"""
        self.action_panel.finish_task(message)

        if success:
            show_info(self, t("plugin.pdf_splitter.dialog.done_title"), message)
        else:
            show_error(self, t("plugin.pdf_splitter.dialog.error_title"), message)

    def retranslate_ui(self):
        """语言切换后重放全部用户可见文本"""
        self.title_label.setText(f"{self.icon} {t('plugin.pdf_splitter.name')}")
        self.desc_label.setText(t("plugin.pdf_splitter.description"))
        self.file_card.title_label.setText(
            t("plugin.pdf_splitter.card.file_list"))
        # 文件选择过滤器在下次打开对话框时生效（扩展名解析结果不变）
        self.file_panel.file_filter = t("plugin.pdf_splitter.filter.add_files")
        self.file_panel.retranslate_ui()
        self.settings_card.title_label.setText(
            t("plugin.pdf_splitter.card.settings"))
        self.pdf_radio.setText(t("plugin.pdf_splitter.radio.pdf"))
        self.image_radio.setText(t("plugin.pdf_splitter.radio.image"))
        self.format_label.setText(t("plugin.pdf_splitter.label.output_format"))
        self.pages_label.setText(t("plugin.pdf_splitter.label.pages_per_split"))
        self.pages_spin.setSuffix(t("plugin.pdf_splitter.spin.suffix"))
        self.image_format_label.setText(
            t("plugin.pdf_splitter.label.image_format"))
        self.quality_row_label.setText(t("plugin.pdf_splitter.label.quality"))
        self.output_card.title_label.setText(t("plugin.pdf_splitter.card.output"))
        self.output_label.setText(t("plugin.pdf_splitter.label.output_dir"))
        self.output_path.setPlaceholderText(
            t("plugin.pdf_splitter.placeholder.output_dir"))
        self.browse_btn.setText(t("plugin.pdf_splitter.button.browse"))
        self.action_panel.set_button_text(
            t("plugin.pdf_splitter.button.start_split"))
        self.action_panel.set_cancel_text(t("common.action_panel.button.cancel"))
        if not FITZ_AVAILABLE:
            self.action_panel.status_label.setText(t(
                "plugin.pdf_splitter.error.pymupdf_missing_status"))


class PDFSplitter(ToolPlugin):
    """PDF拆分插件"""

    def retranslate_ui(self):
        """语言切换后重放全部用户可见文本"""
        if getattr(self, 'widget', None) is not None:
            self.widget.retranslate_ui()

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

    def load_settings(self):
        w = self.widget
        fmt = self.load_setting("output_format", "pdf")
        if fmt == "image":
            w.image_radio.setChecked(True)
        else:
            w.pdf_radio.setChecked(True)
        w.pages_spin.setValue(self.load_setting("pages_per_split", 1, int))
        self.set_combo_by_data(w.image_format_combo, self.load_setting("image_format", "JPG"))
        w.quality_slider.setValue(self.load_setting("quality", 85, int))
        w.output_path.setText(self.load_setting("output_dir", ""))

    def save_settings(self):
        w = self.widget
        self.save_setting("output_format", "image" if w.image_radio.isChecked() else "pdf")
        self.save_setting("pages_per_split", w.pages_spin.value())
        self.save_setting("image_format", w.image_format_combo.currentData())
        self.save_setting("quality", w.quality_slider.value())
        self.save_setting("output_dir", w.output_path.text().strip())
