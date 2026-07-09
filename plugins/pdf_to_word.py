# -*- encoding: utf-8 -*-
"""
PDF转Word插件
将PDF文件转换为Word文档，保留文字格式、图片和表格
使用 PyMuPDF + python-docx 手动组合方案
"""
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QGridLayout, QCheckBox
)

from common.dialog_utils import get_existing_directory
from common.action_panel import ActionPanel
from common.utils import FITZ_AVAILABLE
from common.base_worker import BaseWorker

if FITZ_AVAILABLE:
    import fitz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import (
    ToolPlugin, Card, AnimatedButton, SelectableLabel,
    TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600, Theme,
)
from config import SPACING_SMALL

from common.file_list_panel import FileListPanel
from common.utils import PDF_COLUMNS, get_lineedit_style


class PDFToWordWorker(BaseWorker):
    """PDF转Word工作线程

    使用 PyMuPDF 提取 PDF 内容，用 python-docx 生成 Word 文档。
    """

    def __init__(self, files, output_dir, include_images=True, include_tables=True):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.include_images = include_images
        self.include_tables = include_tables

    def run(self):
        from docx import Document
        from docx.shared import Pt

        try:
            # ========= 预检查：输出目录是否可写 =========
            from common.utils import check_dir_writable
            out_dir = self.output_dir or (
                os.path.dirname(self.files[0]) if self.files else '.'
            )
            writable, err_msg = check_dir_writable(out_dir)
            if not writable:
                self.finished.emit(False, err_msg)
                return

            total = len(self.files)
            processed = 0

            for i, file_path in enumerate(self.files):
                basename = os.path.basename(file_path)
                self.status.emit(f"正在转换: {basename}")

                try:
                    pdf_doc = fitz.open(file_path)
                except Exception as e:
                    self.finished.emit(
                        False,
                        f"无法打开PDF文件: {basename}\n{str(e)}",
                    )
                    return

                page_count = len(pdf_doc)

                # 创建 Word 文档
                word_doc = Document()

                # 设置默认字体
                style = word_doc.styles['Normal']
                style.font.name = 'Microsoft YaHei'
                style.font.size = Pt(11)

                for page_idx in range(page_count):
                    page = pdf_doc[page_idx]

                    # 尝试提取文字（段落级别的纯文本）
                    raw_text = page.get_text("text").strip()

                    if raw_text:
                        # 有文字层 → 按空白行分割段落，保持可读性
                        paragraphs = raw_text.split("\n\n")
                        for para_text in paragraphs:
                            text = para_text.strip()
                            if text:
                                word_doc.add_paragraph(text)

                        # 提取有意义的图片（跳过小徽章）
                        if self.include_images:
                            blocks = page.get_text("dict").get("blocks", [])
                            for b in blocks:
                                if b["type"] == 1:
                                    self._add_image_block(word_doc, page, b)

                        # 提取表格
                        if self.include_tables:
                            tables = page.find_tables()
                            for table in tables:
                                self._add_table(word_doc, table)
                    else:
                        # 没有文字 → 渲染整页为图片
                        try:
                            self._add_full_page_image(word_doc, page)
                        except Exception as e:
                            print(f"Error adding full page image: {e}")

                    # 页间分页
                    if page_idx < page_count - 1:
                        word_doc.add_page_break()

                pdf_doc.close()

                # 生成输出文件名
                base_name = os.path.splitext(basename)[0]
                out_path = os.path.join(out_dir, f"{base_name}.docx")

                word_doc.save(out_path)
                processed += 1
                self.progress.emit(i + 1)

            if total == 1:
                self.status.emit("转换完成")
                self.finished.emit(
                    True,
                    f"转换成功！共 {page_count} 页（已保存到 {out_dir}）",
                )
            else:
                self.finished.emit(
                    True, f"成功转换 {processed} 个PDF文件！",
                )

        except Exception as e:
            print(f"Error in pdf_to_word: {e}")
            self.finished.emit(False, f"转换失败: {str(e)}")

    def _add_image_block(self, doc, page, block):
        """将 PyMuPDF 图片块嵌入 Word 文档（跳过小图标/徽章）"""
        try:
            # 跳过过小的图片（徽章、图标等），只保留截图等有意义的大图
            min_size = 100  # pts
            if block["width"] < min_size and block["height"] < min_size:
                return

            bbox = block["bbox"]
            clip = fitz.Rect(bbox)
            pix = page.get_pixmap(clip=clip)

            from io import BytesIO
            img_data = BytesIO(pix.tobytes("png"))

            from docx.shared import Inches
            page_width = doc.sections[0].page_width.inches
            max_width = page_width - 1.5
            doc.add_picture(img_data, width=Inches(max_width))
            img_data.close()
        except Exception as e:
            print(f"Error adding image: {e}")

    def _add_full_page_image(self, doc, page):
        """将整页渲染为图片嵌入 Word 文档（扫描件/无内容页面的后备方案）"""
        try:
            pix = page.get_pixmap(dpi=150)
            from io import BytesIO
            img_data = BytesIO(pix.tobytes("png"))
            from docx.shared import Inches
            page_width = doc.sections[0].page_width.inches
            max_width = page_width - 1.5
            doc.add_picture(img_data, width=Inches(max_width))
            img_data.close()
        except Exception as e:
            print(f"Error adding full page image: {e}")

    def _add_table(self, doc, table):
        """将 PyMuPDF 表格转为 Word 表格"""
        try:
            data = table.extract()
            if not data or not data[0]:
                return

            rows = len(data)
            cols = max(len(row) for row in data) if data else 0
            if cols == 0:
                return

            word_table = doc.add_table(rows=rows, cols=cols)
            word_table.style = 'Table Grid'

            for row_idx, row_data in enumerate(data):
                for col_idx in range(cols):
                    cell_text = str(row_data[col_idx] or "") if col_idx < len(row_data) else ""
                    word_table.cell(row_idx, col_idx).text = cell_text
        except Exception as e:
            print(f"Error adding table: {e}")


