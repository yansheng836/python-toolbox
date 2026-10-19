# -*- encoding: utf-8 -*-
"""
image_scaler.py - Module for toolbox
"""

import os
import sys
from pathlib import Path
from typing import List

from common.utils import PIL_AVAILABLE, load_oriented_image, build_failure_detail
if PIL_AVAILABLE:
    from PIL import Image

# 导入主程序中的ToolPlugin基类
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, FONT_WEIGHT_700, Theme
from config import SPACING_SMALL

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QSpinBox, QComboBox, QLineEdit,
    QGridLayout, QCheckBox
)

from common.message_utils import show_info, show_error, show_warning
from PyQt6.QtCore import pyqtSignal

from common.file_list_panel import FileListPanel
from common.utils import IMAGE_COLUMNS, get_combo_style, get_spinbox_style, get_lineedit_style
from common.action_panel import ActionPanel
from common.base_worker import BaseWorker
from common.i18n import t, bind_combo


class ScalingWorker(BaseWorker):
    progress_updated = pyqtSignal(int, int)
    # 继承 BaseWorker 的 result 信号

    def __init__(self, input_files: List[str], output_dir: str, scale_type: str,
                 scale_value: float, quality: int, maintain_aspect: bool,
                 width: int = None, height: int = None):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.scale_type = scale_type
        self.scale_value = scale_value
        self.quality = quality
        self.maintain_aspect = maintain_aspect
        self.width = width
        self.height = height

    def run(self):
        try:
            # ========= 预检查：输出目录是否可写 =========
            from common.utils import check_dir_writable
            output_dir = self.output_dir or os.path.dirname(self.input_files[0]) if self.input_files else '.'
            writable, err_msg = check_dir_writable(output_dir)
            if not writable:
                self.result.emit(False, err_msg)
                return

            # 如果指定了输出目录，则创建
            if self.output_dir:
                os.makedirs(self.output_dir, exist_ok=True)
            total = len(self.input_files)
            success_count = 0
            failed_files = []

            for i, input_file in enumerate(self.input_files):
                if self.is_cancelled():
                    self.result.emit(False, t("common.msg.task_cancelled"))
                    return
                try:
                    img = load_oriented_image(input_file)
                    exif_bytes = img.info.get('exif')
                    try:
                        if self.scale_type == "percent":
                            new_width = max(1, int(img.width * self.scale_value / 100))
                            new_height = max(1, int(img.height * self.scale_value / 100))
                        elif self.scale_type == "width":
                            new_width = self.width
                            if self.maintain_aspect:
                                new_height = max(1, int(img.height * new_width / img.width))
                            else:
                                new_height = self.height
                        elif self.scale_type == "height":
                            new_height = self.height
                            if self.maintain_aspect:
                                new_width = max(1, int(img.width * new_height / img.height))
                            else:
                                new_width = self.width
                        else:
                            raise ValueError(f"unknown scale type: {self.scale_type}")

                        scaled_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    finally:
                        img.close()

                    try:
                        input_path = Path(input_file)
                        # 确定输出目录：如果指定了则用指定的，否则用原图目录
                        output_dir = self.output_dir if self.output_dir else str(input_path.parent)
                        output_file = os.path.join(
                            output_dir,
                            f"{input_path.stem}_scaled{input_path.suffix}"
                        )

                        if input_path.suffix.lower() in ['.jpg', '.jpeg']:
                            scaled_img.save(output_file, "JPEG", quality=self.quality, exif=exif_bytes)
                        elif input_path.suffix.lower() == '.png':
                            scaled_img.save(output_file, "PNG", exif=exif_bytes)
                        else:
                            scaled_img.save(output_file, exif=exif_bytes)
                    finally:
                        scaled_img.close()  # 释放内存

                    success_count += 1

                except Exception as e:
                    print(f"Error processing {input_file}: {str(e)}")
                    failed_files.append(f"{input_file}: {str(e)}")

                progress = int((i + 1) / total * 100)
                self.progress_updated.emit(progress, i + 1)

            result_msg = t(
                "plugin.image_scaler.msg.success", count=success_count, total=total
            )
            if failed_files:
                result_msg += build_failure_detail(failed_files)
            self.result.emit(True, result_msg)

        except Exception as e:
            print(f"Error in image_scaler: {e}")
            self.result.emit(
                False, t("plugin.image_scaler.error.process_failed", error=str(e))
            )


