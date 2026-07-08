# -*- encoding: utf-8 -*-
"""
图片转PDF插件
将多张图片合并为一个PDF文件
"""
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QSlider, QLineEdit,
    QGridLayout, QCheckBox
)

from common.dialog_utils import get_save_file_name
from common.action_panel import ActionPanel
from common.utils import PIL_AVAILABLE, IMG2PDF_AVAILABLE, FITZ_AVAILABLE
from common.base_worker import BaseWorker
from PyQt6.QtCore import Qt

if PIL_AVAILABLE:
    from PIL import Image
if IMG2PDF_AVAILABLE:
    import img2pdf
if FITZ_AVAILABLE:
    import fitz

# 导入主程序中的基类和组件
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, Theme

from common.file_list_panel import FileListPanel
from common.utils import IMAGE_COLUMNS, get_create_time, get_combo_style, get_lineedit_style


class PDFWorker(BaseWorker):
    """PDF转换工作线程"""
    # 继承 BaseWorker 的标准信号：progress, status, finished

    def __init__(self, files, output, page_size, compress=True, quality=85):
        super().__init__()
        self.files = files
        self.output = output
        self.page_size = page_size
        self.compress = compress
        self.quality = quality

    BATCH_SIZE = 50  # 每批处理图片数，控制内存占用

    def run(self):
        temp_files = set()  # 使用集合避免重复文件名导致的清理问题
        try:
            # ========= 预检查：目标文件是否被占用 =========
            from common.utils import check_file_writable
            writable, err_msg = check_file_writable(self.output)
            if not writable:
                self.finished.emit(False, err_msg)
                return

            total = len(self.files)
            skipped = 0

            # ========= 阶段1：智能缩放需要先扫描最大宽度 =========
            max_width = None
            if self.page_size == "智能缩放":
                self.status.emit("正在扫描图片尺寸...")
                for f in self.files:
                    try:
                        with Image.open(f) as img:
                            if max_width is None or img.width > max_width:
                                max_width = img.width
                    except Exception as e:
                        print(f"Error in image_to_pdf: {e}")
                        skipped += 1
                if max_width is None:
                    self.finished.emit(False, "没有成功读取任何图片，请检查图片文件是否损坏。")
                    return

            # ========= 阶段2：分批处理图片 =========
            temp_pdfs = []
            processed_count = 0
            self.status.emit("正在处理图片...")

            for batch_start in range(0, total, self.BATCH_SIZE):
                batch_files = self.files[batch_start:min(batch_start + self.BATCH_SIZE, total)]
                self.status.emit(f"正在处理第 {batch_start // self.BATCH_SIZE + 1} 批图片...")

                # 2a. 读取并处理本批图片
                batch_imgs = []
                for f in batch_files:
                    try:
                        with Image.open(f) as src_img:
                            src_img.load()
                            if src_img.mode in ('RGBA', 'LA', 'P'):
                                img = src_img.convert('RGBA')
                            else:
                                img = src_img.convert('RGB')
                        # src_img 已关闭，img 为独立对象
                        batch_imgs.append(img)
                        processed_count += 1
                        self.progress.emit(processed_count)
                    except Exception as e:
                        print(f"Error in image_to_pdf: {e}")
                        skipped += 1
                        processed_count += 1
                        self.progress.emit(processed_count)
                        continue

                if not batch_imgs:
                    continue

                # 2b. 页面大小处理 + 转 RGB JPEG
                jpeg_quality = self.quality if self.compress else 95
                batch_jpeg_files = []

                for img in batch_imgs:
                    # 页面大小
                    if self.page_size == "智能缩放" and img.width != max_width:
                        ratio = max_width / img.width
                        resized = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
                        img.close()
                        img = resized
                    elif self.page_size == "A4":
                        resized = img.resize((595, 842), Image.Resampling.LANCZOS)
                        img.close()
                        img = resized
                    elif self.page_size == "A3":
                        resized = img.resize((842, 1191), Image.Resampling.LANCZOS)
                        img.close()
                        img = resized

                    # 确保 RGB 模式
                    if img.mode == 'RGBA':
                        bg = Image.new('RGB', img.size, (255, 255, 255))
                        bg.paste(img, mask=img.split()[3])
                        img.close()
                        img = bg
                    elif img.mode != 'RGB':
                        rgb = img.convert('RGB')
                        img.close()
                        img = rgb

                    # 去除 ICC 配置，避免 "broken data stream" 错误
                    if 'icc_profile' in img.info:
                        del img.info['icc_profile']

                    # 保存为临时 JPEG（使用时间戳+随机数避免文件名冲突）
                    import time
                    temp_dir = os.path.dirname(self.output) or '.'
                    if not os.path.exists(temp_dir):
                        os.makedirs(temp_dir, exist_ok=True)
                    tmp_jpg = os.path.join(temp_dir, f".temp_{int(time.time() * 1000)}_{id(img)}.jpg")
                    img.save(tmp_jpg, format='JPEG', quality=jpeg_quality, optimize=True)
                    img.close()  # 释放内存
                    batch_jpeg_files.append(tmp_jpg)
                    temp_files.add(tmp_jpg)  # 使用集合，避免重复

                batch_imgs.clear()

                # 2c. 本批生成临时 PDF
                temp_pdf = os.path.join(
                    os.path.dirname(self.output) or '.',
                    f".temp_{batch_start}.pdf"
                )
                temp_files.add(temp_pdf)

                if FITZ_AVAILABLE:
                    doc = fitz.open()
                    for jpg_file in batch_jpeg_files:
                        try:
                            fitz_img = fitz.open(jpg_file)
                            pdfbytes = fitz_img.convert_to_pdf()
                            img_pdf = fitz.open("pdf", pdfbytes)
                            doc.insert_pdf(img_pdf)
                            img_pdf.close()
                            fitz_img.close()
                        except Exception as e:
                            print(f"Error opening JPEG {jpg_file}: {e}")
                            continue
                    doc.save(temp_pdf, garbage=0, deflate=False)
                    doc.close()
                elif IMG2PDF_AVAILABLE:
                    try:
                        with open(temp_pdf, "wb") as f:
                            f.write(img2pdf.convert(batch_jpeg_files))
                    except Exception as e:
                        print(f"Error creating PDF with img2pdf: {e}")
                        # 清理本批 JPEG
                        for jpg_file in batch_jpeg_files:
                            temp_files.discard(jpg_file)
                        continue
                else:
                    pil_imgs = []
                    for j in batch_jpeg_files:
                        with Image.open(j) as src:
                            pil_imgs.append(src.convert('RGB'))
                    if pil_imgs:
                        pil_imgs[0].save(
                            temp_pdf, "PDF",
                            resolution=100.0,
                            save_all=True,
                            append_images=pil_imgs[1:]
                        )
                        # 释放内存
                        for img in pil_imgs:
                            img.close()

                # 验证临时PDF不为空
                if os.path.getsize(temp_pdf) == 0:
                    raise Exception(f"临时PDF生成失败（0字节）: {temp_pdf}")

                # 使用相对路径存储，但确保临时文件能被找到
                temp_pdfs.append(temp_pdf)

                # 2d. 清理本批 JPEG（PDF 已生成，JPEG 不再需要）
                for jpg_file in batch_jpeg_files:
                    try:
                        jpg_full = os.path.abspath(jpg_file)
                        if os.path.exists(jpg_full):
                            os.remove(jpg_full)
                        temp_files.discard(jpg_file)
                    except OSError as e:
                        print(f"Error removing JPEG {jpg_file}: {e}")

            if not temp_pdfs:
                self.finished.emit(False, "没有成功处理任何图片，请检查图片文件是否损坏。")
                return

            # ========= 阶段3：合并所有临时 PDF =========
            self.status.emit("正在合并PDF...")
            if len(temp_pdfs) == 1:
                import shutil
                # 使用完整路径移动文件（处理相对路径情况）
                temp_pdf_full = os.path.abspath(temp_pdfs[0])
                if os.path.exists(temp_pdf_full):
                    shutil.move(temp_pdf_full, self.output)
                temp_files.discard(temp_pdfs[0])
            else:
                if FITZ_AVAILABLE:
                    doc = fitz.open()
                    for tpdf in temp_pdfs:
                        try:
                            src = fitz.open(tpdf)
                            doc.insert_pdf(src)
                            src.close()
                        except Exception as e:
                            print(f"Error opening temp PDF {tpdf}: {e}")
                            continue
                    doc.save(self.output, garbage=0, deflate=False)
                    doc.close()
                else:
                    self.finished.emit(False, "多批合并需要 PyMuPDF，请安装: pip install PyMuPDF")
                    return

            # ========= 阶段4：清理所有临时 PDF =========
            self.status.emit("正在清理临时文件...")
            for tpdf in temp_pdfs:
                try:
                    # 使用完整路径删除临时文件
                    temp_pdf_full = os.path.abspath(tpdf)
                    if os.path.exists(temp_pdf_full):
                        os.remove(temp_pdf_full)
                    temp_files.discard(tpdf)
                except OSError as e:
                    print(f"Error removing temp PDF {tpdf}: {e}")

            msg = f"PDF已保存至:\n{self.output}"
            if skipped > 0:
                msg += f"\n（已跳过 {skipped} 张损坏图片）"
            self.progress.emit(processed_count + 1)  # 合并阶段完成
            # 验证输出PDF不为空
            if os.path.getsize(self.output) == 0:
                raise Exception(f"输出PDF为空（0字节）: {self.output}")
            self.finished.emit(True, msg)
        except Exception as e:
            print(f"Error in image_to_pdf: {e}")
            self.finished.emit(False, f"转换失败: {str(e)}")
        finally:
            # 异常或正常结束时，清理所有未删除的临时文件
            for tf in list(temp_files):
                try:
                    tf_full = os.path.abspath(tf)
                    if os.path.exists(tf_full):
                        os.remove(tf_full)
                except OSError as e:
                    print(f"Error in image_to_pdf (cleanup): {e}")


