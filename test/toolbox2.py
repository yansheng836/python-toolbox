import sys
import os
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QFileDialog,
    QMessageBox, QProgressBar, QComboBox, QLineEdit, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QGraphicsDropShadowEffect, QSystemTrayIcon, QMenu, QDialog,
    QSlider, QCheckBox, QSpinBox, QGridLayout, QSizePolicy,
    QScrollArea, QSplitter, QStatusBar, QToolButton
)
from PyQt6.QtCore import (
    Qt, QSize, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QPoint, QRect, QSettings, QByteArray, QStandardPaths
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QColor, QFont, QFontDatabase,
    QLinearGradient, QBrush, QPalette, QCursor, QKeySequence, QShortcut,
    QAction, QKeyEvent
)

# 平台检测
IS_WINDOWS = sys.platform == 'win32'
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')


# 资源路径处理（打包后 vs 开发环境）
def get_resource_path(relative_path):
    """获取资源文件路径，兼容打包和开发环境"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ==================== 主题系统（支持跟随系统） ====================
class ThemeManager:
    """主题管理器，支持自动/深色/浅色模式"""

    DARK = {
        'name': 'dark',
        'primary': '#6366f1',
        'primary_hover': '#4f46e5',
        'secondary': '#8b5cf6',
        'bg': '#0f172a',
        'bg_secondary': '#1e293b',
        'bg_card': '#1e293b',
        'surface': '#334155',
        'text': '#f1f5f9',
        'text_secondary': '#94a3b8',
        'border': '#334155',
        'success': '#10b981',
        'warning': '#f59e0b',
        'error': '#ef4444',
    }

    LIGHT = {
        'name': 'light',
        'primary': '#4f46e5',
        'primary_hover': '#4338ca',
        'secondary': '#7c3aed',
        'bg': '#f8fafc',
        'bg_secondary': '#f1f5f9',
        'bg_card': '#ffffff',
        'surface': '#e2e8f0',
        'text': '#0f172a',
        'text_secondary': '#64748b',
        'border': '#e2e8f0',
        'success': '#059669',
        'warning': '#d97706',
        'error': '#dc2626',
    }

    @classmethod
    def get_theme(cls, mode='auto'):
        if mode == 'auto':
            # 检测系统主题（macOS/Windows 支持）
            if IS_MACOS or IS_WINDOWS:
                return cls.DARK  # 简化处理，实际可检测系统设置
        return cls.DARK if mode == 'dark' else cls.LIGHT


# ==================== 跨平台样式 ====================
def get_stylesheet(theme):
    """生成跨平台兼容的 QSS"""
    t = theme

    # macOS 需要更小的控件尺寸
    btn_height = "32px" if IS_MACOS else "40px"
    font_size = "13px" if IS_MACOS else "14px"

    return f"""
    QMainWindow {{
        background-color: {t['bg']};
    }}

    QFrame {{
        background-color: transparent;
    }}

    /* 卡片样式 */
    QFrame#card {{
        background-color: {t['bg_card']};
        border-radius: 12px;
        border: 1px solid {t['border']};
    }}

    /* 按钮样式 */
    QPushButton {{
        background-color: {t['primary']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        min-height: {btn_height};
        font-weight: 600;
        font-size: {font_size};
    }}

    QPushButton:hover {{
        background-color: {t['primary_hover']};
    }}

    QPushButton:pressed {{
        background-color: {t['secondary']};
    }}

    QPushButton:disabled {{
        background-color: {t['surface']};
        color: {t['text_secondary']};
    }}

    QPushButton#secondary {{
        background-color: transparent;
        color: {t['text']};
        border: 1px solid {t['border']};
    }}

    /* macOS 菜单栏样式 */
    QMenuBar {{
        background-color: {t['bg']};
        color: {t['text']};
    }}

    QMenuBar::item:selected {{
        background-color: {t['primary']};
        color: white;
    }}

    /* 侧边栏 */
    QFrame#sidebar {{
        background-color: {t['bg']};
        border-right: 1px solid {t['border']};
    }}

    /* 输入框 */
    QLineEdit, QTextEdit, QComboBox {{
        background-color: {t['bg']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 8px;
        color: {t['text']};
        font-size: {font_size};
    }}

    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border: 2px solid {t['primary']};
    }}

    /* 表格 */
    QTableWidget {{
        background-color: {t['bg']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        color: {t['text']};
        gridline-color: {t['border']};
    }}

    QHeaderView::section {{
        background-color: {t['bg_secondary']};
        color: {t['text_secondary']};
        padding: 8px;
        border: none;
        font-weight: 600;
    }}

    /* 进度条 */
    QProgressBar {{
        background-color: {t['bg']};
        border-radius: 6px;
        text-align: center;
        color: {t['text']};
    }}

    QProgressBar::chunk {{
        background-color: {t['primary']};
        border-radius: 6px;
    }}

    /* 滑块 */
    QSlider::groove:horizontal {{
        height: 6px;
        background: {t['surface']};
        border-radius: 3px;
    }}

    QSlider::handle:horizontal {{
        width: 18px;
        height: 18px;
        margin: -6px 0;
        background: {t['primary']};
        border-radius: 9px;
    }}

    /* 滚动条 */
    QScrollBar:vertical {{
        width: 8px;
        background: transparent;
    }}

    QScrollBar::handle:vertical {{
        background: {t['surface']};
        border-radius: 4px;
        min-height: 30px;
    }}

    /* 标签 */
    QLabel {{
        color: {t['text']};
    }}

    QLabel#title {{
        font-size: 24px;
        font-weight: 700;
    }}

    QLabel#subtitle {{
        font-size: 14px;
        color: {t['text_secondary']};
    }}
    """


# ==================== 跨平台文件对话框 ====================
class FileDialogHelper:
    """统一的文件对话框（处理平台差异）"""

    @staticmethod
    def get_open_images(parent, multiple=True):
        """获取图片文件"""
        filters = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff);;All Files (*)"

        if multiple:
            files, _ = QFileDialog.getOpenFileNames(
                parent, "Select Images", "", filters
            )
            return files
        else:
            file, _ = QFileDialog.getOpenFileName(
                parent, "Select Image", "", filters
            )
            return [file] if file else []

    @staticmethod
    def get_save_path(parent, default_name="output.pdf", filter_str="PDF (*.pdf)"):
        """获取保存路径"""
        path, _ = QFileDialog.getSaveFileName(
            parent, "Save As", default_name, filter_str
        )
        return path

    @staticmethod
    def get_directory(parent):
        """获取目录"""
        return QFileDialog.getExistingDirectory(parent, "Select Folder")


# ==================== 核心组件（跨平台优化） ====================
class ModernButton(QPushButton):
    """现代化按钮，支持平台适配"""

    def __init__(self, text="", icon=None, parent=None, color=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # macOS 控件稍小
        if IS_MACOS:
            self.setMinimumHeight(32)
        else:
            self.setMinimumHeight(40)

        if color:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {color};
                    opacity: 0.9;
                }}
            """)


