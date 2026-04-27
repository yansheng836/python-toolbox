"""
PDF拆分工具插件
将PDF文件拆分为多张图片或单页PDF，支持设置拆分页数
"""
import os
import sys
import io

# 导入PyMuPDF用于PDF拆分
try:
    import fitz

    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

# 导入PIL用于图片处理
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 导入主程序中的ToolPlugin基类和相关组件
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin, Card, AnimatedButton, TITLE_STYLES, FONT_SIZE_12, FONT_SIZE_16, FONT_SIZE_20, FONT_WEIGHT_600, FONT_WEIGHT_700, FONT_WEIGHT_800
except ImportError:
    # 如果导入失败，定义简化的基类
    class ToolPlugin:
        name = "Base Tool"
        icon = "🔧"

        def create_ui(self):
            raise NotImplementedError("Subclasses must implement create_ui()")

    class Card:
        def __init__(self, parent=None, title=""):
            pass

    class AnimatedButton:
        def __init__(self, *args, **kwargs):
            pass

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
    QProgressBar, QMessageBox, QComboBox, QSpinBox, QLineEdit,
    QRadioButton, QButtonGroup, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class PDFSplitWorker(QThread):
    """PDF拆分工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, input_file, output_dir,
                 output_format="pdf", pages_per_split=1,
                 image_format="PNG", image_quality=95):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.output_format = output_format
        self.pages_per_split = pages_per_split
        self.image_format = image_format
        self.image_quality = image_quality

    def run(self):
        try:
            if not FITZ_AVAILABLE:
                self.finished.emit(False, "错误: 未安装PyMuPDF库，请运行: pip install PyMuPDF")
                return

            self.status.emit("正在打开PDF文件...")

            doc = fitz.open(self.input_file)

            total_pages = len(doc)
            self.status.emit(f"PDF共 {total_pages} 页，开始拆分...")

            os.makedirs(self.output_dir, exist_ok=True)

            base_name = os.path.splitext(os.path.basename(self.input_file))[0]
            output_count = 0

            if self.output_format == "pdf":
                for i in range(0, total_pages, self.pages_per_split):
                    end_page = min(i + self.pages_per_split, total_pages)

                    new_doc = fitz.open()
                    new_doc.insert_pdf(doc, from_page=i, to_page=end_page - 1)

                    output_file = os.path.join(
                        self.output_dir,
                        f"{base_name}_part{output_count + 1}_pages_{i + 1}-{end_page}.pdf"
                    )
                    new_doc.save(output_file)
                    new_doc.close()

                    output_count += 1
                    self.progress.emit(output_count)

                doc.close()
                self.finished.emit(True, f"成功拆分PDF为 {output_count} 个文件！\n保存位置: {self.output_dir}")

            else:
                if not PIL_AVAILABLE:
                    doc.close()
                    self.finished.emit(False, "错误: 输出图片需要Pillow库，请运行: pip install Pillow")
                    return

                for page_num in range(total_pages):
                    page = doc[page_num]

                    zoom = 2.0
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)

                    img_data = pix.tobytes("ppm")
                    img = Image.open(io.BytesIO(img_data))

                    output_file = os.path.join(
                        self.output_dir,
                        f"{base_name}_page{page_num + 1}.{self.image_format.lower()}"
                    )

                    if self.image_format.upper() in ("JPEG", "JPG"):
                        img.save(output_file, "JPEG", quality=self.image_quality, optimize=True)
                    elif self.image_format.upper() == "PNG":
                        img.save(output_file, "PNG", optimize=True)
                    elif self.image_format.upper() == "WEBP":
                        img.save(output_file, "WEBP", quality=self.image_quality)
                    else:
                        img.save(output_file)

                    output_count += 1
                    self.progress.emit(output_count)

                doc.close()
                self.finished.emit(True, f"成功转换 {output_count} 页为图片！\n保存位置: {self.output_dir}")

        except Exception as e:
            import traceback
            self.finished.emit(False, f"拆分失败: {str(e)}\n{traceback.format_exc()}")


class PDFSplitterWidget(QWidget):
    """PDF拆分工具主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_file = ""
        self.worker = None
        self.setup_ui()

        if not FITZ_AVAILABLE:
            self.status_label.setText("错误: 未安装PyMuPDF库，请运行: pip install PyMuPDF")
            self.split_btn.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        self.title_label = QLabel("📐 PDF拆分工具")
        self.title_label.setStyleSheet(f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700};")
        layout.addWidget(self.title_label)

        self.desc_label = QLabel("将PDF拆分为图片或单页PDF，支持设置拆分页数")
        self.desc_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.desc_label)

        file_card = Card(title="选择PDF文件")
        file_layout = file_card.content_layout

        self.file_display = QLineEdit()
        self.file_display.setPlaceholderText("拖拽PDF文件到此处，或点击按钮选择...")
        self.file_display.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                border: 2px dashed #334155;
                border-radius: 8px;
                padding: 8px;
                color: #94a3b8;
            }
            QLineEdit:hover {
                border-color: #475569;
            }
        """)
        self.file_display.setAcceptDrops(True)
        self.file_display.dragEnterEvent = self.drag_enter_event
        self.file_display.dropEvent = self.drop_event
        file_layout.addWidget(self.file_display)

        self.file_info_label = QLabel("未选择文件")
        self.file_info_label.setStyleSheet(f"color: #64748b; font-size: {FONT_SIZE_12};")
        file_layout.addWidget(self.file_info_label)

        btn_layout = QHBoxLayout()
        self.select_btn = AnimatedButton("选择PDF")
        self.select_btn.clicked.connect(self.select_file)
        self.clear_btn = AnimatedButton("清空")
        self.clear_btn.clicked.connect(self.clear_file)
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        layout.addWidget(file_card)

        settings_card = Card(title="拆分设置")
        settings_layout = QFormLayout()
        settings_layout.setSpacing(12)

        self.format_group = QButtonGroup(self)
        format_layout = QHBoxLayout()
        self.pdf_radio = QRadioButton("单页PDF")
        self.pdf_radio.setChecked(True)
        self.pdf_radio.setStyleSheet("color: #f1f5f9;")
        self.image_radio = QRadioButton("图片")
        self.image_radio.setStyleSheet("color: #f1f5f9;")
        self.format_group.addButton(self.pdf_radio)
        self.format_group.addButton(self.image_radio)
        format_layout.addWidget(self.pdf_radio)
        format_layout.addWidget(self.image_radio)
        format_layout.addStretch()
        self.pdf_radio.toggled.connect(self.on_format_changed)
        settings_layout.addRow("输出格式:", format_layout)

        self.image_format_combo = QComboBox()
        self.image_format_combo.addItems(["PNG", "JPEG", "WebP"])
        self.image_format_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        self.image_format_combo.setVisible(False)
        settings_layout.addRow("图片格式:", self.image_format_combo)

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 1000)
        self.pages_spin.setValue(1)
        self.pages_spin.setSuffix(" 页/文件")
        self.pages_spin.setStyleSheet("""
            QSpinBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
                color: #f1f5f9;
            }
        """)
        settings_layout.addRow("拆分页数:", self.pages_spin)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高质量 (95)", "标准 (85)", "较小文件 (75)", "最小文件 (50)"])
        self.quality_combo.setCurrentIndex(1)
        self.quality_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        self.quality_combo.setVisible(False)
        settings_layout.addRow("图片质量:", self.quality_combo)

        settings_card.content_layout.addLayout(settings_layout)
        layout.addWidget(settings_card)

        output_card = Card(title="输出设置")
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择输出目录...")
        self.output_path.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        self.browse_btn = AnimatedButton("浏览")
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        output_card.content_layout.addLayout(output_layout)
        layout.addWidget(output_card)

        action_card = Card()
        button_layout = QHBoxLayout()

        self.split_btn = AnimatedButton("开始拆分")
        self.split_btn.setMinimumHeight(48)
        self.split_btn.setStyleSheet(f"""
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
        self.split_btn.clicked.connect(self.start_split)
        self.split_btn.setEnabled(False)
        button_layout.addWidget(self.split_btn)

        self.cancel_btn = AnimatedButton("取消")
        self.cancel_btn.setMinimumHeight(48)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ef4444, stop:1 #dc2626);
                color: white; border: none; border-radius: 8px;
                font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f87171, stop:1 #ef4444); }}
            QPushButton:disabled {{ background: #334155; color: #64748b; }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_split)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)

        action_card.content_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0f172a;
                border-radius: 6px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 6px;
            }
        """)
        action_card.content_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("请选择PDF文件")
        self.status_label.setStyleSheet("color: #94a3b8;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_card.content_layout.addWidget(self.status_label)

        layout.addWidget(action_card)
        layout.addStretch()

    def on_format_changed(self):
        """输出格式改变时更新UI"""
        is_image = self.image_radio.isChecked()
        self.image_format_combo.setVisible(is_image)
        self.quality_combo.setVisible(is_image)
        self.pages_spin.setEnabled(self.pdf_radio.isChecked())
        if not self.pdf_radio.isChecked():
            self.pages_spin.setValue(1)

    def drag_enter_event(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith('.pdf'):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def drop_event(self, event):
        """拖放下事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith('.pdf'):
                        self.set_input_file(file_path)
                        break
            event.acceptProposedAction()
        else:
            event.ignore()

    def select_file(self):
        """选择PDF文件"""
        file, _ = QFileDialog.getOpenFileName(
            self,
            "选择PDF文件",
            "",
            "PDF文件 (*.pdf);;所有文件 (*.*)"
        )
        if file:
            self.set_input_file(file)

    def set_input_file(self, file_path):
        """设置输入文件"""
        self.input_file = file_path
        self.file_display.setText(file_path)

        try:
            if FITZ_AVAILABLE:
                doc = fitz.open(file_path)
                page_count = len(doc)
                doc.close()
                size_kb = os.path.getsize(file_path) / 1024
                self.file_info_label.setText(
                    f"文件: {os.path.basename(file_path)} | 页数: {page_count} | 大小: {size_kb:.1f} KB"
                )
                if not self.output_path.text():
                    self.output_path.setText(os.path.dirname(file_path))
                self.pages_spin.setMaximum(page_count)
            else:
                self.file_info_label.setText(f"文件: {os.path.basename(file_path)}")
        except Exception as e:
            self.file_info_label.setText(f"无法读取PDF信息: {e}")

        self.split_btn.setEnabled(bool(self.output_path.text()))

    def clear_file(self):
        """清空文件"""
        self.input_file = ""
        self.file_display.clear()
        self.file_info_label.setText("未选择文件")
        self.split_btn.setEnabled(False)

    def browse_output(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            os.path.dirname(self.input_file) if self.input_file else ""
        )
        if dir_path:
            self.output_path.setText(dir_path)
            if self.input_file:
                self.split_btn.setEnabled(True)

    def start_split(self):
        """开始拆分"""
        if not self.input_file:
            QMessageBox.warning(self, "警告", "请先选择PDF文件！")
            return

        if not self.output_path.text():
            QMessageBox.warning(self, "警告", "请选择输出目录！")
            return

        if not FITZ_AVAILABLE:
            QMessageBox.critical(self, "错误", "请先安装 PyMuPDF: pip install PyMuPDF")
            return

        if self.image_radio.isChecked() and not PIL_AVAILABLE:
            QMessageBox.critical(self, "错误", "输出图片需要 Pillow 库: pip install Pillow")
            return

        output_format = "pdf" if self.pdf_radio.isChecked() else "image"
        pages_per_split = self.pages_spin.value() if output_format == "pdf" else 1
        image_format = self.image_format_combo.currentText()
        quality_str = self.quality_combo.currentText()
        quality = int(quality_str.split("(")[1].split(")")[0])

        self.split_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)

        try:
            doc = fitz.open(self.input_file)
            total = len(doc)
            doc.close()
            if output_format == "pdf":
                total = (total + pages_per_split - 1) // pages_per_split
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(0)
        except Exception:
            self.progress_bar.setMaximum(100)

        self.status_label.setText("正在拆分...")

        self.worker = PDFSplitWorker(
            self.input_file,
            self.output_path.text(),
            output_format,
            pages_per_split,
            image_format,
            quality
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.split_finished)
        self.worker.start()

    def cancel_split(self):
        """取消拆分"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.status_label.setText("已取消")
            self.split_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.progress_bar.setVisible(False)

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)

    def update_status(self, message):
        """更新状态标签"""
        self.status_label.setText(message)

    def split_finished(self, success, message):
        """拆分完成回调"""
        self.progress_bar.setVisible(False)
        self.split_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if success:
            QMessageBox.information(self, "完成", message)
            self.status_label.setText("拆分完成")
        else:
            QMessageBox.critical(self, "错误", message)
            self.status_label.setText("拆分失败")


class PDFSplitter(ToolPlugin):
    """PDF拆分插件"""
    icon = "📐"
    name = "PDF拆分"

    def update_theme(self, theme):
        """更新主题"""
        if hasattr(self, 'widget') and hasattr(self.widget, 'title_label'):
            self.widget.title_label.setStyleSheet(
                f"font-size: {TITLE_STYLES['font_size']}; font-weight: {FONT_WEIGHT_700}; color: {theme['text']};"
            )

        if hasattr(self, 'widget') and hasattr(self.widget, 'desc_label'):
            self.widget.desc_label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: 13px;"
            )

    def create_ui(self):
        """创建UI"""
        self.widget = PDFSplitterWidget()
        return self.widget
