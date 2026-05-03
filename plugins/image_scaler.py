import os
import sys
from pathlib import Path
from typing import List

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 导入主程序中的ToolPlugin基类
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin, Card, AnimatedButton, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, FONT_WEIGHT_700, Theme
    from config import SPACING_SMALL, SPACING_MEDIUM
except ImportError:
    Theme = None
    SPACING_SMALL = 8
    SPACING_MEDIUM = 20
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

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QSpinBox, QComboBox, QLineEdit, QProgressBar,
    QGridLayout, QCheckBox
)

from common.message_utils import show_info, show_error, show_warning
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from common.file_list_panel import FileListPanel
from common.utils import IMAGE_COLUMNS
from common.action_panel import ActionPanel


class ScalingWorker(QThread):
    progress_updated = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str)
    image_processed = pyqtSignal(str, str)

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
            # 如果指定了输出目录，则创建
            if self.output_dir:
                os.makedirs(self.output_dir, exist_ok=True)
            total = len(self.input_files)
            success_count = 0

            for i, input_file in enumerate(self.input_files):
                try:
                    with Image.open(input_file) as img:
                        if self.scale_type == "百分比缩放":
                            new_width = int(img.width * self.scale_value / 100)
                            new_height = int(img.height * self.scale_value / 100)
                        elif self.scale_type == "指定宽度":
                            new_width = self.width
                            if self.maintain_aspect:
                                new_height = int(img.height * new_width / img.width)
                            else:
                                new_height = self.height
                        elif self.scale_type == "指定高度":
                            new_height = self.height
                            if self.maintain_aspect:
                                new_width = int(img.width * new_height / img.height)
                            else:
                                new_width = self.width
                        else:
                            raise ValueError(f"未知缩放类型: {self.scale_type}")

                        scaled_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                        input_path = Path(input_file)
                        # 确定输出目录：如果指定了则用指定的，否则用原图目录
                        output_dir = self.output_dir if self.output_dir else str(input_path.parent)
                        output_file = os.path.join(
                            output_dir,
                            f"{input_path.stem}_scaled{input_path.suffix}"
                        )

                        if input_path.suffix.lower() in ['.jpg', '.jpeg']:
                            scaled_img.save(output_file, "JPEG", quality=self.quality)
                        elif input_path.suffix.lower() == '.png':
                            scaled_img.save(output_file, "PNG")
                        else:
                            scaled_img.save(output_file)

                        success_count += 1
                        self.image_processed.emit(input_file, output_file)

                except Exception as e:
                    print(f"Error processing {input_file}: {str(e)}")

                progress = int((i + 1) / total * 100)
                self.progress_updated.emit(progress, i + 1)

            self.finished.emit(True, f"成功处理 {success_count}/{total} 张图片")

        except Exception as e:
            self.finished.emit(False, f"处理失败: {str(e)}")