class ToolCard(QFrame):
    """工具卡片"""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        # 阴影效果（Windows/Linux 支持更好）
        if not IS_MACOS:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 40))
            shadow.setOffset(0, 4)
            self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("title")
            title_label.setStyleSheet("font-size: 18px; font-weight: 700;")
            layout.addWidget(title_label)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)


# ==================== 图片压缩工具（跨平台版） ====================
class ImageCompressorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title = QLabel("🖼️ Image Compressor")
        title.setObjectName("title")
        layout.addWidget(title)

        # 文件选择
        file_card = ToolCard("Files")
        file_layout = QVBoxLayout(file_card.content)

        self.file_list = QTextEdit()
        self.file_list.setPlaceholderText("Drop images here or click Add...")
        self.file_list.setMaximumHeight(120)
        self.file_list.setAcceptDrops(True)  # 支持拖拽
        file_layout.addWidget(self.file_list)

        btn_layout = QHBoxLayout()
        self.add_btn = ModernButton("Add Images")
        self.add_btn.clicked.connect(self.add_images)
        self.clear_btn = ModernButton("Clear", color="#64748b")
        self.clear_btn.clicked.connect(self.clear_all)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        layout.addWidget(file_card)

        # 设置
        settings_card = ToolCard("Settings")
        settings_layout = QGridLayout(settings_card.content)
        settings_layout.setSpacing(12)

        settings_layout.addWidget(QLabel("Format:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Keep Original", "JPEG", "PNG", "WebP"])
        settings_layout.addWidget(self.format_combo, 0, 1)

        settings_layout.addWidget(QLabel("Quality:"), 1, 0)
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
        settings_layout.addLayout(quality_layout, 1, 1)

        settings_layout.addWidget(QLabel("Output:"), 2, 0)
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Same as source (default)")
        self.browse_btn = ModernButton("Browse", color="#64748b")
        self.browse_btn.setMaximumWidth(100)
        self.browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(output_layout, 2, 1)

        layout.addWidget(settings_card)

        # 操作区
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.start_btn = ModernButton("Start Compression", color="#10b981")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.clicked.connect(self.start_compression)
        layout.addWidget(self.start_btn)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()

    def add_images(self):
        files = FileDialogHelper.get_open_images(self)
        self.files.extend([f for f in files if f not in self.files])
        self.update_list()

    def clear_all(self):
        self.files = []
        self.file_list.clear()

    def update_list(self):
        self.file_list.setText("\n".join(self.files))

    def browse_output(self):
        path = FileDialogHelper.get_directory(self)
        if path:
            self.output_edit.setText(path)

    def start_compression(self):
        if not self.files:
            QMessageBox.warning(self, "Warning", "Please add images first!")
            return

        # 检查依赖
        try:
            from PIL import Image
        except ImportError:
            QMessageBox.critical(
                self, "Error",
                "Pillow not installed!\nRun: pip install Pillow"
            )
            return

        self.progress.setVisible(True)
        self.progress.setMaximum(len(self.files))
        self.progress.setValue(0)
        self.start_btn.setEnabled(False)

        # 启动工作线程
        self.worker = CompressWorker(
            self.files,
            self.output_edit.text() or None,
            self.format_combo.currentText(),
            self.quality_slider.value()
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.compression_done)
        self.worker.start()

    def compression_done(self, success, msg):
        self.start_btn.setEnabled(True)
        self.progress.setVisible(False)

        if success:
            QMessageBox.information(self, "Done", msg)
        else:
            QMessageBox.critical(self, "Error", msg)


