# -*- encoding: utf-8 -*-
"""
PDF合并工具插件
将多个PDF文件合并为一个PDF文件，支持拖拽和顺序调整
"""
import os
import sys

from common.utils import FITZ_AVAILABLE

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, TITLE_STYLES, FONT_SIZE_14, FONT_WEIGHT_700, Theme
from config import SPACING_SMALL

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QLineEdit
)
from PyQt6.QtCore import QThread, pyqtSignal

from common.message_utils import show_info, show_error, show_warning
from common.file_list_panel import FileListPanel
from common.action_panel import ActionPanel
from common.utils import PDF_COLUMNS

if FITZ_AVAILABLE:
    import fitz


class PDFMergeWorker(QThread):
    """PDF合并工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output):
        super().__init__()
        self.files = files
        self.output = output

    def run(self):
        try:
            # ========= 预检查：目标文件是否被占用 =========
            if self.output:
                try:
                    with open(self.output, 'ab') as f:
                        pass
                except PermissionError as e:
                    self.finished.emit(
                        False,
                        f"目标文件被占用，无法写入：\n{self.output}\n\n"
                        f"请先关闭该文件（如在 WPS、Adobe Reader 等软件中打开），然后重试。"
                    )
                    return
                except Exception as e:
                    self.finished.emit(False, f"无法访问目标文件：{str(e)}")
                    return

            if not FITZ_AVAILABLE:
                self.finished.emit(False, "PyMuPDF 未安装")
                return

            self.status.emit("正在合并PDF...")
            merged = fitz.open()

            for i, file_path in enumerate(self.files):
                self.status.emit(f"正在处理: {os.path.basename(file_path)}")
                doc = fitz.open(file_path)
                merged.insert_pdf(doc)
                doc.close()
                self.progress.emit(i + 1)

            merged.save(self.output)
            merged.close()
            self.finished.emit(True, f"合并完成，共 {len(self.files)} 个文件")
        except Exception as e:
            self.finished.emit(False, f"合并失败: {str(e)}")

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
            self.status_label.setText("错误: 未安装PyMuPDF库，请运行: pip install PyMuPDF")
            self.merge_btn.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标题（使用 PLUGIN_MODULES 配置中的 icon + name）
        self.title_label = SelectableLabel(f"{self.icon} {self.name}")
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        layout.addWidget(self.title_label)

        # 说明（使用 PLUGIN_MODULES 配置中的 description）
        self.desc_label = SelectableLabel(self.description)
        self.desc_label.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # PDF文件列表区域
        file_card = Card(title="PDF文件列表（顺序即为合并顺序）")
        file_layout = file_card.content_layout

        self.file_panel = FileListPanel(
            columns=PDF_COLUMNS,
            file_filter="PDF文件 (*.pdf);;所有文件 (*.*)",
            button_class=AnimatedButton,
            show_buttons=["add", "remove", "clear", "up", "down", "sort_name", "sort_time"]
        )
        file_layout.addWidget(self.file_panel)
        layout.addWidget(file_card)

        # 输出设置
        output_card = Card(title="输出设置")
        output_layout = QHBoxLayout()
        output_layout.addWidget(SelectableLabel("输出文件:"))
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择输出文件路径...")
        self.output_path.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme['bg']};
                border: 1px solid {self.theme['surface']};
                border-radius: 6px;
                padding: 6px;
                color: {self.theme['text']};
            }}
        """)
        browse_btn = AnimatedButton("浏览")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_btn)
        output_card.content_layout.addLayout(output_layout)
        layout.addWidget(output_card)

        # 操作面板（按钮 + 进度条 + 状态标签）
        self.action_panel = ActionPanel(
            button_text="开始合并"
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
            "保存合并后的PDF",
            default_path,
            "PDF文件 (*.pdf)"
        )

        if path:
            if not path.endswith('.pdf'):
                path += '.pdf'
            self.output_path.setText(path)

    def start_merge(self):
        """开始合并PDF"""
        files = self.file_panel.get_files()
        if len(files) < 2:
            show_warning(self, "警告", "请至少添加 2 个PDF文件！")
            return

        output = self.output_path.text()
        if not output:
            self.browse_output()
            output = self.output_path.text()
            if not output:
                return

        if not FITZ_AVAILABLE:
            show_error(self, "错误", "请先安装 PyMuPDF: pip install PyMuPDF")
            return

        # 开始任务
        self.action_panel.start_task(len(files), status="正在合并...")

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
            show_info(self, "完成", message)
        else:
            show_error(self, "错误", message)

    def apply_theme(self, theme):
        """应用主题到所有组件"""
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_14};")
        if hasattr(self, 'file_panel'):
            self.file_panel.update_theme(theme)
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

    def update_theme(self, theme):
        """更新主题"""
        if hasattr(self, 'widget') and hasattr(self.widget, 'apply_theme'):
            self.widget.apply_theme(theme)
