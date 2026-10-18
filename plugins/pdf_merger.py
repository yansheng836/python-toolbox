# -*- encoding: utf-8 -*-
"""
PDF合并工具插件
将多个PDF文件合并为一个PDF文件，支持拖拽和顺序调整
"""
import os
import sys

from common.utils import FITZ_AVAILABLE
from common.i18n import t

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, FONT_WEIGHT_700, Theme

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QLineEdit
)
from common.message_utils import show_info, show_error, show_warning
from common.file_list_panel import FileListPanel
from common.action_panel import ActionPanel
from common.utils import PDF_COLUMNS, get_lineedit_style
from common.base_worker import BaseWorker

if FITZ_AVAILABLE:
    import pymupdf as fitz


class PDFMergeWorker(BaseWorker):
    """PDF合并工作线程"""
    # 继承 BaseWorker 的标准信号：progress, status, finished

    def __init__(self, files, output):
        super().__init__()
        self.files = files
        self.output = output

    def run(self):
        try:
            # ========= 预检查：目标文件是否被占用 =========
            from common.utils import check_file_writable
            if self.output:
                writable, err_msg = check_file_writable(self.output)
                if not writable:
                    self.finished.emit(False, err_msg)
                    return

            if not FITZ_AVAILABLE:
                self.finished.emit(
                    False, t("plugin.pdf_merger.error.pymupdf_not_installed"))
                return

            self.status.emit(t("plugin.pdf_merger.msg.status_merging"))
            merged = fitz.open()

            for i, file_path in enumerate(self.files):
                self.status.emit(t(
                    "plugin.pdf_merger.msg.processing",
                    name=os.path.basename(file_path)))
                doc = fitz.open(file_path)
                merged.insert_pdf(doc)
                doc.close()
                self.progress.emit(i + 1)

            merged.save(self.output)
            merged.close()
            self.finished.emit(True, t(
                "plugin.pdf_merger.msg.merge_done", count=len(self.files)))
        except Exception as e:
            self.finished.emit(False, t(
                "plugin.pdf_merger.error.merge_failed", error=str(e)))

