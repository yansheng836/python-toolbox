"""
图片拼接插件
多图横向/纵向合并为一张
"""
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QComboBox, QSpinBox, QGridLayout, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 导入主程序中的基类和组件
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin, Card, AnimatedButton, DragDropHandler, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, Theme
except ImportError:
    ToolPlugin = object
    Card = None
    AnimatedButton = None
    DragDropHandler = None
    Theme = None


class ImageStitchWorker(QThread):
    """图片拼接工作线程"""
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output_path, direction, align, bg_color):
        super().__init__()
        self.files = files
        self.output_path = output_path
        self.direction = direction  # "horizontal" | "vertical"
        self.align = align  # "start" | "center" | "end"
        self.bg_color = bg_color  # (R, G, B)

    def run(self):
        try:
            images = []
            for f in self.files:
                self.status.emit(f"正在读取: {os.path.basename(f)}")
                images.append(Image.open(f).convert("RGBA"))

            self.status.emit("正在拼接...")
            if self.direction == "horizontal":
                total_w = sum(img.width for img in images)
                total_h = max(img.height for img in images)
                canvas = Image.new("RGBA", (total_w, total_h), self.bg_color + (255,))
                x = 0
                for img in images:
                    if self.align == "center":
                        y = (total_h - img.height) // 2
                    elif self.align == "end":
                        y = total_h - img.height
                    else:
                        y = 0
                    canvas.paste(img, (x, y), img)
                    x += img.width
            else:
                total_w = max(img.width for img in images)
                total_h = sum(img.height for img in images)
                canvas = Image.new("RGBA", (total_w, total_h), self.bg_color + (255,))
                y = 0
                for img in images:
                    if self.align == "center":
                        x = (total_w - img.width) // 2
                    elif self.align == "end":
                        x = total_w - img.width
                    else:
                        x = 0
                    canvas.paste(img, (x, y), img)
                    y += img.height

            # 输出格式不支持透明时转 RGB
            ext = os.path.splitext(self.output_path)[1].lower()
            if ext in (".jpg", ".jpeg", ".bmp"):
                bg = Image.new("RGB", canvas.size, self.bg_color)
                bg.paste(canvas, mask=canvas.split()[3])
                canvas = bg

            canvas.save(self.output_path)
            self.finished.emit(True, f"拼接完成，已保存到:\n{self.output_path}")
        except Exception as e:
            self.finished.emit(False, f"拼接失败: {str(e)}")


