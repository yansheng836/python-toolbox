# -*- encoding: utf-8 -*-
"""
图片拼接插件
多图横向/纵向合并，支持自动分批（超尺寸时生成多个文件）
"""
import os
import sys
import traceback
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QComboBox, QSpinBox, QGridLayout, QLineEdit
)

from common.message_utils import show_info, show_error, show_warning
from common.dialog_utils import get_save_file_name
from common.action_panel import ActionPanel
from common.utils import PIL_AVAILABLE
from PyQt6.QtCore import Qt, QThread, pyqtSignal

if PIL_AVAILABLE:
    from PIL import Image

# 导入主程序中的基类和组件
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, \
    Theme
from config import SPACING_SMALL, SPACING_MEDIUM

from common.file_list_panel import FileListPanel
from common.utils import IMAGE_COLUMNS, get_create_time

MAX_DIMENSION = 60000  # Pillow 实际限制 65500，保守取值


class ImageStitchWorker(QThread):
    """图片拼接工作线程（支持自动分批）"""
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)  # 整体进度 0-100

    def __init__(self, files, output_path, direction, align, bg_color):
        super().__init__()
        self.files = files
        self.output_path = output_path
        self.direction = direction  # "horizontal" | "vertical"
        self.align = align  # "start" | "center" | "end" | "max_size"
        self.bg_color = bg_color  # (R, G, B)

    def _make_output_path(self, batch_index):
        """根据批次生成输出文件路径，第1批使用原路径，后续添加 _2, _3 等后缀"""
        if batch_index == 0:
            return self.output_path
        p = Path(self.output_path)
        return str(p.parent / f"{p.stem}_{batch_index + 1}{p.suffix}")

    def _split_into_batches(self, file_info, direction):
        """
        将图片分组为多个批次，每批拼接后在拼接方向上的尺寸不超过 MAX_DIMENSION。
        返回批次列表，每批是 [(path, width, height), ...]。
        单张图片尺寸超过 MAX_DIMENSION 时，保持原样（后续保存时会报错提示）。
        """
        batches = []
        current_batch = []
        current_dim = 0  # 横向时为累计宽度，纵向时为累计高度

        for f, w, h in file_info:
            img_dim = w if direction == "horizontal" else h

            # 单张图片就超过限制，单独成批（后续会报错）
            if img_dim > MAX_DIMENSION:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_dim = 0
                batches.append([(f, w, h)])
                continue

            if current_batch and current_dim + img_dim > MAX_DIMENSION:
                batches.append(current_batch)
                current_batch = [(f, w, h)]
                current_dim = img_dim
            else:
                current_batch.append((f, w, h))
                current_dim += img_dim

        if current_batch:
            batches.append(current_batch)

        return batches

    def _apply_max_size_align(self, batch_info, direction):
        """
        对批次内图片按 max_size 对齐方式计算缩放后的尺寸。
        横向拼接时统一高度，纵向拼接时统一宽度。
        """
        if direction == "vertical":
            max_width = max(w for _, w, _ in batch_info)
            result = []
            for f, w, h in batch_info:
                if w != max_width:
                    ratio = max_width / w
                    result.append((f, max_width, int(h * ratio)))
                else:
                    result.append((f, w, h))
            return result
        else:
            max_height = max(h for _, _, h in batch_info)
            result = []
            for f, w, h in batch_info:
                if h != max_height:
                    ratio = max_height / h
                    result.append((f, int(w * ratio), max_height))
                else:
                    result.append((f, w, h))
            return result

    def run(self):
        try:
            # ========= 第一遍：扫描尺寸 =========
            self.status.emit("正在扫描图片尺寸...")
            file_info = []  # (path, width, height)
            skipped = 0
            for f in self.files:
                try:
                    with Image.open(f) as img:
                        img.verify()
                        img = Image.open(f)
                        file_info.append((f, img.width, img.height))
                except Exception as e:
                    print(f"Error in image_stitcher: {e}")
                    skipped += 1
                    self.status.emit(f"跳过损坏图片: {os.path.basename(f)}")
                    continue

            if not file_info:
                self.finished.emit(False, "没有成功读取任何图片，请检查图片文件是否损坏。")
                return

            # ========= 分批：max_size 先全局缩放，再分批；其他模式直接分批 =========
            if self.align == "max_size":
                # 全局统一尺寸后分批
                if self.direction == "vertical":
                    max_w = max(w for _, w, _ in file_info)
                    scaled = []
                    for f, w, h in file_info:
                        if w != max_w:
                            ratio = max_w / w
                            nh = int(h * ratio)
                            if nh > MAX_DIMENSION:
                                self.finished.emit(False,
                                    f"智能缩放后图片高度（{nh}）超过 {MAX_DIMENSION}，"
                                    f"请先缩小图片尺寸或使用其他对齐方式。")
                                return
                            scaled.append((f, max_w, nh))
                        else:
                            if h > MAX_DIMENSION:
                                self.finished.emit(False,
                                    f"图片 {os.path.basename(f)} 的高度（{h}）"
                                    f"超过 {MAX_DIMENSION}，请先缩小该图片。")
                                return
                            scaled.append((f, w, h))
                else:
                    max_h = max(h for _, _, h in file_info)
                    scaled = []
                    for f, w, h in file_info:
                        if h != max_h:
                            ratio = max_h / h
                            nw = int(w * ratio)
                            if nw > MAX_DIMENSION:
                                self.finished.emit(False,
                                    f"智能缩放后图片宽度（{nw}）超过 {MAX_DIMENSION}，"
                                    f"请先缩小图片尺寸或使用其他对齐方式。")
                                return
                            scaled.append((f, nw, max_h))
                        else:
                            if w > MAX_DIMENSION:
                                self.finished.emit(False,
                                    f"图片 {os.path.basename(f)} 的宽度（{w}）"
                                    f"超过 {MAX_DIMENSION}，请先缩小该图片。")
                                return
                            scaled.append((f, w, h))
                batches = self._split_into_batches(scaled, self.direction)
            else:
                # 检查单张图片尺寸是否超过限制
                for f, w, h in file_info:
                    img_dim = w if self.direction == "horizontal" else h
                    if img_dim > MAX_DIMENSION:
                        dim_name = "宽度" if self.direction == "horizontal" else "高度"
                        self.finished.emit(False,
                            f"图片 {os.path.basename(f)} 的{dim_name}（{img_dim}）"
                            f"超过 {MAX_DIMENSION}，请先缩小该图片。")
                        return
                batches = self._split_into_batches(file_info, self.direction)

            num_batches = len(batches)

            # ========= 预检查：所有目标文件是否被占用 =========
            for bi in range(num_batches):
                out_path = self._make_output_path(bi)
                try:
                    with open(out_path, 'ab') as f:
                        pass
                except PermissionError:
                    self.finished.emit(
                        False,
                        f"目标文件被占用，无法写入：\n{out_path}\n\n"
                        f"请先关闭该文件，然后重试。"
                    )
                    return
                except Exception as e:
                    self.finished.emit(False, f"无法访问目标文件：{str(e)}")
                    return

            # ========= 逐批次拼接 =========
            saved_paths = []
            total_images = sum(len(b) for b in batches)

            for bi, batch_info in enumerate(batches):
                align = "start" if self.align == "max_size" else self.align

                # 计算本批次画布尺寸
                if self.direction == "horizontal":
                    batch_w = sum(w for _, w, _ in batch_info)
                    batch_h = max(h for _, _, h in batch_info)
                else:
                    batch_w = max(w for _, w, _ in batch_info)
                    batch_h = sum(h for _, _, h in batch_info)


                # 最终检查：画布尺寸不得超过 Pillow 限制
                if batch_w > MAX_DIMENSION or batch_h > MAX_DIMENSION:
                    self.finished.emit(
                        False,
                        f"批次 {bi+1} 画布尺寸（{batch_w}x{batch_h}）"
                        f"超过 {MAX_DIMENSION}，请减少图片数量或缩小图片尺寸。"
                    )
                    return

                canvas = Image.new("RGBA", (batch_w, batch_h), self.bg_color + (255,))

                if self.direction == "horizontal":
                    x = 0
                    for i, (f, expected_w, expected_h) in enumerate(batch_info):
                        global_idx = sum(len(b) for b in batches[:bi]) + i + 1
                        self.status.emit(
                            f"正在处理: {os.path.basename(f)} "
                            f"({global_idx}/{total_images})，批次 {bi+1}/{num_batches}"
                        )
                        with Image.open(f) as img:
                            img = img.convert("RGBA")
                            if img.width != expected_w or img.height != expected_h:
                                img = img.resize((expected_w, expected_h), Image.Resampling.LANCZOS)
                            if align == "center":
                                y = (batch_h - img.height) // 2
                            elif align == "end":
                                y = batch_h - img.height
                            else:
                                y = 0
                            canvas.paste(img, (x, y), img)
                            x += img.width
                        self.progress.emit(int(global_idx / total_images * 100))
                else:
                    y = 0
                    for i, (f, expected_w, expected_h) in enumerate(batch_info):
                        global_idx = sum(len(b) for b in batches[:bi]) + i + 1
                        self.status.emit(
                            f"正在处理: {os.path.basename(f)} "
                            f"({global_idx}/{total_images})，批次 {bi+1}/{num_batches}"
                        )
                        with Image.open(f) as img:
                            img = img.convert("RGBA")
                            if img.width != expected_w or img.height != expected_h:
                                img = img.resize((expected_w, expected_h), Image.Resampling.LANCZOS)
                            if align == "center":
                                x = (batch_w - img.width) // 2
                            elif align == "end":
                                x = batch_w - img.width
                            else:
                                x = 0
                            canvas.paste(img, (x, y), img)
                            y += img.height
                        self.progress.emit(int(global_idx / total_images * 100))

                # 输出格式不支持透明时转 RGB
                out_path = self._make_output_path(bi)
                ext = os.path.splitext(out_path)[1].lower()
                to_save = canvas
                if ext in (".jpg", ".jpeg", ".bmp"):
                    bg = Image.new("RGB", canvas.size, self.bg_color)
                    bg.paste(canvas, mask=canvas.split()[3])
                    to_save = bg

                save_kwargs = {}
                if ext in (".jpg", ".jpeg", ".webp"):
                    save_kwargs['quality'] = 85
                    save_kwargs['optimize'] = True
                elif ext == ".png":
                    save_kwargs['compress_level'] = 6
                    save_kwargs['optimize'] = True
                elif ext == ".tiff":
                    save_kwargs['compression'] = "tiff_deflate"

                # 最后防线：Pillow 硬限制 65500
                if to_save.width > 65500 or to_save.height > 65500:
                    self.finished.emit(
                        False,
                        f"图片尺寸（{to_save.width}x{to_save.height}）"
                        f"超过 Pillow 限制（65500），无法保存。"
                    )
                    return
                to_save.save(out_path, **save_kwargs)
                saved_paths.append(out_path)

            # ========= 完成 =========
            if num_batches == 1:
                msg = f"拼接完成，已保存到:\n{saved_paths[0]}"
            else:
                msg = f"拼接完成，已分为 {num_batches} 个文件保存:\n" + "\n".join(saved_paths)
            if skipped > 0:
                msg += f"\n（已跳过 {skipped} 张损坏图片）"
            self.finished.emit(True, msg)
        except Exception as e:
            error_detail = f"{str(e)}\n\n详细错误:\n{traceback.format_exc()}"
            print(error_detail)
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

        self.title_label = SelectableLabel(f"{self.icon} {self.name}")
        self.title_label.setStyleSheet(
            f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']};"
        )
        layout.addWidget(self.title_label)

        self.desc_label = SelectableLabel(self.description)
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
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(10)
        settings_card.content_layout.addLayout(grid)

        # 第0行：拼接方向占左半边，对齐方式占右半边
        dir_widget = QWidget()
        dir_layout = QHBoxLayout(dir_widget)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.setSpacing(SPACING_SMALL)
        dir_layout.addWidget(QLabel("拼接方向:"))
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["横向（左→右）", "纵向（上→下）"])
        self.dir_combo.setCurrentIndex(1)
        dir_layout.addWidget(self.dir_combo, 1)
        grid.addWidget(dir_widget, 0, 0)

        align_widget = QWidget()
        align_layout = QHBoxLayout(align_widget)
        align_layout.setContentsMargins(0, 0, 0, 0)
        align_layout.setSpacing(SPACING_SMALL)
        align_layout.addWidget(QLabel("对齐方式:"))
        self.align_combo = QComboBox()
        self.align_combo.addItems(["顶部/左侧对齐", "居中对齐", "底部/右侧对齐", "智能缩放"])
        self.align_combo.setCurrentIndex(3)
        align_layout.addWidget(self.align_combo, 1)
        grid.addWidget(align_widget, 0, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # 第1行：背景颜色
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
        for label, spin in (("R", self.bg_r), ("G", self.bg_g), ("B", self.bg_b)):
            bg_row.addWidget(QLabel(label))
            bg_row.addWidget(spin)
        bg_row.addStretch()
        grid.addLayout(bg_row, 1, 0, 1, 2)

        # 第2行：输出文件
        out_row = QHBoxLayout()
        out_row.setSpacing(SPACING_SMALL)
        out_row.addWidget(QLabel("输出文件:"))
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择保存路径...")
        out_row.addWidget(self.output_path)
        browse_btn = AnimatedButton("浏览")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_output)
        out_row.addWidget(browse_btn)
        grid.addLayout(out_row, 2, 0, 1, 2)
        layout.addWidget(settings_card)

        # 应用初始主题
        self.update_theme(Theme.DARK)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text="开始拼接"
        )
        self.action_panel.clicked.connect(self.start_stitch)
        layout.addWidget(self.action_panel)

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
        if not self.output_path.text():
            show_warning(None, "警告", "请选择输出文件路径！")
            return

        direction = "horizontal" if self.dir_combo.currentIndex() == 0 else "vertical"
        align_map = {0: "start", 1: "center", 2: "end", 3: "max_size"}
        align = align_map[self.align_combo.currentIndex()]
        bg = (self.bg_r.value(), self.bg_g.value(), self.bg_b.value())

        self.action_panel.start_task(100, status="正在拼接...")
        self.worker = ImageStitchWorker(
            files, self.output_path.text(), direction, align, bg
        )
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.finished.connect(self.stitch_finished)
        self.worker.start()

    def stitch_finished(self, success, message):
        self.action_panel.finish_task(message)
        if success:
            show_info(None, "完成", message)
        else:
            show_error(None, "错误", message)