class ImageScalerWidget(QWidget):
    def __init__(self, parent=None, icon="", name="", description=""):
        super().__init__(parent)
        self.icon = icon
        self.name = name
        self.description = description
        self.worker = None
        self.setup_ui()

        if not PIL_AVAILABLE:
            self.status_label.setText("错误: 未安装Pillow库，请运行: pip install Pillow")
            self.start_btn.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 标题（使用 PLUGIN_MODULES 配置中的 icon + name）
        self.title_label = QLabel(f"{self.icon} {self.name}")
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        layout.addWidget(self.title_label)

        # 说明（使用 PLUGIN_MODULES 配置中的 description）
        self.desc_label = QLabel(self.description)
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # 文件选择区域
        file_card = Card(title="选择图片")
        self.file_panel = FileListPanel(
            columns=IMAGE_COLUMNS,
            file_filter="图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*.*)",
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear"]
        )
        file_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(file_card)

        # 缩放设置区域（参考图片拼接布局方式）
        settings_card = Card(title="缩放设置")
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)   # 两列之间间距，同图片拼接
        grid.setVerticalSpacing(SPACING_SMALL)
        settings_card.content_layout.addLayout(grid)

        combo_style = """
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """

        spin_style = """
            QSpinBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
                color: #f1f5f9;
                text-align: left;
            }
        """

        # 第0行：缩放方式（跨两列）
        scale_widget = QWidget()
        scale_layout = QHBoxLayout(scale_widget)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.setSpacing(SPACING_SMALL)
        scale_layout.addWidget(QLabel("缩放方式:"))
        self.scale_type_combo = QComboBox()
        self.scale_type_combo.addItems(["百分比缩放", "指定宽度", "指定高度"])
        self.scale_type_combo.setStyleSheet(combo_style)
        self.scale_type_combo.currentTextChanged.connect(self.on_scale_type_changed)
        scale_layout.addWidget(self.scale_type_combo, 1)
        grid.addWidget(scale_widget, 0, 0, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # 第1行：缩放值（跨两列）
        self.zoom_row_widget = QWidget()
        zoom_layout = QHBoxLayout(self.zoom_row_widget)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(SPACING_SMALL)
        zoom_layout.addWidget(QLabel("缩放值:"))
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
        self.width_label = QLabel("宽度:")
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
        self.height_label = QLabel("高度:")
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
        self.maintain_aspect = QCheckBox("保持宽高比")
        self.maintain_aspect.setChecked(True)
        self.maintain_aspect.setStyleSheet("color: #f1f5f9;")
        self.maintain_aspect.stateChanged.connect(self.on_scale_type_changed)
        aspect_layout.addWidget(self.maintain_aspect)
        grid.addWidget(self.aspect_row_widget, 4, 0, 1, 2)
        self.aspect_row_widget.setVisible(False)

        # 第5行：图片质量（跨两列）
        self.quality_row_widget = QWidget()
        quality_layout = QHBoxLayout(self.quality_row_widget)
        quality_layout.setContentsMargins(0, 0, 0, 0)
        quality_layout.setSpacing(SPACING_SMALL)
        quality_layout.addWidget(QLabel("图片质量:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高质量 (95)", "标准 (85)", "较小文件 (75)", "最小文件 (50)"])
        self.quality_combo.setCurrentIndex(1)
        self.quality_combo.setStyleSheet(combo_style)
        quality_layout.addWidget(self.quality_combo, 1)
        grid.addWidget(self.quality_row_widget, 5, 0, 1, 2)

        # 第6行：输出目录（跨两列）
        self.output_row_widget = QWidget()
        output_dir_layout = QHBoxLayout(self.output_row_widget)
        output_dir_layout.setContentsMargins(0, 0, 0, 0)
        output_dir_layout.setSpacing(SPACING_SMALL)
        output_dir_layout.addWidget(QLabel("输出目录:"))
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("默认保存到原图目录（图片缩放后带 _scaled 后缀）")
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
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.select_output_dir)
        output_dir_layout.addWidget(self.output_path, 1)
        output_dir_layout.addWidget(self.browse_btn)
        grid.addWidget(self.output_row_widget, 6, 0, 1, 2)

        layout.addWidget(settings_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text="开始缩放"
        )
        self.action_panel.clicked.connect(self.start_scaling)
        layout.addWidget(self.action_panel)

        layout.addStretch()

        # 初始状态
        self.on_scale_type_changed()

        # 应用初始主题
        if Theme is not None:
            self.apply_theme(Theme.DARK)

    def on_scale_type_changed(self):
        scale_type = self.scale_type_combo.currentText()

        if scale_type == "百分比缩放":
            self.zoom_row_widget.setVisible(True)
            self.width_row_widget.setVisible(False)
            self.height_row_widget.setVisible(False)
            self.aspect_row_widget.setVisible(False)
        elif scale_type == "指定宽度":
            self.zoom_row_widget.setVisible(False)
            self.width_row_widget.setVisible(True)
            self.height_row_widget.setVisible(True)
            self.aspect_row_widget.setVisible(True)
            # 指定宽度模式下，宽度始终可编辑
            self.width_input.setEnabled(True)
            self.width_input.setSuffix(" px")
            # 高度的可编辑性取决于是否保持宽高比
            if self.maintain_aspect.isChecked():
                self.height_input.setEnabled(False)
                self.height_input.setSuffix(" (自动)")
            else:
                self.height_input.setEnabled(True)
                self.height_input.setSuffix(" px")
        elif scale_type == "指定高度":
            self.zoom_row_widget.setVisible(False)
            self.width_row_widget.setVisible(True)
            self.height_row_widget.setVisible(True)
            self.aspect_row_widget.setVisible(True)
            # 指定高度模式下，高度始终可编辑
            self.height_input.setEnabled(True)
            self.height_input.setSuffix(" px")
            # 宽度的可编辑性取决于是否保持宽高比
            if self.maintain_aspect.isChecked():
                self.width_input.setEnabled(False)
                self.width_input.setSuffix(" (自动)")
            else:
                self.width_input.setEnabled(True)
                self.width_input.setSuffix(" px")

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", ""
        )
        if dir_path:
            self.output_path.setText(dir_path)

    def start_scaling(self):
        files = self.file_panel.get_files()
        if not files:
            show_warning(self, "警告", "请先添加图片！")
            return

        scale_type = self.scale_type_combo.currentText()
        quality = int(self.quality_combo.currentText().split("(")[1].split(")")[0])

        self.worker = ScalingWorker(
            input_files=files,
            output_dir=self.output_path.text(),
            scale_type=scale_type,
            scale_value=self.scale_value_input.value() if scale_type == "百分比缩放" else 100,
            quality=quality,
            maintain_aspect=self.maintain_aspect.isChecked(),
            width=self.width_input.value() if scale_type in ["指定宽度", "指定高度"] else None,
            height=self.height_input.value() if scale_type in ["指定宽度", "指定高度"] else None
        )

        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.finished.connect(self.on_scaling_finished)
        self.worker.image_processed.connect(self.on_image_processed)

        self.action_panel.start_task(len(files), status="正在处理...")

        self.worker.start()

    def on_progress_updated(self, progress, current):
        self.action_panel.update_progress(progress)
        total = len(self.file_panel.get_files())
        self.action_panel.update_status(f"正在处理... {current}/{total}")

    def on_image_processed(self, input_file, output_file):
        pass

    def on_scaling_finished(self, success, message):
        self.action_panel.finish_task(message)

        if success:
            show_info(self, "完成", message)
        else:
            show_error(self, "错误", message)

    def apply_theme(self, theme):
        """应用主题到所有组件"""
        if hasattr(self, 'file_panel'):
            self.file_panel.update_theme(theme)
        if hasattr(self, 'action_panel'):
            self.action_panel.update_theme(theme)
        combo_style = f"""
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
        """
        self.scale_type_combo.setStyleSheet(combo_style)
        self.quality_combo.setStyleSheet(combo_style)
        spin_style = f"""
            QSpinBox {{
                background-color: {theme['bg']};
                border: 1px solid {theme['surface']};
                border-radius: 6px;
                padding: 4px;
                color: {theme['text']};
                text-align: left;
            }}
        """
        self.scale_value_input.setStyleSheet(spin_style)
        self.width_input.setStyleSheet(spin_style)
        self.height_input.setStyleSheet(spin_style)
        self.maintain_aspect.setStyleSheet(f"color: {theme['text']};")
        self.output_path.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['bg']};
                border: 1px solid {theme['surface']};
                border-radius: 6px;
                padding: 6px;
                color: {theme['text']};
            }}
        """)


class ImageScaler(ToolPlugin):
    def update_theme(self, theme):
        if hasattr(self, 'widget') and hasattr(self.widget, 'apply_theme'):
            self.widget.apply_theme(theme)

    def create_ui(self):
        widget = ImageScalerWidget(icon=self.icon, name=self.name, description=self.description)
        # 将 Widget 的标签属性复制到插件实例，统一访问入口
        self.title_label = widget.title_label
        self.desc_label = widget.desc_label
        return widget