class CompressWorker(QThread):
    """压缩工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output_dir, fmt, quality):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.fmt = fmt
        self.quality = quality

    def run(self):
        try:
            from PIL import Image
            import os

            for i, path in enumerate(self.files):
                self.status.emit(f"Processing: {os.path.basename(path)}")

                img = Image.open(path)

                # 确定格式
                if self.fmt == "Keep Original":
                    save_fmt = img.format or 'JPEG'
                else:
                    save_fmt = self.fmt

                # 构建输出路径
                base = os.path.splitext(os.path.basename(path))[0]
                ext = save_fmt.lower() if save_fmt != 'JPEG' else 'jpg'

                if self.output_dir:
                    out = os.path.join(self.output_dir, f"{base}_compressed.{ext}")
                else:
                    dir_name = os.path.dirname(path)
                    out = os.path.join(dir_name, f"{base}_compressed.{ext}")

                # 处理透明通道
                if img.mode in ('RGBA', 'LA', 'P') and save_fmt == 'JPEG':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        bg.paste(img, mask=img.split()[-1])
                        img = bg
                    else:
                        img = img.convert('RGB')
                elif img.mode != 'RGB' and save_fmt == 'JPEG':
                    img = img.convert('RGB')

                # 保存
                kwargs = {}
                if save_fmt in ('JPEG', 'WEBP'):
                    kwargs = {'quality': self.quality, 'optimize': True}
                elif save_fmt == 'PNG':
                    kwargs = {'optimize': True}

                img.save(out, save_fmt, **kwargs)
                self.progress.emit(i + 1)

            self.finished.emit(True, f"Compressed {len(self.files)} images!")

        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


# ==================== 图片转PDF工具 ====================
class ImageToPDFWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("📄 Images to PDF")
        title.setObjectName("title")
        layout.addWidget(title)

        # 文件列表
        list_card = ToolCard("Image List")
        list_layout = QVBoxLayout(list_card.content)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Name", "Size", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        list_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.add_btn = ModernButton("Add")
        self.add_btn.clicked.connect(self.add_images)
        self.remove_btn = ModernButton("Remove", color="#ef4444")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.up_btn = ModernButton("▲")
        self.up_btn.clicked.connect(self.move_up)
        self.down_btn = ModernButton("▼")
        self.down_btn.clicked.connect(self.move_down)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.up_btn)
        btn_layout.addWidget(self.down_btn)
        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)

        layout.addWidget(list_card)

        # 设置
        settings_card = ToolCard("PDF Settings")
        settings_layout = QGridLayout(settings_card.content)

        settings_layout.addWidget(QLabel("Page Size:"), 0, 0)
        self.size_combo = QComboBox()
        self.size_combo.addItems(["Auto-fit", "A4", "A3", "Original"])
        settings_layout.addWidget(self.size_combo, 0, 1)

        settings_layout.addWidget(QLabel("Save to:"), 1, 0)
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("output.pdf")
        self.browse_btn = ModernButton("Browse", color="#64748b")
        self.browse_btn.setMaximumWidth(100)
        self.browse_btn.clicked.connect(self.browse_output)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(path_layout, 1, 1)

        layout.addWidget(settings_card)

        # 转换按钮
        self.convert_btn = ModernButton("Convert to PDF", color="#8b5cf6")
        self.convert_btn.setMinimumHeight(48)
        self.convert_btn.clicked.connect(self.start_conversion)
        layout.addWidget(self.convert_btn)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        layout.addStretch()

    def add_images(self):
        files = FileDialogHelper.get_open_images(self)
        for f in files:
            if f not in self.files:
                self.files.append(f)
        self.update_table()

    def remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            if 0 <= r < len(self.files):
                self.files.pop(r)
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
            try:
                from PIL import Image
                img = Image.open(f)
                size = f"{img.width}×{img.height}"
            except:
                size = "?"

            self.table.setItem(i, 0, QTableWidgetItem(os.path.basename(f)))
            self.table.setItem(i, 1, QTableWidgetItem(size))
            self.table.setItem(i, 2, QTableWidgetItem("Ready"))

    def browse_output(self):
        path = FileDialogHelper.get_save_path(self, "output.pdf")
        if path:
            self.path_edit.setText(path)

    def start_conversion(self):
        if not self.files:
            QMessageBox.warning(self, "Warning", "Add images first!")
            return

        out = self.path_edit.text()
        if not out:
            QMessageBox.warning(self, "Warning", "Select output path!")
            return

        # 检查可用的PDF库
        pdf_lib = None
        for lib, name in [(self._check_img2pdf, "img2pdf"),
                          (self._check_fitz, "PyMuPDF"),
                          (self._check_pil, "Pillow")]:
            if lib():
                pdf_lib = name
                break

        if not pdf_lib:
            QMessageBox.critical(
                self, "Error",
                "No PDF library found!\nInstall: pip install img2pdf"
            )
            return

        self.convert_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(self.files))
        self.progress.setValue(0)

        self.worker = PDFWorker(self.files, out, self.size_combo.currentText())
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.conversion_done)
        self.worker.start()

    def _check_img2pdf(self):
        try:
            import img2pdf
            return True
        except:
            return False

    def _check_fitz(self):
        try:
            import fitz
            return True
        except:
            return False

    def _check_pil(self):
        try:
            from PIL import Image
            return True
        except:
            return False

    def conversion_done(self, success, msg):
        self.convert_btn.setEnabled(True)
        self.progress.setVisible(False)

        if success:
            QMessageBox.information(self, "Done", msg)
        else:
            QMessageBox.critical(self, "Error", msg)


class PDFWorker(QThread):
    """PDF转换线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output, page_size):
        super().__init__()
        self.files = files
        self.output = output
        self.page_size = page_size

    def run(self):
        try:
            # 优先使用 img2pdf
            try:
                import img2pdf
                with open(self.output, "wb") as f:
                    f.write(img2pdf.convert(self.files))
                self.finished.emit(True, f"PDF saved:\n{self.output}")
                return
            except ImportError:
                pass

            # 备选：PyMuPDF
            try:
                import fitz
                doc = fitz.open()
                for i, path in enumerate(self.files):
                    img = fitz.open(path)
                    pdf_bytes = img.convert_to_pdf()
                    img_pdf = fitz.open("pdf", pdf_bytes)
                    doc.insert_pdf(img_pdf)
                    self.progress.emit(i + 1)
                doc.save(self.output)
                doc.close()
                self.finished.emit(True, f"PDF saved:\n{self.output}")
                return
            except ImportError:
                pass

            # 备选：PIL
            from PIL import Image
            images = []
            for i, path in enumerate(self.files):
                img = Image.open(path)
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

            self.finished.emit(True, f"PDF saved:\n{self.output}")

        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


