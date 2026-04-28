"""
图片转PDF插件
将多张图片合并为一个PDF文件
"""
import os
import sys
import io

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QComboBox, QSlider, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QGridLayout, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import img2pdf
    IMG2PDF_AVAILABLE = True
except ImportError:
    IMG2PDF_AVAILABLE = False

try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

# 导入主程序中的基类和组件
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from toolbox import ToolPlugin, Card, AnimatedButton, TITLE_STYLES, FONT_SIZE_14, FONT_SIZE_16, FONT_WEIGHT_600
except ImportError:
    ToolPlugin = object
    Card = None
    AnimatedButton = None


class PDFWorker(QThread):
    """PDF转换工作线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output, page_size, compress=True, quality=85):
        super().__init__()
        self.files = files
        self.output = output
        self.page_size = page_size
        self.compress = compress
        self.quality = quality

    @staticmethod
    def compress_image(image_path, quality):
        """压缩图片到内存，返回 BytesIO 对象"""
        img = Image.open(image_path)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
                img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        buf.seek(0)
        return buf

    def run(self):
        try:
            if IMG2PDF_AVAILABLE:
                if self.compress:
                    compressed_images = []
                    for i, img_path in enumerate(self.files):
                        buf = self.compress_image(img_path, self.quality)
                        compressed_images.append(buf)
                        self.progress.emit(i + 1)

                    with open(self.output, "wb") as f:
                        f.write(img2pdf.convert(compressed_images))
                else:
                    for i, _ in enumerate(self.files):
                        self.progress.emit(i + 1)
                    with open(self.output, "wb") as f:
                        f.write(img2pdf.convert(self.files))
            elif FITZ_AVAILABLE:
                doc = fitz.open()
                for i, img_path in enumerate(self.files):
                    if self.compress:
                        buf = self.compress_image(img_path, self.quality)
                        img = fitz.open("jpg", buf.getvalue())
                    else:
                        img = fitz.open(img_path)

                    rect = img[0].rect
                    pdfbytes = img.convert_to_pdf()
                    img_pdf = fitz.open("pdf", pdfbytes)
                    doc.insert_pdf(img_pdf)
                    self.progress.emit(i + 1)
                doc.save(self.output)
                doc.close()
            else:
                images = []
                for i, f in enumerate(self.files):
                    if self.compress:
                        buf = self.compress_image(f, self.quality)
                        img = Image.open(buf)
                    else:
                        img = Image.open(f)
                        if img.mode in ('RGBA', 'LA', 'P'):
                            img = img.convert('RGB')
                    images.append(img)
                    self.progress.emit(i + 1)

                if images:
                    images[0].save(
                        self.output, "PDF",
                        resolution=100.0,
                        save_all=True,
                        append_images=images[1:]
                    )

            self.finished.emit(True, f"PDF已保存至:\n{self.output}")
        except Exception as e:
            self.finished.emit(False, f"转换失败: {str(e)}")


class ImageToPDF(ToolPlugin):
    """图片转PDF工具"""
    name = "图片转PDF"
    description = "将多张图片合并为一个PDF文件"
    icon = "📄"
    order = 5

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
        except RuntimeError:
            pass  # C++ object already deleted

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        self.title_label = QLabel("📄 图片转PDF工具")
        self.title_label.setStyleSheet(
            f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']};"
        )
        layout.addWidget(self.title_label)

        self.desc_label = QLabel("将多张图片合并为一个PDF文件，支持拖拽排序")
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_14};")
        layout.addWidget(self.desc_label)

        # 图片列表
        list_card = Card(title="图片列表")
        list_layout = list_card.content_layout

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["文件名", "尺寸", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f1f5f9;
                gridline-color: #334155;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 8px;
                border: none;
                font-weight: {FONT_WEIGHT_600};
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        list_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.add_btn = AnimatedButton("添加图片")
        self.add_btn.clicked.connect(self.add_images)
        self.remove_btn = AnimatedButton("移除选中")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.up_btn = AnimatedButton("上移")
        self.up_btn.clicked.connect(self.move_up)
        self.down_btn = AnimatedButton("下移")
        self.down_btn.clicked.connect(self.move_down)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.up_btn)
        btn_layout.addWidget(self.down_btn)
        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)

        layout.addWidget(list_card)

        # 设置
        settings_card = Card(title="PDF设置")
        settings_layout = QGridLayout()
        settings_card.content_layout.addLayout(settings_layout)

        settings_layout.addWidget(QLabel("页面大小:"), 0, 0)
        self.size_combo = QComboBox()
        self.size_combo.addItems(["自动适应", "A4", "A3", "原图尺寸"])
        self.size_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        settings_layout.addWidget(self.size_combo, 0, 1)

        settings_layout.addWidget(QLabel("启用压缩:"), 1, 0)
        self.compress_check = QCheckBox()
        self.compress_check.setChecked(True)
        settings_layout.addWidget(self.compress_check, 1, 1)

        settings_layout.addWidget(QLabel("JPEG质量:"), 2, 0)
        quality_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(85)
        self.quality_label = QLabel("85%")
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"{v}%")
        )
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        settings_layout.addLayout(quality_layout, 2, 1)

        settings_layout.addWidget(QLabel("输出路径:"), 3, 0)
        path_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择保存位置...")
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
        self.browse_btn.clicked.connect(self.browse_output)
        self.browse_btn.setMaximumWidth(80)
        path_layout.addWidget(self.output_path)
        path_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(path_layout, 3, 1)

        layout.addWidget(settings_card)

        # 操作按钮
        self.convert_btn = AnimatedButton("开始转换")
        self.convert_btn.setMinimumHeight(48)
        self.convert_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{
                background-color: #7c3aed;
            }}
        """)
        self.convert_btn.clicked.connect(self.start_conversion)
        layout.addWidget(self.convert_btn)

        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #0f172a;
                border-radius: 6px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #8b5cf6;
                border-radius: 6px;
            }
        """)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        layout.addStretch()

        self.files = []
        return widget

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self.parent, "选择图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tiff)"
        )
        for f in files:
            if f not in self.files:
                self.files.append(f)
        self.update_table()

    def remove_selected(self):
        indices = sorted(set([i.row() for i in self.table.selectedIndexes()]), reverse=True)
        for i in indices:
            if 0 <= i < len(self.files):
                self.files.pop(i)
        self.update_table()

    def move_up(self):
        row = self.table.currentRow()
        if row > 0:
            self.files[row], self.files[row - 1] = self.files[row - 1], self.files[row]
            self.update_table()
            self.table.selectRow(row - 1)

    def move_down(self):
        row = self.table.currentRow()
        if row < len(self.files) - 1:
            self.files[row], self.files[row + 1] = self.files[row + 1], self.files[row]
            self.update_table()
            self.table.selectRow(row + 1)

    def update_table(self):
        self.table.setRowCount(len(self.files))
        for i, f in enumerate(self.files):
            name = os.path.basename(f)
            try:
                img = Image.open(f)
                size = f"{img.width} x {img.height}"
            except:
                size = "未知"

            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(size))
            self.table.setItem(i, 2, QTableWidgetItem("就绪"))

    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self.parent, "保存PDF", "", "PDF文件 (*.pdf)"
        )
        if path:
            if not path.endswith('.pdf'):
                path += '.pdf'
            self.output_path.setText(path)

    def start_conversion(self):
        if not self.files:
            QMessageBox.warning(self.parent, "警告", "请先添加图片！")
            return

        output = self.output_path.text()
        if not output:
            QMessageBox.warning(self.parent, "警告", "请选择输出路径！")
            return

        if not (IMG2PDF_AVAILABLE or FITZ_AVAILABLE or PIL_AVAILABLE):
            QMessageBox.critical(
                self.parent, "错误",
                "请先安装依赖: pip install img2pdf 或 pip install PyMuPDF 或 pip install Pillow"
            )
            return

        self.convert_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(self.files))
        self.progress.setValue(0)

        self.worker = PDFWorker(
            self.files,
            output,
            self.size_combo.currentText(),
            self.compress_check.isChecked(),
            self.quality_slider.value()
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.start()

    def conversion_finished(self, success, message):
        self.convert_btn.setEnabled(True)
        self.progress.setVisible(False)
        if success:
            QMessageBox.information(self.parent, "完成", message)
        else:
            QMessageBox.critical(self.parent, "错误", message)