class ImageToPDF(ToolPlugin):
    """图片转PDF工具"""

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
            if hasattr(self, 'size_combo'):
                self.size_combo.setStyleSheet(get_combo_style(theme))
            if hasattr(self, 'output_path'):
                self.output_path.setStyleSheet(get_lineedit_style(theme))
            if hasattr(self, 'action_panel'):
                self.action_panel.update_theme(theme)
        except RuntimeError:
            pass  # C++ object already deleted

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        self.theme = Theme.DARK

        # 标题 + 描述
        self._setup_header(layout, theme=self.theme)

        # 图片列表
        list_card = Card(title="图片列表（列表顺序即PDF顺序）")
        self.file_panel = FileListPanel(
            columns=IMAGE_COLUMNS + [("创建时间", get_create_time)],
            file_filter="图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tiff)",
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear", "up", "down", "sort_name", "sort_time"]
        )
        list_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(list_card)

        # 设置
        settings_card = Card(title="PDF设置")
        settings_layout = QGridLayout()
        settings_card.content_layout.addLayout(settings_layout)

        settings_layout.addWidget(SelectableLabel("页面大小:"), 0, 0)
        self.size_combo = QComboBox()
        self.size_combo.addItems(["自动适应", "A4", "A3", "原图尺寸", "智能缩放"])
        self.size_combo.setCurrentIndex(4)  # 默认智能缩放
        self.size_combo.setStyleSheet(get_combo_style(self.theme))
        settings_layout.addWidget(self.size_combo, 0, 1)

        settings_layout.addWidget(SelectableLabel("启用压缩:"), 1, 0)
        self.compress_check = QCheckBox()
        self.compress_check.setChecked(True)
        settings_layout.addWidget(self.compress_check, 1, 1)

        settings_layout.addWidget(SelectableLabel("JPEG质量:"), 2, 0)
        quality_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(85)
        self.quality_label = SelectableLabel("85%")
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"{v}%")
        )
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        settings_layout.addLayout(quality_layout, 2, 1)

        settings_layout.addWidget(SelectableLabel("输出文件:"), 3, 0)
        path_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择保存位置...")
        browse_btn = AnimatedButton("浏览")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_output)
        path_layout.addWidget(self.output_path)
        path_layout.addWidget(browse_btn)
        settings_layout.addLayout(path_layout, 3, 1)

        layout.addWidget(settings_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text="开始转换"
        )
        self.action_panel.clicked.connect(self.start_conversion)
        layout.addWidget(self.action_panel)

        # 应用初始主题
        if Theme is not None:
            self.update_theme(Theme.DARK)
        return widget

    def browse_output(self):
        parent = self.widget if self.widget else None
        path = get_save_file_name(
            parent, "保存PDF", "", "PDF文件 (*.pdf)"
        )
        if path:
            if not path.endswith('.pdf'):
                path += '.pdf'
            self.output_path.setText(path)

    def start_conversion(self):
        files = self.file_panel.get_files()
        if not files:
            self._show_empty_warning("请先添加图片！")
            return

        output = self.output_path.text()
        if not output:
            parent = self.widget if self.widget else None
            output = get_save_file_name(
                parent, "保存PDF", "", "PDF文件 (*.pdf)"
            )
            if not output:
                return
            if not output.endswith('.pdf'):
                output += '.pdf'
            self.output_path.setText(output)

        if not (IMG2PDF_AVAILABLE or FITZ_AVAILABLE or PIL_AVAILABLE):
            parent = self.widget if self.widget else None
            from common.message_utils import show_error
            show_error(
                parent, "错误",
                "请先安装依赖: pip install img2pdf 或 pip install PyMuPDF 或 pip install Pillow"
            )
            return

        self.action_panel.start_task(len(files) + 1, status="")

        self.worker = PDFWorker(
            files,
            output,
            self.size_combo.currentText(),
            self.compress_check.isChecked(),
            self.quality_slider.value()
        )
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.start()

    def conversion_finished(self, success, message):
        self._finish_with_message(self.action_panel, success, message)