# ==================== 主窗口 ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Toolbox")
        self.setMinimumSize(1100, 750 if IS_MACOS else 800)

        # macOS 特殊设置
        if IS_MACOS:
            self.setUnifiedTitleAndToolBarOnMac(True)
            self.menuBar().setNativeMenuBar(True)

        self.setup_ui()
        self.setup_menu()
        self.load_settings()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMaximumWidth(240)
        sidebar.setMinimumWidth(240)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(8)

        # Logo
        logo = QLabel("🧰 Toolbox")
        logo.setStyleSheet("font-size: 20px; font-weight: 700;")
        sidebar_layout.addWidget(logo)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #334155; max-height: 1px;")
        sidebar_layout.addWidget(line)

        # 导航
        nav = QWidget()
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 8, 0, 0)
        nav_layout.setSpacing(4)

        self.nav_buttons = []
        tools = [
            ("🖼️", "Compressor", ImageCompressorWidget),
            ("📄", "To PDF", ImageToPDFWidget),
        ]

        self.stack = QStackedWidget()

        # 欢迎页
        welcome = QWidget()
        w_layout = QVBoxLayout(welcome)
        w_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_label = QLabel("Select a tool from sidebar")
        w_label.setStyleSheet("font-size: 18px; color: #64748b;")
        w_layout.addWidget(w_label)
        self.stack.addWidget(welcome)

        for icon, name, widget_class in tools:
            btn = QPushButton(f"  {icon}  {name}")
            btn.setCheckable(True)
            btn.setMinimumHeight(44 if IS_MACOS else 48)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94a3b8;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: rgba(99, 102, 241, 0.1);
                    color: #f1f5f9;
                }
                QPushButton:checked {
                    background-color: rgba(99, 102, 241, 0.2);
                    color: #6366f1;
                    font-weight: 600;
                }
            """)

            # 创建工具页
            page = widget_class()
            self.stack.addWidget(page)
            index = self.stack.count() - 1

            btn.clicked.connect(lambda checked, idx=index: self.switch_page(idx))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_layout.addStretch()
        sidebar_layout.addWidget(nav)

        # 底部
        footer = QLabel("v1.0.0")
        footer.setStyleSheet("color: #475569; font-size: 12px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(footer)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack, 1)

        # 应用主题
        theme = ThemeManager.get_theme()
        self.setStyleSheet(get_stylesheet(theme))

    def setup_menu(self):
        """设置菜单栏（macOS 友好）"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("File")

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit if IS_MACOS else "Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 帮助菜单
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def switch_page(self, index):
        for btn in self.nav_buttons:
            btn.setChecked(False)

        sender = self.sender()
        if sender:
            sender.setChecked(True)

        self.stack.setCurrentIndex(index)

    def show_about(self):
        QMessageBox.about(
            self, "About Toolbox",
            "<h2>Toolbox v1.0</h2>"
            "<p>A modern, cross-platform utility toolkit.</p>"
            "<p>Built with PyQt6</p>"
        )

    def load_settings(self):
        settings = QSettings("Toolbox", "App")
        geo = settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(1200, 800)
            qr = self.frameGeometry()
            cp = self.screen().availableGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())

    def closeEvent(self, event):
        settings = QSettings("Toolbox", "App")
        settings.setValue("geometry", self.saveGeometry())
        event.accept()


def main():
    # 高DPI支持
    if IS_WINDOWS:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("Toolbox")

    # 设置字体
    if IS_MACOS:
        font = QFont(".AppleSystemUIFont", 13)
    elif IS_WINDOWS:
        font = QFont("Microsoft YaHei UI", 10)
    else:
        font = QFont("Noto Sans CJK SC", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()