class ImageScalerWidget(QWidget):
    def __init__(self, parent=None, icon="", name="", description="", theme=None):
        super().__init__(parent)
        self.icon = icon
        self.name = name
        self.description = description
        self.theme = theme or Theme.DARK
        self.worker = None
        self.setup_ui()

        if not PIL_AVAILABLE:
            self.action_panel.status_label.setText(t("plugin.image_scaler.error.pil_missing"))
            self.action_panel.btn.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 标题（icon 来自配置，名称由词典提供）
        self.title_label = SelectableLabel(f"{self.icon} {self.name}")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        layout.addWidget(self.title_label)

        # 说明（由词典提供）
        self.desc_label = SelectableLabel(self.description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # 文件选择区域
        self.file_card = Card(title=t("plugin.image_scaler.card.select_images"))
        self.file_panel = FileListPanel(
            columns=IMAGE_COLUMNS,
            file_filter=t("plugin.image_scaler.filter.images"),
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear"]
        )
        self.file_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(self.file_card)

        # 缩放设置区域（参考图片拼接布局方式）
        self.settings_card = Card(title=t("plugin.image_scaler.card.settings"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)   # 两列之间间距，同图片拼接
        grid.setVerticalSpacing(SPACING_SMALL)
        self.settings_card.content_layout.addLayout(grid)

        combo_style = get_combo_style(self.theme)

        spin_style = get_spinbox_style(self.theme)

        # 第0行：缩放方式（跨两列）
        scale_widget = QWidget()
        scale_layout = QHBoxLayout(scale_widget)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.setSpacing(SPACING_SMALL)
        self.scale_type_label = SelectableLabel(t("plugin.image_scaler.label.scale_type"))
        scale_layout.addWidget(self.scale_type_label)
        self.scale_type_combo = QComboBox()
        bind_combo(self.scale_type_combo, [
            ("plugin.image_scaler.combo.percent", "percent"),
            ("plugin.image_scaler.combo.width", "width"),
            ("plugin.image_scaler.combo.height", "height"),
        ])
        self.scale_type_combo.setStyleSheet(combo_style)
        self.scale_type_combo.currentIndexChanged.connect(self.on_scale_type_changed)
        scale_layout.addWidget(self.scale_type_combo, 1)
        grid.addWidget(scale_widget, 0, 0, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # 第1行：缩放值（跨两列）
        self.zoom_row_widget = QWidget()
        zoom_layout = QHBoxLayout(self.zoom_row_widget)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(SPACING_SMALL)
        self.scale_value_label = SelectableLabel(t("plugin.image_scaler.label.scale_value"))
        zoom_layout.addWidget(self.scale_value_label)
        self.scale_value_input = QSpinBox()
        self.scale_value_input.setRange(1, 200)
        self.scale_value_input.setValue(50)
        self.scale_value_input.setSuffix(" %")
        self.scale_value_input.setStyleSheet(spin_style)
        zoom_layout.addWidget(self.scale_value_input, 1)
        grid.addWidget(self.zoom_row_widget, 1, 0, 1, 2)

        # 第2行：宽度（跨两列）
        self.width_row_widget = QWidget()
        width_layout = QHBoxLayout(self.width_row_widget)
        width_layout.setContentsMargins(0, 0, 0, 0)
        width_layout.setSpacing(SPACING_SMALL)
        self.width_label = SelectableLabel(t("plugin.image_scaler.label.width"))
        width_layout.addWidget(self.width_label)
        self.width_input = QSpinBox()
        self.width_input.setRange(1, 10000)
        self.width_input.setValue(800)
        self.width_input.setSuffix(" px")
        self.width_input.setStyleSheet(spin_style)
        width_layout.addWidget(self.width_input, 1)
        grid.addWidget(self.width_row_widget, 2, 0, 1, 2)
        self.width_row_widget.setVisible(False)

        # 第3行：高度（跨两列）
        self.height_row_widget = QWidget()
        height_layout = QHBoxLayout(self.height_row_widget)
        height_layout.setContentsMargins(0, 0, 0, 0)
        height_layout.setSpacing(SPACING_SMALL)
        self.height_label = SelectableLabel(t("plugin.image_scaler.label.height"))
        height_layout.addWidget(self.height_label)
        self.height_input = QSpinBox()
        self.height_input.setRange(1, 10000)
        self.height_input.setValue(600)
        self.height_input.setSuffix(" px")
        self.height_input.setStyleSheet(spin_style)
        height_layout.addWidget(self.height_input, 1)
        grid.addWidget(self.height_row_widget, 3, 0, 1, 2)
        self.height_row_widget.setVisible(False)

        # 第4行：保持宽高比（跨两列，放在宽度/高度后面）
        self.aspect_row_widget = QWidget()
        aspect_layout = QHBoxLayout(self.aspect_row_widget)
        aspect_layout.setContentsMargins(0, 0, 0, 0)
        aspect_layout.setSpacing(SPACING_SMALL)
        aspect_layout.addStretch()
        self.maintain_aspect = QCheckBox(t("plugin.image_scaler.checkbox.maintain_aspect"))
        self.maintain_aspect.setChecked(True)
        self.maintain_aspect.setStyleSheet(f"color: {self.theme['text']};")
        self.maintain_aspect.stateChanged.connect(self.on_scale_type_changed)
        aspect_layout.addWidget(self.maintain_aspect)
        grid.addWidget(self.aspect_row_widget, 4, 0, 1, 2)
        self.aspect_row_widget.setVisible(False)

        # 第5行：图片质量（跨两列）
        self.quality_row_widget = QWidget()
        quality_layout = QHBoxLayout(self.quality_row_widget)
        quality_layout.setContentsMargins(0, 0, 0, 0)
        quality_layout.setSpacing(SPACING_SMALL)
        self.quality_label = SelectableLabel(t("plugin.image_scaler.label.quality"))
        quality_layout.addWidget(self.quality_label)
        self.quality_combo = QComboBox()
        bind_combo(self.quality_combo, [
            ("plugin.image_scaler.combo.95", 95),
            ("plugin.image_scaler.combo.85", 85),
            ("plugin.image_scaler.combo.75", 75),
            ("plugin.image_scaler.combo.50", 50),
        ])
        self.quality_combo.setCurrentIndex(self.quality_combo.findData(85))
        self.quality_combo.setStyleSheet(combo_style)
        quality_layout.addWidget(self.quality_combo, 1)
        grid.addWidget(self.quality_row_widget, 5, 0, 1, 2)

        # 第6行：输出目录（跨两列）
        self.output_row_widget = QWidget()
        output_dir_layout = QHBoxLayout(self.output_row_widget)
        output_dir_layout.setContentsMargins(0, 0, 0, 0)
        output_dir_layout.setSpacing(SPACING_SMALL)
        self.output_dir_label = SelectableLabel(t("plugin.image_scaler.label.output_dir"))
        output_dir_layout.addWidget(self.output_dir_label)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText(t("plugin.image_scaler.placeholder.output_dir"))
        self.output_path.setStyleSheet(get_lineedit_style(self.theme))
        self.browse_btn = AnimatedButton(t("plugin.image_scaler.button.browse"))
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.select_output_dir)
        output_dir_layout.addWidget(self.output_path, 1)
        output_dir_layout.addWidget(self.browse_btn)
        grid.addWidget(self.output_row_widget, 6, 0, 1, 2)

        layout.addWidget(self.settings_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text=t("plugin.image_scaler.button.start")
        )
        self.action_panel.clicked.connect(self.start_scaling)
        layout.addWidget(self.action_panel)

        # 初始状态
        self.on_scale_type_changed()

        # 应用初始主题
        self.apply_theme(Theme.DARK)

    def on_scale_type_changed(self):
        scale_type = self.scale_type_combo.currentData()

        if scale_type == "percent":
            self.zoom_row_widget.setVisible(True)
            self.width_row_widget.setVisible(False)
            self.height_row_widget.setVisible(False)
            self.aspect_row_widget.setVisible(False)
        elif scale_type == "width":
            self.zoom_row_widget.setVisible(False)
            self.width_row_widget.setVisible(True)
            self.height_row_widget.setVisible(True)
            self.aspect_row_widget.setVisible(True)
            self.width_input.setEnabled(True)
            self.width_input.setSuffix(" px")
            if self.maintain_aspect.isChecked():
                self.height_input.setEnabled(False)
                self.height_input.setSuffix(t("plugin.image_scaler.suffix.auto"))
            else:
                self.height_input.setEnabled(True)
                self.height_input.setSuffix(" px")
        elif scale_type == "height":
            self.zoom_row_widget.setVisible(False)
            self.width_row_widget.setVisible(True)
            self.height_row_widget.setVisible(True)
            self.aspect_row_widget.setVisible(True)
            self.height_input.setEnabled(True)
            self.height_input.setSuffix(" px")
            if self.maintain_aspect.isChecked():
                self.width_input.setEnabled(False)
                self.width_input.setSuffix(t("plugin.image_scaler.suffix.auto"))
            else:
                self.width_input.setEnabled(True)
                self.width_input.setSuffix(" px")

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, t("plugin.image_scaler.dialog.select_output_dir"), ""
        )
        if dir_path:
            self.output_path.setText(dir_path)

    def start_scaling(self):
        files = self.file_panel.get_files()
        if not files:
            show_warning(
                self,
                t("plugin.image_scaler.dialog.warning"),
                t("plugin.image_scaler.warning.no_files"),
            )
            return

        scale_type = self.scale_type_combo.currentData()
        quality = self.quality_combo.currentData()

        self.worker = ScalingWorker(
            input_files=files,
            output_dir=self.output_path.text(),
            scale_type=scale_type,
            scale_value=self.scale_value_input.value() if scale_type == "percent" else 100,
            quality=quality,
            maintain_aspect=self.maintain_aspect.isChecked(),
            width=self.width_input.value() if scale_type in ("width", "height") else None,
            height=self.height_input.value() if scale_type in ("width", "height") else None
        )

        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.result.connect(self.on_scaling_finished)

        self.action_panel.start_task(
            len(files), status=t("plugin.image_scaler.msg.processing")
        )

        self.action_panel.cancelled.connect(self.worker.cancel)
        self.worker.start()

    def on_progress_updated(self, progress, current):
        # 进度条最大值为文件数（start_task(len(files))），故喂 current(i+1)
        # 而非 0-100 百分比，避免维度不一致导致进度条瞬间打满（M-A）
        self.action_panel.update_progress(current)
        total = len(self.file_panel.get_files())
        self.action_panel.update_status(
            t("plugin.image_scaler.msg.progress", count=current, total=total)
        )

    def on_scaling_finished(self, success, message):
        self.action_panel.finish_task(message)

        if success:
            show_info(self, t("plugin.image_scaler.dialog.done"), message)
        else:
            show_error(self, t("plugin.image_scaler.dialog.error"), message)

    def apply_theme(self, theme):
        """应用主题到所有组件"""
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700}; color: {theme['text']};")
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_14};")
        if hasattr(self, 'file_panel'):
            self.file_panel.update_theme(theme)
        if hasattr(self, 'action_panel'):
            self.action_panel.update_theme(theme)
        combo_style = get_combo_style(theme)
        self.scale_type_combo.setStyleSheet(combo_style)
        self.quality_combo.setStyleSheet(combo_style)
        spin_style = get_spinbox_style(theme)
        self.scale_value_input.setStyleSheet(spin_style)
        self.width_input.setStyleSheet(spin_style)
        self.height_input.setStyleSheet(spin_style)
        self.maintain_aspect.setStyleSheet(f"color: {theme['text']};")
        self.output_path.setStyleSheet(get_lineedit_style(theme))


