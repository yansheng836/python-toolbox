"""
图片拼接插件
多图横向/纵向合并为一张
"""
import os
import sys
import traceback

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QComboBox, QSpinBox, QGridLayout, QLineEdit
)

from common.message_utils import show_info, show_error, show_warning
from common.dialog_utils import get_save_file_name
from common.action_panel import ActionPanel
from PyQt6.QtCore import Qt, QThread, pyqtSignal

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 导入主程序中的基类和组件
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin, Card, AnimatedButton, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, \
        Theme
    from config import SPACING_SMALL, SPACING_MEDIUM
except ImportError:
    ToolPlugin = object
    Card = None
    AnimatedButton = None
    DragDropHandler = None
    Theme = None
    SPACING_SMALL = 8
    SPACING_MEDIUM = 20

from common.file_list_panel import FileListPanel
from common.utils import IMAGE_COLUMNS, get_create_time


class ImageStitchWorker(QThread):
    """图片拼接工作线程"""
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output_path, direction, align, bg_color):
        super().__init__()
        self.files = files
        self.output_path = output_path
        self.direction = direction  # "horizontal" | "vertical"
        self.align = align  # "start" | "center" | "end" | "max_size"
        self.bg_color = bg_color  # (R, G, B)

    def run(self):
        try:
            images = []
            skipped = 0
            for f in self.files:
                self.status.emit(f"正在读取: {os.path.basename(f)}")
                try:
                    img = Image.open(f)
                    img.load()  # 强制加载，提前发现损坏文件
                    images.append(img.convert("RGBA"))
                except Exception as e:
                    skipped += 1
                    self.status.emit(f"跳过损坏图片: {os.path.basename(f)}")
                    continue

            if not images:
                self.finished.emit(False, "没有成功读取任何图片，请检查图片文件是否损坏。")
                return

            # 按最大尺寸扩展：先缩放图片
            if self.align == "max_size":
                self.status.emit("正在按最大尺寸缩放图片...")
                if self.direction == "vertical":
                    # 纵向拼接：找出宽度最大的图片，其他图片按比例缩放
                    max_width = max(img.width for img in images)
                    scaled_images = []
                    for img in images:
                        if img.width != max_width:
                            ratio = max_width / img.width
                            new_height = int(img.height * ratio)
                            scaled = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                            scaled_images.append(scaled)
                        else:
                            scaled_images.append(img)
                    images = scaled_images
                else:
                    # 横向拼接：找出高度最大的图片，其他图片按比例缩放
                    max_height = max(img.height for img in images)
                    scaled_images = []
                    for img in images:
                        if img.height != max_height:
                            ratio = max_height / img.height
                            new_width = int(img.width * ratio)
                            scaled = img.resize((new_width, max_height), Image.Resampling.LANCZOS)
                            scaled_images.append(scaled)
                        else:
                            scaled_images.append(img)
                    images = scaled_images

            # 检查拼接后尺寸，避免超大图片导致失败
            if self.direction == "horizontal":
                total_w = sum(img.width for img in images)
                total_h = max(img.height for img in images)
            else:
                total_w = max(img.width for img in images)
                total_h = sum(img.height for img in images)

            MAX_DIMENSION = 65535  # 多数格式支持的最大尺寸
            if total_w > MAX_DIMENSION or total_h > MAX_DIMENSION:
                self.finished.emit(False,
                                   f"拼接后尺寸过大（{total_w}x{total_h}），超过 {MAX_DIMENSION} 像素限制。\n"
                                   f"建议：1) 减少图片数量；2) 先缩小图片尺寸；3) 使用纵向拼接代替横向。")
                return

            self.status.emit("正在拼接...")
            # 按最大尺寸扩展后，使用 start 对齐（因为尺寸已统一）
            align = "start" if self.align == "max_size" else self.align

            if self.direction == "horizontal":
                total_w = sum(img.width for img in images)
                total_h = max(img.height for img in images)
                canvas = Image.new("RGBA", (total_w, total_h), self.bg_color + (255,))
                x = 0
                for img in images:
                    if align == "center":
                        y = (total_h - img.height) // 2
                    elif align == "end":
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
                    if align == "center":
                        x = (total_w - img.width) // 2
                    elif align == "end":
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

            # 根据输出格式添加压缩参数，避免文件变大
            save_kwargs = {}
            if ext in (".jpg", ".jpeg", ".webp"):
                save_kwargs['quality'] = 85
                save_kwargs['optimize'] = True
            elif ext == ".png":
                save_kwargs['compress_level'] = 6  # 0-9，6 是兼顾压缩率和速度的常用值
                save_kwargs['optimize'] = True
            elif ext == ".tiff":
                save_kwargs['compression'] = "tiff_deflate"

            canvas.save(self.output_path, **save_kwargs)
            msg = f"拼接完成，已保存到:\n{self.output_path}"
            if skipped > 0:
                msg += f"\n（已跳过 {skipped} 张损坏图片）"
            self.finished.emit(True, msg)
        except Exception as e:
            error_detail = f"{str(e)}\n\n详细错误:\n{traceback.format_exc()}"
            print(error_detail)  # 输出到控制台方便调试
            self.finished.emit(False, f"拼接失败: {str(e)}")


