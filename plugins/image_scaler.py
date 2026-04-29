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
    from toolbox import ToolPlugin, Card, AnimatedButton, DragDropHandler, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, FONT_WEIGHT_700, Theme
except ImportError:
    # 如果导入失败，定义一个简化的基类
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

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QSpinBox, QComboBox, QLineEdit, QProgressBar, QMessageBox,
    QGridLayout, QCheckBox, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


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
            os.makedirs(self.output_dir, exist_ok=True)

            total = len(self.input_files)
            success_count = 0

            for i, input_file in enumerate(self.input_files):
                try:
                    # 打开图片
                    with Image.open(input_file) as img:
                        # 计算新尺寸
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

                        # 缩放图片
                        scaled_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                        # 获取输出文件名
                        input_path = Path(input_file)
                        output_file = os.path.join(
                            self.output_dir,
                            f"{input_path.stem}_scaled{input_path.suffix}"
                        )

                        # 保存图片
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

                # 更新进度
                progress = int((i + 1) / total * 100)
                self.progress_updated.emit(progress, i + 1)

            self.finished.emit(True, f"成功处理 {success_count}/{total} 张图片")

        except Exception as e:
            self.finished.emit(False, f"处理失败: {str(e)}")


class ImageScalerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_files = []
        self.worker = None
        self.setup_ui()

        # 检查PIL是否可用
        if not PIL_AVAILABLE:
            self.status_label.setText("错误: 未安装Pillow库，请运行: pip install Pillow")
            self.start_btn.setEnabled(False)

    def setup_ui(self):
        widget = QWidget()
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标题
        self.title_label = QLabel("📏 图片批量缩放")
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        layout.addWidget(self.title_label)

        # 说明
        self.desc_label = QLabel("支持按百分比或指定尺寸缩放图片，支持保持宽高比和质量设置")
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # 文件选择区域
        file_card = Card(title="选择图片")
        file_layout = file_card.content_layout

        self.file_list = QTextEdit()
        self.file_list.setPlaceholderText("点击按钮选择图片，或拖拽图片文件到此区域...")
        self.file_list.setMaximumHeight(120)
        self.file_list.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                border: 2px dashed #334155;
                border-radius: 8px;
                color: #94a3b8;
                padding: 8px;
            }
            QTextEdit:hover {
                border-color: #475569;
            }
        """)
        file_layout.addWidget(self.file_list)

        # 创建文件列表包装器
        class FileListWrapper:
            def __init__(self, text_edit):
                self.files = []
                self._text_edit = text_edit

            def append(self, file):
                if file not in self.files:
                    self.files.append(file)
                    self._update_display()

            def clear(self):
                self.files.clear()
                self._update_display()

            def _update_display(self):
                self._text_edit.setText("\n".join(
                    f"{i+1}. {os.path.basename(f)}" for i, f in enumerate(self.files)
                ))

        # 创建包装器并设置拖拽功能
        self.file_wrapper = FileListWrapper(self.file_list)
        DragDropHandler.setup_drag_drop(self.file_list, self.file_wrapper)

        btn_layout = QHBoxLayout()
        self.add_btn = AnimatedButton("添加图片")
        self.add_btn.clicked.connect(self.select_files)
        self.clear_btn = AnimatedButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_images)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        layout.addWidget(file_card)

        # 缩放设置区域
        settings_card = Card(title="缩放设置")
        settings_layout = QGridLayout()
        settings_card.content_layout.addLayout(settings_layout)

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

        settings_layout.addWidget(QLabel("缩放方式:"), 0, 0, 1, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scale_type_combo = QComboBox()
        self.scale_type_combo.addItems(["百分比缩放", "指定宽度", "指定高度"])
        self.scale_type_combo.setStyleSheet(combo_style)
        self.scale_type_combo.currentTextChanged.connect(self.on_scale_type_changed)
        settings_layout.addWidget(self.scale_type_combo, 0, 1, 1, 1,
                                  Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.maintain_aspect = QCheckBox("保持宽高比")
        self.maintain_aspect.setChecked(True)
        self.maintain_aspect.setStyleSheet("color: #f1f5f9;")
        self.maintain_aspect.stateChanged.connect(self.on_scale_type_changed)
        settings_layout.addWidget(self.maintain_aspect, 1, 0, 1, 2,
                                  Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        settings_layout.addWidget(QLabel("缩放值:"), 2, 0, 1, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scale_value_input = QSpinBox()
        self.scale_value_input.setRange(1, 200)
        self.scale_value_input.setValue(50)
        self.scale_value_input.setSuffix(" %")
        self.scale_value_input.setStyleSheet(spin_style)
        settings_layout.addWidget(self.scale_value_input, 2, 1, 1, 1,
                                  Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # 宽度设置
        self.width_label = QLabel("宽度:")
        settings_layout.addWidget(self.width_label, 3, 0, 1, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.width_input = QSpinBox()
        self.width_input.setRange(1, 10000)
        self.width_input.setValue(800)
        self.width_input.setSuffix(" px")
        self.width_input.setStyleSheet(spin_style)
        settings_layout.addWidget(self.width_input, 3, 1, 1, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # 高度设置
        self.height_label = QLabel("高度:")
        settings_layout.addWidget(self.height_label, 4, 0, 1, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.height_input = QSpinBox()
        self.height_input.setRange(1, 10000)
        self.height_input.setValue(600)
        self.height_input.setSuffix(" px")
        self.height_input.setStyleSheet(spin_style)
        settings_layout.addWidget(self.height_input, 4, 1, 1, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        settings_layout.addWidget(QLabel("图片质量:"), 5, 0, 1, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高质量 (95)", "标准 (85)", "较小文件 (75)", "最小文件 (50)"])
        self.quality_combo.setCurrentIndex(1)
        self.quality_combo.setStyleSheet(combo_style)
        settings_layout.addWidget(self.quality_combo, 5, 1, 1, 1,
                                  Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(settings_card)

        # 输出设置
        output_card = Card(title="输出设置")
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择输出目录...")
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
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        output_card.content_layout.addLayout(output_layout)
        layout.addWidget(output_card)

        # 操作区
        action_card = Card()
        button_layout = QHBoxLayout()

        self.start_btn = AnimatedButton("开始缩放")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white; border: none; border-radius: 8px;
                font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #34d399, stop:1 #10b981); }}
            QPushButton:disabled {{ background: #334155; color: #64748b; }}
        """)
        self.start_btn.clicked.connect(self.start_scaling)
        self.start_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)

        self.cancel_btn = AnimatedButton("取消")
        self.cancel_btn.setMinimumHeight(48)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ef4444, stop:1 #dc2626);
                color: white; border: none; border-radius: 8px;
                font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f87171, stop:1 #ef4444); }}
            QPushButton:disabled {{ background: #334155; color: #64748b; }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_scaling)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)

        action_card.content_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0f172a;
                border-radius: 6px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 6px;
            }
        """)
        action_card.content_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #94a3b8;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_card.content_layout.addWidget(self.status_label)

        layout.addWidget(action_card)
        layout.addStretch()

        # 初始状态
        self.on_scale_type_changed()

        # 应用初始主题
        if Theme is not None:
            self.apply_theme(Theme.DARK)

    def on_scale_type_changed(self):
        scale_type = self.scale_type_combo.currentText()

        # 显示/隐藏相应的输入框和标签
        if scale_type == "百分比缩放":
            self.scale_value_input.setVisible(True)
            self.width_label.setVisible(False)
            self.width_input.setVisible(False)
            self.height_label.setVisible(False)
            self.height_input.setVisible(False)
            self.maintain_aspect.setVisible(True)
        elif scale_type == "指定宽度":
            self.scale_value_input.setVisible(False)
            self.width_label.setVisible(True)
            self.width_input.setVisible(True)
            self.height_label.setVisible(True)
            self.height_input.setVisible(True)
            self.maintain_aspect.setVisible(True)
            if self.maintain_aspect.isChecked():
                self.height_input.setEnabled(False)
                self.height_input.setSuffix(" (自动)")
            else:
                self.height_input.setEnabled(True)
                self.height_input.setSuffix(" px")
        elif scale_type == "指定高度":
            self.scale_value_input.setVisible(False)
            self.width_label.setVisible(True)
            self.width_input.setVisible(True)
            self.height_label.setVisible(True)
            self.height_input.setVisible(True)
            self.maintain_aspect.setVisible(True)
            if self.maintain_aspect.isChecked():
                self.width_input.setEnabled(False)
                self.width_input.setSuffix(" (自动)")
            else:
                self.width_input.setEnabled(True)
                self.width_input.setSuffix(" px")

    def clear_images(self):
        self.input_files = []
        self.file_wrapper.clear()
        self.start_btn.setEnabled(False)
        self.status_label.setText("就绪")

    def apply_theme(self, theme):
        """应用主题到所有组件"""
        self.file_list.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme['bg']};
                border: 2px dashed {theme['surface']};
                border-radius: 8px;
                color: {theme['text_secondary']};
                padding: 8px;
            }}
            QTextEdit:hover {{
                border-color: {theme['text_secondary']};
            }}
        """)
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
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {theme['error']}, stop:1 {theme.get('error_gradient_end', theme['error'])});
                color: {theme['text']};
                border: none;
                border-radius: 8px;
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {theme['error_hover']}, stop:1 {theme.get('error_gradient_end', theme['error'])}); }}
            QPushButton:disabled {{ background: {theme['surface']}; color: {theme['text_secondary']}; }}
        """)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme['bg']};
                border-radius: 6px;
                text-align: center;
                color: {theme['text']};
            }}
            QProgressBar::chunk {{
                background-color: {theme['success']};
                border-radius: 6px;
            }}
        """)
        self.status_label.setStyleSheet(f"color: {theme['text_secondary']};")

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片文件",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*.*)"
        )

        if files:
            # 避免重复添加文件
            existing_files = set(self.input_files)
            for file in files:
                if file not in existing_files:
                    self.input_files.append(file)
                    self.file_wrapper.append(file)
                    existing_files.add(file)
            if self.input_files and self.output_path.text():
                self.start_btn.setEnabled(True)
            self.status_label.setText(f"已选择 {len(self.input_files)} 个文件")

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            ""
        )

        if dir_path:
            self.output_path.setText(dir_path)
            if self.input_files:
                self.start_btn.setEnabled(True)

    def start_scaling(self):
        if not self.input_files or not self.output_path.text():
            QMessageBox.warning(self, "警告", "请先选择图片文件和输出目录")
            return

        # 获取缩放参数
        scale_type = self.scale_type_combo.currentText()
        quality = int(self.quality_combo.currentText().split("(")[1].split(")")[0])

        # 准备工作线程
        self.worker = ScalingWorker(
            input_files=self.input_files,
            output_dir=self.output_path.text(),
            scale_type=scale_type,
            scale_value=self.scale_value_input.value() if scale_type == "百分比缩放" else 100,
            quality=quality,
            maintain_aspect=self.maintain_aspect.isChecked(),
            width=self.width_input.value() if scale_type in ["指定宽度", "指定高度"] else None,
            height=self.height_input.value() if scale_type in ["指定宽度", "指定高度"] else None
        )

        # 连接信号
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.finished.connect(self.on_scaling_finished)
        self.worker.image_processed.connect(self.on_image_processed)

        # 更新UI
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在处理...")

        # 启动工作线程
        self.worker.start()

    def cancel_scaling(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.status_label.setText("已取消")
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)

    def update_progress(self, value, current):
        self.progress_bar.setValue(value)
        self.status_label.setText(f"正在处理... {current}/{len(self.input_files)}")

    def on_image_processed(self, input_file, output_file):
        # 可以在这里添加更多反馈，比如更新状态
        pass

    def on_scaling_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "错误", message)


class ImageScaler(ToolPlugin):
    icon = "📏"
    name = "图片批量缩放"
    order = 2

    def update_theme(self, theme):
        """更新主题"""
        # 调用 widget 的 apply_theme 方法
        if hasattr(self, 'widget') and hasattr(self.widget, 'apply_theme'):
            self.widget.apply_theme(theme)

    def create_ui(self):
        return ImageScalerWidget()
