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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSpinBox, QGridLayout, QLineEdit
)

from common.i18n import t, bind_combo
from common.message_utils import show_warning
from common.dialog_utils import get_save_file_name
from common.action_panel import ActionPanel
from common.utils import PIL_AVAILABLE, load_oriented_image
from common.base_worker import BaseWorker

if PIL_AVAILABLE:
    from PIL import Image

# 导入主程序中的基类和组件
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, \
    Theme
from config import SPACING_SMALL

from common.file_list_panel import FileListPanel
from common.utils import IMAGE_COLUMNS, Column, get_create_time, get_combo_style, get_lineedit_style, get_spinbox_style

MAX_DIMENSION = 60000  # Pillow 实际限制 65500，保守取值


class ImageStitchWorker(BaseWorker):
    """图片拼接工作线程（支持自动分批）"""
    # 继承 BaseWorker 的标准信号：progress, status, finished
    # progress 和 status 在此直接可用  # 整体进度 0-100

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

    def _load_composited_image(self, file_path, expected_w, expected_h):
        """读取图片，应用 EXIF 方向、按需缩放并转换为 RGBA"""
        loaded = load_oriented_image(file_path)
        try:
            if loaded.width != expected_w or loaded.height != expected_h:
                resized = loaded.resize((expected_w, expected_h), Image.Resampling.LANCZOS)
                try:
                    return resized.convert("RGBA")
                finally:
                    resized.close()
            return loaded.convert("RGBA")
        finally:
            loaded.close()

    def _emit_processing_status(self, file_path, global_idx, total_images, batch_index, num_batches):
        """发出当前处理进度状态（横向/纵向共用）"""
        self.status.emit(t(
            "plugin.image_stitcher.msg.processing",
            name=os.path.basename(file_path),
            index=global_idx,
            total=total_images,
            batch=batch_index + 1,
            batch_total=num_batches,
        ))

    def run(self):
        try:
            # ========= 第一遍：扫描尺寸 =========
            self.status.emit(t("plugin.image_stitcher.msg.scanning_sizes"))
            file_info = []  # (path, width, height)
            skipped = 0
            for f in self.files:
                try:
                    img = load_oriented_image(f)
                    try:
                        file_info.append((f, img.width, img.height))
                    finally:
                        img.close()
                except Exception as e:
                    print(f"Error in image_stitcher: {e}")
                    skipped += 1
                    self.status.emit(t(
                        "plugin.image_stitcher.msg.skip_broken",
                        name=os.path.basename(f),
                    ))
                    continue

            if not file_info:
                self.finished.emit(False, t("plugin.image_stitcher.error.no_readable_images"))
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
                                self.finished.emit(False, t(
                                    "plugin.image_stitcher.error.scaled_too_large_height",
                                    height=nh,
                                    limit=MAX_DIMENSION,
                                ))
                                return
                            scaled.append((f, max_w, nh))
                        else:
                            if h > MAX_DIMENSION:
                                self.finished.emit(False, t(
                                    "plugin.image_stitcher.error.image_too_large_height",
                                    name=os.path.basename(f),
                                    height=h,
                                    limit=MAX_DIMENSION,
                                ))
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
                                self.finished.emit(False, t(
                                    "plugin.image_stitcher.error.scaled_too_large_width",
                                    width=nw,
                                    limit=MAX_DIMENSION,
                                ))
                                return
                            scaled.append((f, nw, max_h))
                        else:
                            if w > MAX_DIMENSION:
                                self.finished.emit(False, t(
                                    "plugin.image_stitcher.error.image_too_large_width",
                                    name=os.path.basename(f),
                                    width=w,
                                    limit=MAX_DIMENSION,
                                ))
                                return
                            scaled.append((f, w, h))
                batches = self._split_into_batches(scaled, self.direction)
            else:
                # 检查单张图片尺寸是否超过限制
                for f, w, h in file_info:
                    img_dim = w if self.direction == "horizontal" else h
                    if img_dim > MAX_DIMENSION:
                        params = {"name": os.path.basename(f), "limit": MAX_DIMENSION}
                        if self.direction == "horizontal":
                            key = "plugin.image_stitcher.error.image_too_large_width"
                            params["width"] = img_dim
                        else:
                            key = "plugin.image_stitcher.error.image_too_large_height"
                            params["height"] = img_dim
                        self.finished.emit(False, t(key, **params))
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
                    self.finished.emit(False, t(
                        "plugin.image_stitcher.error.output_locked",
                        path=out_path,
                    ))
                    return
                except Exception as e:
                    self.finished.emit(False, t(
                        "plugin.image_stitcher.error.output_access_failed",
                        error=str(e),
                    ))
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
                    self.finished.emit(False, t(
                        "plugin.image_stitcher.error.canvas_too_large",
                        index=bi + 1,
                        width=batch_w,
                        height=batch_h,
                        limit=MAX_DIMENSION,
                    ))
                    return

                canvas = Image.new("RGBA", (batch_w, batch_h), self.bg_color + (255,))

                if self.direction == "horizontal":
                    x = 0
                    for i, (f, expected_w, expected_h) in enumerate(batch_info):
                        global_idx = sum(len(b) for b in batches[:bi]) + i + 1
                        self._emit_processing_status(
                            f, global_idx, total_images, bi, num_batches
                        )
                        composited = self._load_composited_image(f, expected_w, expected_h)
                        try:
                            if align == "center":
                                y = (batch_h - composited.height) // 2
                            elif align == "end":
                                y = batch_h - composited.height
                            else:
                                y = 0
                            canvas.paste(composited, (x, y), composited)
                            x += composited.width
                        finally:
                            composited.close()
                        self.progress.emit(int(global_idx / total_images * 100))
                else:
                    y = 0
                    for i, (f, expected_w, expected_h) in enumerate(batch_info):
                        global_idx = sum(len(b) for b in batches[:bi]) + i + 1
                        self._emit_processing_status(
                            f, global_idx, total_images, bi, num_batches
                        )
                        composited = self._load_composited_image(f, expected_w, expected_h)
                        try:
                            if align == "center":
                                x = (batch_w - composited.width) // 2
                            elif align == "end":
                                x = batch_w - composited.width
                            else:
                                x = 0
                            canvas.paste(composited, (x, y), composited)
                            y += composited.height
                        finally:
                            composited.close()
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
                    self.finished.emit(False, t(
                        "plugin.image_stitcher.error.pillow_limit",
                        width=to_save.width,
                        height=to_save.height,
                    ))
                    return
                to_save.save(out_path, **save_kwargs)
                saved_paths.append(out_path)

            # ========= 完成 =========
            if num_batches == 1:
                msg = t("plugin.image_stitcher.msg.stitch_done_single", path=saved_paths[0])
            else:
                msg = t(
                    "plugin.image_stitcher.msg.stitch_done_multi",
                    count=num_batches,
                    paths="\n".join(saved_paths),
                )
            if skipped > 0:
                msg += t("plugin.image_stitcher.msg.skipped_note", count=skipped)
            self.finished.emit(True, msg)
        except Exception as e:
            error_detail = f"{str(e)}\n\n详细错误:\n{traceback.format_exc()}"
            print(error_detail)
            self.finished.emit(False, t("plugin.image_stitcher.error.stitch_failed", error=str(e)))


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
            combo_style = get_combo_style(theme)
            if hasattr(self, 'dir_combo'):
                self.dir_combo.setStyleSheet(combo_style)
            if hasattr(self, 'align_combo'):
                self.align_combo.setStyleSheet(combo_style)
            spin_style = get_spinbox_style(theme)
            for spin in [getattr(self, 'bg_r', None), getattr(self, 'bg_g', None), getattr(self, 'bg_b', None)]:
                if spin:
                    spin.setStyleSheet(spin_style)
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

    @staticmethod
    def _build_columns():
        """按当前语言重建列定义（IMAGE_COLUMNS 是共享常量，其标签不随语言切换）"""
        columns = [
            Column(col.id, t(f"column.{col.id}"), col.func)
            for col in IMAGE_COLUMNS
        ]
        columns.append(Column("created", t("column.created"), get_create_time))
        return columns

    def _retranslate_columns(self):
        """重建文件列表表头文本（表头标签在表格创建时固定）"""
        columns = self._build_columns()
        self.file_panel.columns = columns
        self.file_panel.table.setHorizontalHeaderLabels([col.label for col in columns])

    def retranslate_ui(self):
        """语言切换后重放全部用户可见文本"""
        self.title_label.setText(f"{self.icon} {t('plugin.image_stitcher.name')}")
        self.desc_label.setText(t("plugin.image_stitcher.description"))
        self.file_card.title_label.setText(t("plugin.image_stitcher.card.select_images"))
        self.settings_card.title_label.setText(t("plugin.image_stitcher.card.settings"))
        self.direction_label.setText(t("plugin.image_stitcher.label.direction"))
        self.align_label.setText(t("plugin.image_stitcher.label.align"))
        self.bg_color_label.setText(t("plugin.image_stitcher.label.bg_color"))
        self.output_file_label.setText(t("plugin.image_stitcher.label.output_file"))
        self.output_path.setPlaceholderText(t("plugin.image_stitcher.placeholder.output_path"))
        self.browse_btn.setText(t("plugin.image_stitcher.button.browse"))
        self.action_panel.btn.setText(t("plugin.image_stitcher.button.start"))
        self.file_panel.file_filter = t("plugin.image_stitcher.filter.images")
        self.file_panel.retranslate_ui()
        self._retranslate_columns()
        # 组合框由 bind_combo 自动重放，无需处理

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        self.theme = Theme.DARK

        # 标题 + 描述
        self._setup_header(
            layout,
            title=f"{self.icon} {t('plugin.image_stitcher.name')}",
            desc=t("plugin.image_stitcher.description"),
            theme=self.theme,
        )

        # 文件列表（含创建时间列）
        self.file_card = Card(title=t("plugin.image_stitcher.card.select_images"))
        self.file_panel = FileListPanel(
            columns=self._build_columns(),
            file_filter=t("plugin.image_stitcher.filter.images"),
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear", "up", "down", "sort_name", "sort_time"]
        )
        self.file_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(self.file_card)

        # 拼接设置
        self.settings_card = Card(title=t("plugin.image_stitcher.card.settings"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(10)
        self.settings_card.content_layout.addLayout(grid)

        # 第0行：拼接方向占左半边，对齐方式占右半边
        dir_widget = QWidget()
        dir_layout = QHBoxLayout(dir_widget)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.setSpacing(SPACING_SMALL)
        self.direction_label = SelectableLabel(t("plugin.image_stitcher.label.direction"))
        dir_layout.addWidget(self.direction_label)
        self.dir_combo = QComboBox()
        bind_combo(self.dir_combo, [
            ("plugin.image_stitcher.combo.horizontal", "horizontal"),
            ("plugin.image_stitcher.combo.vertical", "vertical"),
        ])
        self.dir_combo.setCurrentIndex(self.dir_combo.findData("vertical"))
        dir_layout.addWidget(self.dir_combo, 1)
        grid.addWidget(dir_widget, 0, 0)

        align_widget = QWidget()
        align_layout = QHBoxLayout(align_widget)
        align_layout.setContentsMargins(0, 0, 0, 0)
        align_layout.setSpacing(SPACING_SMALL)
        self.align_label = SelectableLabel(t("plugin.image_stitcher.label.align"))
        align_layout.addWidget(self.align_label)
        self.align_combo = QComboBox()
        bind_combo(self.align_combo, [
            ("plugin.image_stitcher.combo.start", "start"),
            ("plugin.image_stitcher.combo.center", "center"),
            ("plugin.image_stitcher.combo.end", "end"),
            ("plugin.image_stitcher.combo.max_size", "max_size"),
        ])
        self.align_combo.setCurrentIndex(self.align_combo.findData("max_size"))
        align_layout.addWidget(self.align_combo, 1)
        grid.addWidget(align_widget, 0, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # 第1行：背景颜色
        bg_row = QHBoxLayout()
        bg_row.setSpacing(SPACING_SMALL)
        self.bg_color_label = SelectableLabel(t("plugin.image_stitcher.label.bg_color"))
        bg_row.addWidget(self.bg_color_label)
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
        self.output_file_label = SelectableLabel(t("plugin.image_stitcher.label.output_file"))
        out_row.addWidget(self.output_file_label)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText(t("plugin.image_stitcher.placeholder.output_path"))
        out_row.addWidget(self.output_path)
        self.browse_btn = AnimatedButton(t("plugin.image_stitcher.button.browse"))
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_output)
        out_row.addWidget(self.browse_btn)
        grid.addLayout(out_row, 2, 0, 1, 2)
        layout.addWidget(self.settings_card)

        # 应用初始主题
        self.update_theme(Theme.DARK)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text=t("plugin.image_stitcher.button.start")
        )
        self.action_panel.clicked.connect(self.start_stitch)
        layout.addWidget(self.action_panel)

        return widget

    def browse_output(self):
        path = get_save_file_name(
            None, t("plugin.image_stitcher.dialog.save_image"), "stitched.jpg",
            t("plugin.image_stitcher.filter.save_image")
        )
        if path:
            self.output_path.setText(path)

    def start_stitch(self):
        files = self.file_panel.get_files()
        if len(files) < 2:
            show_warning(
                None,
                t("plugin.image_stitcher.dialog.warning_title"),
                t("plugin.image_stitcher.warning.min_images"),
            )
            return
        if not self.output_path.text():
            show_warning(
                None,
                t("plugin.image_stitcher.dialog.warning_title"),
                t("plugin.image_stitcher.warning.no_output_path"),
            )
            return

        direction = self.dir_combo.currentData()
        align = self.align_combo.currentData()
        bg = (self.bg_r.value(), self.bg_g.value(), self.bg_b.value())

        self.action_panel.start_task(100, status=t("plugin.image_stitcher.msg.stitching"))
        self.worker = ImageStitchWorker(
            files, self.output_path.text(), direction, align, bg
        )
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.finished.connect(self.stitch_finished)
        self.worker.start()

    def stitch_finished(self, success, message):
        self._finish_with_message(self.action_panel, success, message)