class ImageStitcher(ToolPlugin):
    """图片拼接工具"""

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
        layout.setSpacing(10)

        self.title_label = QLabel(self.icon + " " + self.name + "工具")
        self.title_label.setStyleSheet(
            f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']};"
        )
        layout.addWidget(self.title_label)

        self.desc_label = QLabel("将多张图片横向或纵向合并为一张，支持对齐方式和背景色设置（最大支持20张图片，因图片尺寸限制，大尺寸图片数量会更少）")
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # 文件列表（含创建时间列）
        file_card = Card(title="选择图片（列表顺序即拼接顺序）")
        self.file_panel = FileListPanel(
            columns=IMAGE_COLUMNS + [("创建时间", get_create_time)],
            file_filter="图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif *.gif)",
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear", "up", "down", "sort_name", "sort_time"]
        )
        file_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(file_card)

        # 拼接设置
        settings_card = Card(title="拼接设置")
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)  # 两列之间无间距
        grid.setVerticalSpacing(10)
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

        # 第0行：拼接方向占左半边，对齐方式占右半边，两半紧贴无间距
        # 左半边：拼接方向（标签+下拉框，下拉框拉伸占满左半边）
        dir_widget = QWidget()
        dir_layout = QHBoxLayout(dir_widget)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.setSpacing(SPACING_SMALL)  # 标签和控件之间8px
        dir_layout.addWidget(QLabel("拼接方向:"))
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["横向（左→右）", "纵向（上→下）"])
        self.dir_combo.setCurrentIndex(1)  # 默认竖向拼接
        self.dir_combo.setStyleSheet(combo_style)
        dir_layout.addWidget(self.dir_combo, 1)  # 拉伸占满左半边
        grid.addWidget(dir_widget, 0, 0)

        # 右半边：对齐方式（标签+下拉框，下拉框拉伸占满右半边）
        align_widget = QWidget()
        align_layout = QHBoxLayout(align_widget)
        align_layout.setContentsMargins(0, 0, 0, 0)
        align_layout.setSpacing(SPACING_SMALL)  # 标签和控件之间8px
        align_layout.addWidget(QLabel("对齐方式:"))
        self.align_combo = QComboBox()
        self.align_combo.addItems(["顶部/左侧对齐", "居中对齐", "底部/右侧对齐", "智能缩放"])
        self.align_combo.setCurrentIndex(3)  # 默认智能缩放
        self.align_combo.setStyleSheet(combo_style)
        align_layout.addWidget(self.align_combo, 1)  # 拉伸占满右半边
        grid.addWidget(align_widget, 0, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # 第1行：背景颜色（标签和控件之间无间距）
        bg_row = QHBoxLayout()
        bg_row.setSpacing(SPACING_SMALL)
        bg_row.addWidget(QLabel("背景颜色:"))
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
        grid.addLayout(bg_row, 1, 0, 1, 2)  # 跨两列

        # 第2行：输出文件（标签和控件之间无间距）
        out_row = QHBoxLayout()
        out_row.setSpacing(SPACING_SMALL)
        out_row.addWidget(QLabel("输出文件:"))
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
        grid.addLayout(out_row, 2, 0, 1, 2)  # 跨两列
        layout.addWidget(settings_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text="开始拼接"
        )
        self.action_panel.clicked.connect(self.start_stitch)
        layout.addWidget(self.action_panel)

        layout.addStretch()

        # 应用初始主题
        if Theme is not None:
            self.update_theme(Theme.DARK)
        return widget

    def browse_output(self):
        path = get_save_file_name(
            None, "保存拼接图片", "stitched.jpg",
            "JPEG (*.jpg);;PNG (*.png);;WebP (*.webp)"
        )
        if path:
            self.output_path.setText(path)

    def start_stitch(self):
        files = self.file_panel.get_files()
        if len(files) < 2:
            show_warning(None, "警告", "请至少添加 2 张图片！")
            return
        MAX_IMAGES = 20
        if len(files) > MAX_IMAGES:
            show_warning(None, "警告",
                          f"图片数量过多（当前 {len(files)} 张），请控制在 {MAX_IMAGES} 张以内，避免内存不足或处理失败。")
            return
        if not self.output_path.text():
            show_warning(None, "警告", "请选择输出文件路径！")
            return

        direction = "horizontal" if self.dir_combo.currentIndex() == 0 else "vertical"
        align_map = {0: "start", 1: "center", 2: "end", 3: "max_size"}
        align = align_map[self.align_combo.currentIndex()]
        bg = (self.bg_r.value(), self.bg_g.value(), self.bg_b.value())

        self.action_panel.start_task(0, status="正在拼接...")
        self.worker = ImageStitchWorker(
            files, self.output_path.text(), direction, align, bg
        )
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.finished.connect(self.stitch_finished)
        self.worker.start()

    def stitch_finished(self, success, message):
        self.action_panel.finish_task(message)
        if success:
            show_info(None, "完成", message)
        else:
            show_error(None, "错误", message)