class PDFToWord(ToolPlugin):
    """PDF转Word工具"""
    name = "PDF转Word"
    description = "将PDF转换为Word文档，保留文字格式、图片和表格"
    icon = "📝"
    order = 110

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
                self.desc_label.setStyleSheet(
                    f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_14};"
                )
            if hasattr(self, 'file_panel'):
                self.file_panel.update_theme(theme)
            if hasattr(self, 'output_path'):
                self.output_path.setStyleSheet(get_lineedit_style(theme))
            if hasattr(self, 'chk_images'):
                self.chk_images.setStyleSheet(f"color: {theme['text']};")
            if hasattr(self, 'chk_tables'):
                self.chk_tables.setStyleSheet(f"color: {theme['text']};")
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
                self.status_label.setStyleSheet(
                    f"color: {theme['text_secondary']};"
                )
        except RuntimeError:
            pass  # C++ object already deleted

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        self.theme = Theme.DARK

        # 标题 + 描述
        self._setup_header(layout, theme=self.theme)

        # 文件选择区域
        file_card = Card(title="选择PDF文件")
        self.file_panel = FileListPanel(
            columns=PDF_COLUMNS,
            file_filter="PDF文件 (*.pdf)",
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear"],
        )
        file_card.content_layout.addWidget(self.file_panel)
        layout.addWidget(file_card)

        # 转换设置
        settings_card = Card(title="转换设置")
        settings_layout = QGridLayout()
        settings_layout.setSpacing(SPACING_SMALL)
        settings_card.content_layout.addLayout(settings_layout)

        # 输出目录
        settings_layout.addWidget(SelectableLabel("输出目录:"), 0, 0)
        out_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("默认保存到PDF所在目录")
        self.output_path.setStyleSheet(get_lineedit_style(self.theme))
        browse_btn = AnimatedButton("浏览")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_output)
        out_row.addWidget(self.output_path)
        out_row.addWidget(browse_btn)
        settings_layout.addLayout(out_row, 0, 1)

        # 选项：包含图片、包含表格
        options_row = QHBoxLayout()
        self.chk_images = QCheckBox("包含图片")
        self.chk_images.setChecked(True)
        self.chk_images.setStyleSheet(f"color: {self.theme['text']};")
        options_row.addWidget(self.chk_images)

        self.chk_tables = QCheckBox("包含表格")
        self.chk_tables.setChecked(True)
        self.chk_tables.setStyleSheet(f"color: {self.theme['text']};")
        options_row.addWidget(self.chk_tables)

        options_row.addStretch()
        settings_layout.addLayout(options_row, 1, 0, 1, 2)

        layout.addWidget(settings_card)

        # 操作面板
        self.action_panel = ActionPanel(
            button_text="开始转换",
        )
        self.action_panel.clicked.connect(self.start_convert)
        layout.addWidget(self.action_panel)

        # 应用初始主题
        self.update_theme(Theme.DARK)
        return widget

    def browse_output(self):
        """选择输出目录"""
        parent = self.widget if self.widget else None
        path = get_existing_directory(parent, "选择输出目录")
        if path:
            self.output_path.setText(path)

    def start_convert(self):
        """开始转换"""
        files = self.file_panel.get_files()
        if not files:
            self._show_empty_warning("请先添加PDF文件！")
            return

        if not FITZ_AVAILABLE:
            from common.message_utils import show_error
            parent = self.widget if self.widget else None
            show_error(parent, "缺少依赖", "PyMuPDF 未安装，无法转换PDF。\n请运行: pip install pymupdf")
            return

        try:
            import docx as _docx  # 验证 python-docx 是否可用
            _ = _docx
        except ImportError:
            from common.message_utils import show_error
            parent = self.widget if self.widget else None
            show_error(parent, "缺少依赖", "python-docx 未安装，无法生成Word文档。\n请运行: pip install python-docx")
            return

        self.action_panel.start_task(len(files), status="准备中...")

        self.worker = PDFToWordWorker(
            files,
            self.output_path.text() or None,
            include_images=self.chk_images.isChecked(),
            include_tables=self.chk_tables.isChecked(),
        )
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.finished.connect(self.convert_finished)
        self.worker.start()

    def convert_finished(self, success, message):
        """转换完成回调"""
        self._finish_with_message(self.action_panel, success, message)