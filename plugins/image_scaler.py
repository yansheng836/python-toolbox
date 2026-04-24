import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 导入主程序中的ToolPlugin基类
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin
except ImportError:
    # 如果导入失败，定义一个简化的基类
    class ToolPlugin:
        name = "Base Tool"
        icon = "🔧"

        def create_ui(self):
            raise NotImplementedError("Subclasses must implement create_ui()")

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QSpinBox, QComboBox, QLineEdit, QProgressBar, QMessageBox, QGroupBox,
    QRadioButton, QButtonGroup, QGridLayout, QCheckBox, QListWidget,
    QScrollArea, QFrame
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
                        if self.scale_type == "percentage":
                            if self.maintain_aspect:
                                new_width = int(img.width * self.scale_value / 100)
                                new_height = int(img.height * self.scale_value / 100)
                            else:
                                new_width = int(img.width * self.scale_value / 100)
                                new_height = int(img.height * self.scale_value / 100)
                        elif self.scale_type == "width":
                            new_width = self.width
                            if self.maintain_aspect:
                                new_height = int(img.height * new_width / img.width)
                            else:
                                new_height = self.height
                        elif self.scale_type == "height":
                            new_height = self.height
                            if self.maintain_aspect:
                                new_width = int(img.width * new_height / img.height)
                            else:
                                new_width = self.width

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
        layout = QVBoxLayout(self)

        # 输入文件区域
        input_group = QGroupBox("选择图片文件")
        input_layout = QVBoxLayout()

        # 选择文件按钮
        select_btn = QPushButton("选择图片")
        select_btn.clicked.connect(self.select_files)
        input_layout.addWidget(select_btn)

        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(150)
        input_layout.addWidget(self.file_list)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # 缩放设置区域
        scale_group = QGroupBox("缩放设置")
        scale_layout = QVBoxLayout()

        # 缩放方式
        scale_method_layout = QHBoxLayout()
        self.scale_type_combo = QComboBox()
        self.scale_type_combo.addItems(["百分比缩放", "指定宽度", "指定高度"])
        self.scale_type_combo.currentTextChanged.connect(self.on_scale_type_changed)
        scale_method_layout.addWidget(QLabel("缩放方式:"))
        scale_method_layout.addWidget(self.scale_type_combo)
        scale_method_layout.addStretch()
        scale_layout.addLayout(scale_method_layout)

        # 保持比例
        self.maintain_aspect = QCheckBox("保持宽高比")
        self.maintain_aspect.setChecked(True)
        self.maintain_aspect.stateChanged.connect(self.on_scale_type_changed)
        scale_layout.addWidget(self.maintain_aspect)

        # 缩放参数
        param_layout = QGridLayout()
        param_layout.addWidget(QLabel("缩放值:"), 0, 0)

        self.scale_value_input = QSpinBox()
        self.scale_value_input.setRange(1, 200)
        self.scale_value_input.setValue(50)
        self.scale_value_input.setSuffix(" %")
        param_layout.addWidget(self.scale_value_input, 0, 1)

        self.width_input = QSpinBox()
        self.width_input.setRange(1, 10000)
        self.width_input.setValue(800)
        self.width_input.setSuffix(" px")

        self.height_input = QSpinBox()
        self.height_input.setRange(1, 10000)
        self.height_input.setValue(600)
        self.height_input.setSuffix(" px")

        param_layout.addWidget(self.width_input, 1, 0)
        param_layout.addWidget(self.height_input, 1, 1)

        scale_layout.addLayout(param_layout)

        # 图片质量
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("图片质量:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高质量 (95)", "标准 (85)", "较小文件 (75)", "最小文件 (50)"])
        self.quality_combo.setCurrentIndex(1)
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        scale_layout.addLayout(quality_layout)

        scale_group.setLayout(scale_layout)
        layout.addWidget(scale_group)

        # 输出设置
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout()

        # 选择输出目录
        output_btn_layout = QHBoxLayout()
        self.output_label = QLabel("未选择输出目录")
        output_btn = QPushButton("选择输出目录")
        output_btn.clicked.connect(self.select_output_dir)
        output_btn_layout.addWidget(self.output_label)
        output_btn_layout.addWidget(output_btn)
        output_layout.addLayout(output_btn_layout)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # 操作按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始缩放")
        self.start_btn.clicked.connect(self.start_scaling)
        self.start_btn.setEnabled(False)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_scaling)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 状态信息
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 初始状态
        self.on_scale_type_changed()

    def on_scale_type_changed(self):
        scale_type = self.scale_type_combo.currentText()

        # 显示/隐藏相应的输入框
        if scale_type == "百分比缩放":
            self.scale_value_input.setVisible(True)
            self.width_input.setVisible(False)
            self.height_input.setVisible(False)
            self.maintain_aspect.setVisible(True)
        elif scale_type == "指定宽度":
            self.scale_value_input.setVisible(False)
            self.width_input.setVisible(True)
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
            self.width_input.setVisible(True)
            self.height_input.setVisible(True)
            self.maintain_aspect.setVisible(True)
            if self.maintain_aspect.isChecked():
                self.width_input.setEnabled(False)
                self.width_input.setSuffix(" (自动)")
            else:
                self.width_input.setEnabled(True)
                self.width_input.setSuffix(" px")

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片文件",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*.*)"
        )

        if files:
            self.input_files = files
            self.file_list.clear()
            for file in files:
                self.file_list.addItem(os.path.basename(file))
            self.start_btn.setEnabled(True)
            self.status_label.setText(f"已选择 {len(files)} 个文件")

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            ""
        )

        if dir_path:
            self.output_label.setText(dir_path)
            if self.input_files:
                self.start_btn.setEnabled(True)

    def start_scaling(self):
        if not self.input_files or not self.output_label.text() or self.output_label.text() == "未选择输出目录":
            QMessageBox.warning(self, "警告", "请先选择图片文件和输出目录")
            return

        # 获取缩放参数
        scale_type = self.scale_type_combo.currentText()
        quality = int(self.quality_combo.currentText().split("(")[1].split(")")[0])

        # 准备工作线程
        self.worker = ScalingWorker(
            input_files=self.input_files,
            output_dir=self.output_label.text(),
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

    def create_ui(self):
        return ImageScalerWidget()