class ImageStitcher(ToolPlugin):
    """图片拼接工具"""
    name = "图片拼接"
    description = "多图横向/纵向合并为一张"
    icon = "📐"
    order = 4

    class FileListWrapper:
        """文件列表包装器"""
        def __init__(self, text_edit, refresh_callback):
            self.files = []
            self._text_edit = text_edit
            self._refresh_callback = refresh_callback

        def append(self, file):
            if file not in self.files:
                self.files.append(file)
                self._refresh_callback()

        def extend(self, files):
            for f in files:
                if f not in self.files:
                    self.files.append(f)
            self._refresh_callback()

        def clear(self):
            self.files.clear()
            self._text_edit.clear()

        def pop(self, index=-1):
            result = self.files.pop(index)
            self._refresh_callback()
            return result

        def insert(self, index, item):
            self.files.insert(index, item)
            self._refresh_callback()

    def setup_drag_handler(self):
        """设置拖拽处理器"""
        if hasattr(self, 'file_list'):
            DragDropHandler.setup_drag_drop(self.file_list, self.files)

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
            if hasattr(self, 'file_list'):
                self.file_list.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: {theme['bg']};
                        border: 2px dashed {theme['surface']};
                        border-radius: 8px;
                        color: {theme['text_secondary']};
                        padding: 8px;
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
            """
            if hasattr(self, 'dir_combo'):
                self.dir_combo.setStyleSheet(combo_style)
            if hasattr(self, 'align_combo'):
                self.align_combo.setStyleSheet(combo_style)
            spin_style = f"""
                QSpinBox {{
                    background-color: {theme['bg']};
                    border: 1px solid {theme['surface']};
                    border-radius: 6px;
                    padding: 4px;
                    color: {theme['text']};
                    max-width: 60px;
                }}
            """
            for spin in [getattr(self, 'bg_r', None), getattr(self, 'bg_g', None), getattr(self, 'bg_b', None)]:
                if spin:
                    spin.setStyleSheet(spin_style)
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
        layout.setSpacing(16)

        self.title_label = QLabel(self.icon + " " + self.name + "工具")
        self.title_label.setStyleSheet(
            f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']};"
        )
        layout.addWidget(self.title_label)

        self.desc_label = QLabel("将多张图片横向或纵向合并为一张，支持对齐方式和背景色设置")
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # 文件列表
        file_card = Card(title="选择图片（顺序即拼接顺序）")
        self.file_list = QTextEdit()
        self.file_list.setPlaceholderText("拖拽图片到此处，或点击按钮选择...")
        self.file_list.setMaximumHeight(120)
        self.file_list.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                border: 2px dashed #334155;
                border-radius: 8px;
                color: #94a3b8;
                padding: 8px;
            }
        """)
        file_card.content_layout.addWidget(self.file_list)

        btn_layout = QHBoxLayout()
        add_btn = AnimatedButton("添加图片")
        add_btn.clicked.connect(self.add_images)
        up_btn = AnimatedButton("↑ 上移")
        up_btn.clicked.connect(self.move_up)
        down_btn = AnimatedButton("↓ 下移")
        down_btn.clicked.connect(self.move_down)
        clear_btn = AnimatedButton("清空列表")
        clear_btn.clicked.connect(self.clear_images)
        for b in (add_btn, up_btn, down_btn, clear_btn):
            btn_layout.addWidget(b)
        btn_layout.addStretch()
        file_card.content_layout.addLayout(btn_layout)
        layout.addWidget(file_card)

        # 拼接设置
        settings_card = Card(title="拼接设置")
        grid = QGridLayout()
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

        grid.addWidget(QLabel("拼接方向:"), 0, 0)
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["横向（左→右）", "纵向（上→下）"])
        self.dir_combo.setStyleSheet(combo_style)
        grid.addWidget(self.dir_combo, 0, 1)

        grid.addWidget(QLabel("对齐方式:"), 1, 0)
        self.align_combo = QComboBox()
        self.align_combo.addItems(["顶部/左侧对齐", "居中对齐", "底部/右侧对齐"])
        self.align_combo.setStyleSheet(combo_style)
        grid.addWidget(self.align_combo, 1, 1)

        grid.addWidget(QLabel("背景颜色:"), 2, 0)
        bg_row = QHBoxLayout()
        self.bg_r = QSpinBox()
        self.bg_r.setRange(0, 255)
        self.bg_r.setValue(255)
        self.bg_g = QSpinBox()
        self.bg_g.setRange(0, 255)
        self.bg_g.setValue(255)
        self.bg_b = QSpinBox()
        self.bg_b.setRange(0, 255)
        self.bg_b.setValue(255)
        spin_style = """
            QSpinBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
                color: #f1f5f9;
                max-width: 60px;
            }
        """
        for label, spin in (("R", self.bg_r), ("G", self.bg_g), ("B", self.bg_b)):
            bg_row.addWidget(QLabel(label))
            spin.setStyleSheet(spin_style)
            bg_row.addWidget(spin)
        bg_row.addStretch()
        grid.addLayout(bg_row, 2, 1)

        grid.addWidget(QLabel("输出文件:"), 3, 0)
        out_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择保存路径...")
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
        grid.addLayout(out_row, 3, 1)
        layout.addWidget(settings_card)

        # 操作区
        action_card = Card()
        self.start_btn = AnimatedButton("开始拼接")
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
        self.start_btn.clicked.connect(self.start_stitch)
        action_card.content_layout.addWidget(self.start_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #94a3b8;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_card.content_layout.addWidget(self.status_label)
        layout.addWidget(action_card)
        layout.addStretch()

        self.files = self.FileListWrapper(self.file_list, self._refresh_list)
        # 应用初始主题
        if Theme is not None:
            self.update_theme(Theme.DARK)
        return widget

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            None, "选择图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif *.gif)"
        )
        if files:
            self.files.extend(files)

    def move_up(self):
        if len(self.files.files) > 1:
            self.files.insert(0, self.files.pop())
            self._refresh_list()

    def move_down(self):
        if len(self.files.files) > 1:
            self.files.insert(0, self.files.pop())
            self._refresh_list()

    def clear_images(self):
        self.files.clear()

    def _refresh_list(self):
        self.file_list.setText("\n".join(
            f"{i+1}. {os.path.basename(f)}" for i, f in enumerate(self.files.files)
        ))

    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            None, "保存拼接图片", "stitched.png",
            "PNG (*.png);;JPEG (*.jpg);;WebP (*.webp)"
        )
        if path:
            self.output_path.setText(path)

    def start_stitch(self):
        if len(self.files.files) < 2:
            QMessageBox.warning(None, "警告", "请至少添加 2 张图片！")
            return
        if not self.output_path.text():
            QMessageBox.warning(None, "警告", "请选择输出文件路径！")
            return

        direction = "horizontal" if self.dir_combo.currentIndex() == 0 else "vertical"
        align_map = {0: "start", 1: "center", 2: "end"}
        align = align_map[self.align_combo.currentIndex()]
        bg = (self.bg_r.value(), self.bg_g.value(), self.bg_b.value())

        self.start_btn.setEnabled(False)
        self.worker = ImageStitchWorker(
            self.files.files, self.output_path.text(), direction, align, bg
        )
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.stitch_finished)
        self.worker.start()

    def stitch_finished(self, success, message):
        self.start_btn.setEnabled(True)
        self.status_label.setText("")
        if success:
            QMessageBox.information(None, "完成", message)
        else:
            QMessageBox.critical(None, "错误", message)
