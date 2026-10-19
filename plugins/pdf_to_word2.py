# -*- encoding: utf-8 -*-
"""
PDF转Word插件（pdf2docx方案）
使用 pdf2docx 库进行转换，作为对比方案
"""
import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QGridLayout,
)

from common.dialog_utils import get_existing_directory
from common.action_panel import ActionPanel
from common.base_worker import BaseWorker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import (
    ToolPlugin, Card, AnimatedButton, SelectableLabel,
    TITLE_STYLES, FONT_SIZE_14, Theme,
)
from config import SPACING_SMALL

from common.file_list_panel import FileListPanel
from common.utils import PDF_COLUMNS, get_lineedit_style


class PDFToWord2Worker(BaseWorker):
    """PDF转Word工作线程（pdf2docx方案）"""

    def __init__(self, files, output_dir):
        super().__init__()
        self.files = files
        self.output_dir = output_dir

    def run(self):
        try:
            from pdf2docx import Converter

            # 预检查：输出目录是否可写
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

                base_name = os.path.splitext(basename)[0]
                out_path = os.path.join(out_dir, f"{base_name}.docx")

                try:
                    cv = Converter(file_path)
                    cv.convert(out_path, start=0, end=None)
                    cv.close()
                except Exception as e:
                    self.finished.emit(
                        False,
                        f"转换失败: {basename}\n{str(e)}",
                    )
                    return

                processed += 1
                self.progress.emit(i + 1)

            if total == 1:
                self.status.emit("转换完成")
                self.finished.emit(
                    True,
                    f"转换成功！（已保存到 {out_dir}）",
                )
            else:
                self.finished.emit(
                    True, f"成功转换 {processed} 个PDF文件！",
                )

        except ImportError:
            self.finished.emit(
                False,
                "缺少 pdf2docx 库，请运行: pip install pdf2docx",
            )
        except Exception as e:
            print(f"Error in pdf_to_word2: {e}")
            self.finished.emit(False, f"转换失败: {str(e)}")


class PDFToWord2(ToolPlugin):
    """PDF转Word工具（pdf2docx方案）"""
    name = "PDF转Word(对比)"
    description = "使用 pdf2docx 库转换，对比效果用"
    icon = "📄"
    order = 111

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
            if hasattr(self, 'action_panel'):
                self.action_panel.update_theme(theme)
        except RuntimeError:
            pass

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

        # 输出目录设置
        settings_card = Card(title="输出设置")
        settings_layout = QGridLayout()
        settings_layout.setSpacing(SPACING_SMALL)
        settings_card.content_layout.addLayout(settings_layout)

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
        parent = self.widget if self.widget else None
        path = get_existing_directory(parent, "选择输出目录")
        if path:
            self.output_path.setText(path)

    def start_convert(self):
        files = self.file_panel.get_files()
        if not files:
            self._show_empty_warning("请先添加PDF文件！")
            return

        self.action_panel.start_task(len(files), status="准备中...")

        self.worker = PDFToWord2Worker(
            files,
            self.output_path.text() or None,
        )
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.finished.connect(self.convert_finished)
        self.worker.start()

    def convert_finished(self, success, message):
        self._finish_with_message(self.action_panel, success, message)