class ImageScaler(ToolPlugin):
    def update_theme(self, theme):
        if hasattr(self, 'widget') and hasattr(self.widget, 'apply_theme'):
            self.widget.apply_theme(theme)

    def create_ui(self):
        widget = ImageScalerWidget(
            icon=self.icon,
            name=t("plugin.image_scaler.name"),
            description=t("plugin.image_scaler.description"),
        )
        # 将 Widget 的标签属性复制到插件实例，统一访问入口
        self.title_label = widget.title_label
        self.desc_label = widget.desc_label
        self.widget = widget
        return widget

    def load_settings(self):
        w = self.widget
        self.set_combo_by_data(w.scale_type_combo, self.load_setting("scale_type", "percent"))
        w.scale_value_input.setValue(self.load_setting("scale_value", 50, int))
        w.width_input.setValue(self.load_setting("width", 800, int))
        w.height_input.setValue(self.load_setting("height", 600, int))
        w.maintain_aspect.setChecked(self.load_setting("maintain_aspect", True, bool))
        self.set_combo_by_data(w.quality_combo, self.load_setting("quality", 85, int))
        w.output_path.setText(self.load_setting("output_dir", ""))

    def save_settings(self):
        w = self.widget
        self.save_setting("scale_type", w.scale_type_combo.currentData())
        self.save_setting("scale_value", w.scale_value_input.value())
        self.save_setting("width", w.width_input.value())
        self.save_setting("height", w.height_input.value())
        self.save_setting("maintain_aspect", 1 if w.maintain_aspect.isChecked() else 0)
        self.save_setting("quality", w.quality_combo.currentData())
        self.save_setting("output_dir", w.output_path.text().strip())

    def retranslate_ui(self):
        """语言切换后重放图片缩放页全部用户可见文本"""
        widget = getattr(self, 'widget', None)
        if widget is None:
            return

        widget.title_label.setText(f"{widget.icon} {t('plugin.image_scaler.name')}")
        widget.desc_label.setText(t("plugin.image_scaler.description"))
        widget.file_card.title_label.setText(
            t("plugin.image_scaler.card.select_images")
        )
        widget.settings_card.title_label.setText(t("plugin.image_scaler.card.settings"))
        widget.scale_type_label.setText(t("plugin.image_scaler.label.scale_type"))
        widget.scale_value_label.setText(t("plugin.image_scaler.label.scale_value"))
        widget.width_label.setText(t("plugin.image_scaler.label.width"))
        widget.height_label.setText(t("plugin.image_scaler.label.height"))
        widget.maintain_aspect.setText(
            t("plugin.image_scaler.checkbox.maintain_aspect")
        )
        widget.quality_label.setText(t("plugin.image_scaler.label.quality"))
        widget.output_dir_label.setText(t("plugin.image_scaler.label.output_dir"))
        widget.output_path.setPlaceholderText(
            t("plugin.image_scaler.placeholder.output_dir")
        )
        widget.browse_btn.setText(t("plugin.image_scaler.button.browse"))
        widget.action_panel.set_button_text(t("plugin.image_scaler.button.start"))
        widget.action_panel.set_cancel_text(t("common.action_panel.button.cancel"))
        # 文件选择过滤器在每次打开对话框时读取，需同步更新
        widget.file_panel.file_filter = t("plugin.image_scaler.filter.images")
        widget.file_panel.retranslate_ui()
        # 组合框由 bind_combo 自动重放；这里刷新「(自动)」后缀等动态文本
        widget.on_scale_type_changed()