class PDFMergerWidget(QWidget):
    """PDF合并工具主界面"""

    def __init__(self, parent=None, icon="", name="", description="", theme=None):
        super().__init__(parent)
        self.icon = icon
        self.name = name
        self.description = description
        self.theme = theme or Theme.DARK
        self.worker = None
        self.setup_ui()

        # 检查PyMuPDF是否可用
        if not FITZ_AVAILABLE:
            self.action_panel.status_label.setText(t(
                "plugin.pdf_merger.error.pymupdf_missing_status"))
            self.action_panel.btn.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标题（使用 PLUGIN_MODULES 配置中的 icon + 名称词典）
        self.title_label = SelectableLabel(
            f"{self.icon} {t('plugin.pdf_merger.name')}")
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # 说明
        self.desc_label = SelectableLabel(t("plugin.pdf_merger.description"))
        self.desc_label.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: {FONT_SIZE_14};")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # PDF文件列表区域
        self.file_card = Card(title=t("plugin.pdf_merger.card.file_list"))
        file_layout = self.file_card.content_layout

        self.file_panel = FileListPanel(
            columns=PDF_COLUMNS,
            file_filter=t("plugin.pdf_merger.filter.add_files"),
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear", "up", "down", "sort_name", "sort_time"]
        )
        file_layout.addWidget(self.file_panel)
        layout.addWidget(self.file_card)

        # 输出设置
        self.output_card = Card(title=t("plugin.pdf_merger.card.output"))
        output_layout = QHBoxLayout()
        self.output_file_label = SelectableLabel(
            t("plugin.pdf_merger.label.output_file"))
        output_layout.addWidget(self.output_file_label)
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText(
            t("plugin.pdf_merger.placeholder.output_path"))
        self.output_path.setStyleSheet(get_lineedit_style(self.theme))
        self.browse_btn = AnimatedButton(t("plugin.pdf_merger.button.browse"))
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        self.output_card.content_layout.addLayout(output_layout)
        layout.addWidget(self.output_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text=t("plugin.pdf_merger.button.start_merge")
        )
        self.action_panel.clicked.connect(self.start_merge)
        layout.addWidget(self.action_panel)

        # 应用初始主题
        if Theme is not None:
            self.apply_theme(Theme.DARK)

    def browse_output(self):
        """选择输出文件路径"""
        # 默认使用第一个输入文件的目录
        files = self.file_panel.get_files()
        default_name = "merged.pdf"
        if files:
            default_dir = os.path.dirname(files[0])
            default_path = os.path.join(default_dir, default_name)
        else:
            default_path = default_name

        path, _ = QFileDialog.getSaveFileName(
            self,
            t("plugin.pdf_merger.dialog.save_pdf"),
            default_path,
            t("plugin.pdf_merger.filter.save_pdf")
        )

        if path:
            if not path.endswith('.pdf'):
                path += '.pdf'
            self.output_path.setText(path)

    def start_merge(self):
        """开始合并PDF"""
        files = self.file_panel.get_files()
        if len(files) < 2:
            show_warning(
                self,
                t("plugin.pdf_merger.dialog.warning_title"),
                t("plugin.pdf_merger.warning.min_files"))
            return

        output = self.output_path.text()
        if not output:
            self.browse_output()
            output = self.output_path.text()
            if not output:
                return

        if not FITZ_AVAILABLE:
            show_error(
                self,
                t("plugin.pdf_merger.dialog.error_title"),
                t("plugin.pdf_merger.error.install_pymupdf"))
            return

        # 开始任务
        self.action_panel.start_task(
            len(files), status=t("plugin.pdf_merger.msg.starting"))

        # 创建工作线程
        self.worker = PDFMergeWorker(files, output)
        self.worker.progress.connect(self.action_panel.update_progress)
        self.worker.status.connect(self.action_panel.update_status)
        self.worker.finished.connect(self.merge_finished)
        self.worker.start()

    def merge_finished(self, success, message):
        """合并完成回调"""
        self.action_panel.finish_task(message)

        if success:
            show_info(self, t("plugin.pdf_merger.dialog.done_title"), message)
        else:
            show_error(self, t("plugin.pdf_merger.dialog.error_title"), message)

    def retranslate_ui(self):
        """语言切换后重放全部用户可见文本"""
        self.title_label.setText(f"{self.icon} {t('plugin.pdf_merger.name')}")
        self.desc_label.setText(t("plugin.pdf_merger.description"))
        self.file_card.title_label.setText(
            t("plugin.pdf_merger.card.file_list"))
        # 文件选择过滤器在下次打开对话框时生效（扩展名解析结果不变）
        self.file_panel.file_filter = t("plugin.pdf_merger.filter.add_files")
        self.file_panel.retranslate_ui()
        self.output_card.title_label.setText(t("plugin.pdf_merger.card.output"))
        self.output_file_label.setText(t("plugin.pdf_merger.label.output_file"))
        self.output_path.setPlaceholderText(
            t("plugin.pdf_merger.placeholder.output_path"))
        self.browse_btn.setText(t("plugin.pdf_merger.button.browse"))
        self.action_panel.btn.setText(
            t("plugin.pdf_merger.button.start_merge"))
        if not FITZ_AVAILABLE:
            self.action_panel.status_label.setText(t(
                "plugin.pdf_merger.error.pymupdf_missing_status"))

    def apply_theme(self, theme):
        """应用主题到所有组件"""
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_14};")
        if hasattr(self, 'file_panel'):
            self.file_panel.update_theme(theme)
        if hasattr(self, 'output_path'):
            self.output_path.setStyleSheet(get_lineedit_style(theme))
        if hasattr(self, 'action_panel'):
            self.action_panel.update_theme(theme)


class PDFMerger(ToolPlugin):
    """PDF合并插件"""

    def create_ui(self):
        """创建UI"""
        self.widget = PDFMergerWidget(icon=self.icon, name=self.name, description=self.description, theme=Theme.DARK)
        # 将 Widget 的标签属性复制到插件实例，统一访问入口
        self.title_label = self.widget.title_label
        self.desc_label = self.widget.desc_label
        return self.widget

    def retranslate_ui(self):
        """语言切换后重放全部用户可见文本"""
        if getattr(self, 'widget', None) is not None:
            self.widget.retranslate_ui()

    def update_theme(self, theme):
        """更新主题"""
        if hasattr(self, 'widget') and hasattr(self.widget, 'apply_theme'):
            self.widget.apply_theme(theme)
