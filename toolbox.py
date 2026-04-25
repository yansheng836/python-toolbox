__version__ = "1.0.0"

import sys
import os
import json
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import io
import base64

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QScrollArea, QFrame,
    QFileDialog, QMessageBox, QProgressBar, QSpinBox, QComboBox,
    QLineEdit, QTextEdit, QGridLayout, QSizePolicy, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect, QToolTip, QSystemTrayIcon, QMenu, QDialog,
    QDialogButtonBox, QCheckBox, QSlider, QSplitter, QStatusBar,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import (
    Qt, QSize, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QPoint, QRect, QMargins, QSettings, QByteArray
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QColor, QFont, QFontDatabase,
    QLinearGradient, QBrush, QPalette, QCursor, QKeySequence, QShortcut,
    QTransform, QMovie, QFontMetrics, QAction
)

# 尝试导入PIL用于图片处理
try:
    from PIL import Image, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 尝试导入img2pdf用于PDF转换
try:
    import img2pdf
    IMG2PDF_AVAILABLE = True
except ImportError:
    IMG2PDF_AVAILABLE = False

# 尝试导入PyMuPDF (fitz) 作为PDF备选方案
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False


# ==================== 主题配置 ====================
class Theme:
    """现代化深色/浅色主题"""
    DARK = {
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
        'shadow': 'rgba(0, 0, 0, 0.3)'
    }

    LIGHT = {
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
        'shadow': 'rgba(0, 0, 0, 0.1)'
    }

    @staticmethod
    def init_theme():
        """初始化主题系统"""
        pass


# ==================== 动画组件 ====================
class AnimatedButton(QPushButton):
    """带动画效果的按钮"""
    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)

        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.base_style = ""
        self.update_style()

    def update_style(self, theme=None):
        if theme is None:
            theme = Theme.DARK
        self.base_style = f"""
            QPushButton {{
                background-color: {theme['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {theme['primary_hover']};
            }}
            QPushButton:pressed {{
                background-color: {theme['secondary']};
            }}
            QPushButton:disabled {{
                background-color: {theme['surface']};
                color: {theme['text_secondary']};
            }}
        """
        self.setStyleSheet(self.base_style)

    def enterEvent(self, event):
        self.setStyleSheet(self.base_style.replace(
            f"background-color: {Theme.DARK['primary']};",
            f"background-color: {Theme.DARK['primary_hover']};"
        ))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.base_style)
        super().leaveEvent(event)


class Card(QFrame):
    """现代化卡片组件"""
    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self.title = title
        self.setObjectName("card")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        if self.title:
            self.title_label = QLabel(self.title)
            self.title_label.setObjectName("cardTitle")
            self.title_label.setStyleSheet("""
                font-size: 18px;
                font-weight: 700;
                color: #f1f5f9;
            """)
            layout.addWidget(self.title_label)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)

        self.setStyleSheet("""
            QFrame#card {
                background-color: #1e293b;
                border-radius: 12px;
                border: 1px solid #334155;
            }
        """)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class SidebarButton(QPushButton):
    """侧边栏导航按钮"""
    def __init__(self, text, icon_text, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_text}  {text}")
        self.setMinimumHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                text-align: left;
                font-size: 14px;
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


# ==================== 核心功能模块 ====================
class ToolPlugin:
    """插件基类 - 所有工具都应继承此类"""
    name = "Base Tool"
    description = "Base tool description"
    icon = "🔧"
    version = "1.0.0"

    def __init__(self, parent=None):
        self.parent = parent
        self.widget = None

    def create_ui(self) -> QWidget:
        """创建工具UI，子类必须实现"""
        raise NotImplementedError

    def get_widget(self) -> QWidget:
        if self.widget is None:
            self.widget = self.create_ui()
        return self.widget


class ImageCompressor(ToolPlugin):
    """图片压缩工具"""
    name = "图片压缩"
    description = "批量压缩图片，支持JPG/PNG/WebP格式"
    icon = "🖼️"

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # 标题
        title = QLabel("🖼️ 图片压缩工具")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f1f5f9;")
        layout.addWidget(title)

        # 说明
        desc = QLabel("支持 JPG、PNG、WebP 格式，可批量处理并调整压缩质量")
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # 文件选择区域
        file_card = Card(title="选择图片")
        file_layout = file_card.content_layout

        self.file_list = QTextEdit()
        self.file_list.setPlaceholderText("拖拽图片到此处，或点击按钮选择...")
        self.file_list.setMaximumHeight(120)
        self.file_list.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                border: 2px dashed #334155;
                border-radius: 8px;
                color: #94a3b8;
                padding: 8px;
            }
        """)
        file_layout.addWidget(self.file_list)

        btn_layout = QHBoxLayout()
        self.add_btn = AnimatedButton("添加图片")
        self.add_btn.clicked.connect(self.add_images)
        self.clear_btn = AnimatedButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_images)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        layout.addWidget(file_card)

        # 设置区域
        settings_card = Card(title="压缩设置")
        settings_layout = QGridLayout()
        settings_card.content_layout.addLayout(settings_layout)

        settings_layout.addWidget(QLabel("输出格式:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["保持原格式", "JPG", "PNG", "WebP"])
        self.format_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        settings_layout.addWidget(self.format_combo, 0, 1)

        settings_layout.addWidget(QLabel("压缩质量:"), 1, 0)
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

        settings_layout.addWidget(QLabel("输出目录:"), 2, 0)
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("默认保存到原图目录")
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
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(output_layout, 2, 1)

        layout.addWidget(settings_card)

        # 进度和操作
        progress_card = Card()
        progress_layout = progress_card.content_layout

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0f172a;
                border-radius: 6px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #6366f1;
                border-radius: 6px;
            }
        """)
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.start_btn = AnimatedButton("开始压缩")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #34d399, stop:1 #10b981); }
            QPushButton:disabled { background: #334155; color: #64748b; }
        """)
        self.start_btn.clicked.connect(self.start_compression)
        progress_layout.addWidget(self.start_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #94a3b8;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.status_label)

        layout.addWidget(progress_card)
        layout.addStretch()

        self.files = []
        return widget

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self.parent, "选择图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.gif)"
        )
        if files:
            self.files.extend(files)
            self.update_file_list()

    def clear_images(self):
        self.files = []
        self.file_list.clear()

    def update_file_list(self):
        self.file_list.setText("\n".join(self.files))

    def browse_output(self):
        path = QFileDialog.getExistingDirectory(self.parent, "选择输出目录")
        if path:
            self.output_path.setText(path)

    def start_compression(self):
        if not self.files:
            QMessageBox.warning(self.parent, "警告", "请先添加图片！")
            return

        if not PIL_AVAILABLE:
            QMessageBox.critical(self.parent, "错误", "请先安装 Pillow: pip install Pillow")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.files))
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)

        # 使用线程处理
        self.worker = CompressionWorker(
            self.files,
            self.output_path.text() or None,
            self.format_combo.currentText(),
            self.quality_slider.value()
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.compression_finished)
        self.worker.start()

    def compression_finished(self, success, message):
        self.start_btn.setEnabled(True)
        self.status_label.setText("")
        if success:
            QMessageBox.information(self.parent, "完成", message)
        else:
            QMessageBox.critical(self.parent, "错误", message)
        self.progress_bar.setVisible(False)


class CompressionWorker(QThread):
    """图片压缩工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output_dir, format_str, quality):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.format_str = format_str
        self.quality = quality

    def run(self):
        try:
            processed = 0
            for i, file_path in enumerate(self.files):
                self.status.emit(f"正在处理: {os.path.basename(file_path)}")

                img = Image.open(file_path)

                # 确定输出格式
                if self.format_str == "保持原格式":
                    fmt = img.format or 'JPEG'
                else:
                    fmt = {'JPG': 'JPEG', 'PNG': 'PNG', 'WebP': 'WEBP'}[self.format_str]

                # 确定输出路径
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                if self.output_dir:
                    output_path = os.path.join(self.output_dir, f"{base_name}_compressed.{fmt.lower()}")
                else:
                    dir_name = os.path.dirname(file_path)
                    output_path = os.path.join(dir_name, f"{base_name}_compressed.{fmt.lower()}")

                # 处理图片
                if img.mode in ('RGBA', 'LA', 'P') and fmt == 'JPEG':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    else:
                        img = img.convert('RGB')
                elif img.mode != 'RGB' and fmt == 'JPEG':
                    img = img.convert('RGB')

                # 保存
                save_kwargs = {}
                if fmt in ('JPEG', 'WEBP'):
                    save_kwargs['quality'] = self.quality
                    save_kwargs['optimize'] = True
                elif fmt == 'PNG':
                    save_kwargs['optimize'] = True

                img.save(output_path, fmt, **save_kwargs)
                processed += 1
                self.progress.emit(i + 1)

            self.finished.emit(True, f"成功压缩 {processed} 张图片！")
        except Exception as e:
            self.finished.emit(False, f"压缩失败: {str(e)}")


class FormatConvertWorker(QThread):
    """图片格式转换工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    FORMAT_MAP = {
        "JPEG": ("JPEG", "jpg"),
        "PNG":  ("PNG",  "png"),
        "WebP": ("WEBP", "webp"),
        "BMP":  ("BMP",  "bmp"),
        "TIFF": ("TIFF", "tiff"),
        "GIF":  ("GIF", "gif"),
    }

    def __init__(self, files, output_dir, target_fmt):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.target_fmt = target_fmt

    def run(self):
        try:
            processed = 0
            pil_fmt, ext = self.FORMAT_MAP[self.target_fmt]
            for i, file_path in enumerate(self.files):
                self.status.emit(f"正在转换: {os.path.basename(file_path)}")
                img = Image.open(file_path)
                img = self._prepare_image(img, pil_fmt)
                base = os.path.splitext(os.path.basename(file_path))[0]
                out_dir = self.output_dir or os.path.dirname(file_path)
                out_path = os.path.join(out_dir, f"{base}.{ext}")
                img.save(out_path, pil_fmt)
                processed += 1
                self.progress.emit(i + 1)
            self.finished.emit(True, f"成功转换 {processed} 张图片！")
        except Exception as e:
            self.finished.emit(False, f"转换失败: {str(e)}")

    def _prepare_image(self, img, pil_fmt):
        """处理模式兼容性，JPEG/BMP 不支持透明通道"""
        if pil_fmt in ("JPEG", "BMP"):
            if img.mode == "P":
                img = img.convert("RGBA")
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                return bg
            return img.convert("RGB") if img.mode != "RGB" else img
        if pil_fmt == "GIF":
            return img.convert("P") if img.mode not in ("P", "L", "RGB") else img
        return img  # PNG/WebP/TIFF 支持透明，直接保留


class FormatConverter(ToolPlugin):
    """图片格式批量转换工具"""
    name = "图片格式转换"
    description = "批量转换图片格式，支持 JPEG/PNG/WebP/BMP/TIFF/GIF"
    icon = "🔄"

    FORMATS = ["JPEG", "PNG", "WebP", "BMP", "TIFF", "GIF"]

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        title = QLabel("🔄 图片格式批量转换")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f1f5f9;")
        layout.addWidget(title)

        desc = QLabel("纯格式转换，保持原始质量，支持 JPEG / PNG / WebP / BMP / TIFF / GIF")
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # 文件选择
        file_card = Card(title="选择图片")
        self.file_list = QTextEdit()
        self.file_list.setPlaceholderText("点击按钮选择图片...")
        self.file_list.setMaximumHeight(120)
        self.file_list.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                border: 2px dashed #334155;
                border-radius: 8px;
                color: #94a3b8;
                padding: 8px;
            }
        """)
        file_card.content_layout.addWidget(self.file_list)

        btn_layout = QHBoxLayout()
        add_btn = AnimatedButton("添加图片")
        add_btn.clicked.connect(self.add_images)
        clear_btn = AnimatedButton("清空列表")
        clear_btn.clicked.connect(self.clear_images)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        file_card.content_layout.addLayout(btn_layout)
        layout.addWidget(file_card)

        # 转换设置
        settings_card = Card(title="转换设置")
        settings_layout = QGridLayout()
        settings_card.content_layout.addLayout(settings_layout)

        settings_layout.addWidget(QLabel("目标格式:"), 0, 0)
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(self.FORMATS)
        self.fmt_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        settings_layout.addWidget(self.fmt_combo, 0, 1)

        settings_layout.addWidget(QLabel("输出目录:"), 1, 0)
        out_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("默认保存到原图目录")
        self.output_path.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        browse_btn = AnimatedButton("浏览")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_output)
        out_row.addWidget(self.output_path)
        out_row.addWidget(browse_btn)
        settings_layout.addLayout(out_row, 1, 1)
        layout.addWidget(settings_card)

        # 进度和操作
        action_card = Card()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        action_card.content_layout.addWidget(self.progress_bar)

        self.start_btn = AnimatedButton("开始转换")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #34d399, stop:1 #10b981); }
            QPushButton:disabled { background: #334155; color: #64748b; }
        """)
        self.start_btn.clicked.connect(self.start_convert)
        action_card.content_layout.addWidget(self.start_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #94a3b8;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_card.content_layout.addWidget(self.status_label)
        layout.addWidget(action_card)
        layout.addStretch()

        self.files = []
        return widget

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            None, "选择图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif *.gif)"
        )
        if files:
            self.files.extend(files)
            self.file_list.setText("\n".join(self.files))

    def clear_images(self):
        self.files = []
        self.file_list.clear()

    def browse_output(self):
        path = QFileDialog.getExistingDirectory(None, "选择输出目录")
        if path:
            self.output_path.setText(path)

    def start_convert(self):
        if not self.files:
            QMessageBox.warning(None, "警告", "请先添加图片！")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.files))
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)

        self.worker = FormatConvertWorker(
            self.files,
            self.output_path.text() or None,
            self.fmt_combo.currentText()
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.convert_finished)
        self.worker.start()

    def convert_finished(self, success, message):
        self.start_btn.setEnabled(True)
        self.status_label.setText("")
        self.progress_bar.setVisible(False)
        if success:
            QMessageBox.information(None, "完成", message)
        else:
            QMessageBox.critical(None, "错误", message)


class ImageStitchWorker(QThread):
    """图片拼接工作线程"""
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output_path, direction, align, bg_color):
        super().__init__()
        self.files = files
        self.output_path = output_path
        self.direction = direction  # "horizontal" | "vertical"
        self.align = align          # "start" | "center" | "end"
        self.bg_color = bg_color    # (R, G, B)

    def run(self):
        try:
            images = []
            for f in self.files:
                self.status.emit(f"正在读取: {os.path.basename(f)}")
                images.append(Image.open(f).convert("RGBA"))

            self.status.emit("正在拼接...")
            if self.direction == "horizontal":
                total_w = sum(img.width for img in images)
                total_h = max(img.height for img in images)
                canvas = Image.new("RGBA", (total_w, total_h), self.bg_color + (255,))
                x = 0
                for img in images:
                    if self.align == "center":
                        y = (total_h - img.height) // 2
                    elif self.align == "end":
                        y = total_h - img.height
                    else:
                        y = 0
                    canvas.paste(img, (x, y), img)
                    x += img.width
            else:
                total_w = max(img.width for img in images)
                total_h = sum(img.height for img in images)
                canvas = Image.new("RGBA", (total_w, total_h), self.bg_color + (255,))
                y = 0
                for img in images:
                    if self.align == "center":
                        x = (total_w - img.width) // 2
                    elif self.align == "end":
                        x = total_w - img.width
                    else:
                        x = 0
                    canvas.paste(img, (x, y), img)
                    y += img.height

            # 输出格式不支持透明时转 RGB
            ext = os.path.splitext(self.output_path)[1].lower()
            if ext in (".jpg", ".jpeg", ".bmp"):
                bg = Image.new("RGB", canvas.size, self.bg_color)
                bg.paste(canvas, mask=canvas.split()[3])
                canvas = bg

            canvas.save(self.output_path)
            self.finished.emit(True, f"拼接完成，已保存到:\n{self.output_path}")
        except Exception as e:
            self.finished.emit(False, f"拼接失败: {str(e)}")


class ImageStitcher(ToolPlugin):
    """图片拼接工具"""
    name = "图片拼接"
    description = "多图横向/纵向合并为一张"
    icon = "📐"

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        title = QLabel("🪄 图片拼接")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f1f5f9;")
        layout.addWidget(title)

        desc = QLabel("将多张图片横向或纵向合并为一张，支持对齐方式和背景色设置")
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        # 文件列表
        file_card = Card(title="选择图片（顺序即拼接顺序）")
        self.file_list = QTextEdit()
        self.file_list.setPlaceholderText("点击按钮选择图片...")
        self.file_list.setMaximumHeight(120)
        self.file_list.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                border: 2px dashed #334155;
                border-radius: 8px;
                color: #94a3b8;
                padding: 8px;
            }
        """)
        file_card.content_layout.addWidget(self.file_list)

        btn_layout = QHBoxLayout()
        add_btn = AnimatedButton("添加图片")
        add_btn.clicked.connect(self.add_images)
        up_btn = AnimatedButton("↑ 上移")
        up_btn.clicked.connect(self.move_up)
        down_btn = AnimatedButton("↓ 下移")
        down_btn.clicked.connect(self.move_down)
        clear_btn = AnimatedButton("清空列表")
        clear_btn.clicked.connect(self.clear_images)
        for b in (add_btn, up_btn, down_btn, clear_btn):
            btn_layout.addWidget(b)
        btn_layout.addStretch()
        file_card.content_layout.addLayout(btn_layout)
        layout.addWidget(file_card)

        # 拼接设置
        settings_card = Card(title="拼接设置")
        grid = QGridLayout()
        settings_card.content_layout.addLayout(grid)

        combo_style = """
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """

        grid.addWidget(QLabel("拼接方向:"), 0, 0)
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["横向（左→右）", "纵向（上→下）"])
        self.dir_combo.setStyleSheet(combo_style)
        grid.addWidget(self.dir_combo, 0, 1)

        grid.addWidget(QLabel("对齐方式:"), 1, 0)
        self.align_combo = QComboBox()
        self.align_combo.addItems(["顶部/左侧对齐", "居中对齐", "底部/右侧对齐"])
        self.align_combo.setStyleSheet(combo_style)
        grid.addWidget(self.align_combo, 1, 1)

        grid.addWidget(QLabel("背景颜色:"), 2, 0)
        bg_row = QHBoxLayout()
        self.bg_r = QSpinBox(); self.bg_r.setRange(0, 255); self.bg_r.setValue(255)
        self.bg_g = QSpinBox(); self.bg_g.setRange(0, 255); self.bg_g.setValue(255)
        self.bg_b = QSpinBox(); self.bg_b.setRange(0, 255); self.bg_b.setValue(255)
        spin_style = """
            QSpinBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
                color: #f1f5f9;
                max-width: 60px;
            }
        """
        for label, spin in (("R", self.bg_r), ("G", self.bg_g), ("B", self.bg_b)):
            bg_row.addWidget(QLabel(label))
            spin.setStyleSheet(spin_style)
            bg_row.addWidget(spin)
        bg_row.addStretch()
        grid.addLayout(bg_row, 2, 1)

        grid.addWidget(QLabel("输出文件:"), 3, 0)
        out_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择保存路径...")
        self.output_path.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
                color: #f1f5f9;
            }
        """)
        browse_btn = AnimatedButton("浏览")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_output)
        out_row.addWidget(self.output_path)
        out_row.addWidget(browse_btn)
        grid.addLayout(out_row, 3, 1)
        layout.addWidget(settings_card)

        # 操作区
        action_card = Card()
        self.start_btn = AnimatedButton("开始拼接")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white; border: none; border-radius: 8px;
                font-size: 16px; font-weight: 600;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #34d399, stop:1 #10b981); }
            QPushButton:disabled { background: #334155; color: #64748b; }
        """)
        self.start_btn.clicked.connect(self.start_stitch)
        action_card.content_layout.addWidget(self.start_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #94a3b8;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_card.content_layout.addWidget(self.status_label)
        layout.addWidget(action_card)
        layout.addStretch()

        self.files = []
        return widget

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            None, "选择图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif *.gif)"
        )
        if files:
            self.files.extend(files)
            self._refresh_list()

    def move_up(self):
        if len(self.files) > 1:
            self.files.insert(0, self.files.pop())
            self._refresh_list()

    def move_down(self):
        if len(self.files) > 1:
            self.files.append(self.files.pop(0))
            self._refresh_list()

    def clear_images(self):
        self.files = []
        self.file_list.clear()

    def _refresh_list(self):
        self.file_list.setText("\n".join(
            f"{i+1}. {os.path.basename(f)}" for i, f in enumerate(self.files)
        ))

    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            None, "保存拼接图片", "stitched.png",
            "PNG (*.png);;JPEG (*.jpg);;WebP (*.webp)"
        )
        if path:
            self.output_path.setText(path)

    def start_stitch(self):
        if len(self.files) < 2:
            QMessageBox.warning(None, "警告", "请至少添加 2 张图片！")
            return
        if not self.output_path.text():
            QMessageBox.warning(None, "警告", "请选择输出文件路径！")
            return

        direction = "horizontal" if self.dir_combo.currentIndex() == 0 else "vertical"
        align_map = {0: "start", 1: "center", 2: "end"}
        align = align_map[self.align_combo.currentIndex()]
        bg = (self.bg_r.value(), self.bg_g.value(), self.bg_b.value())

        self.start_btn.setEnabled(False)
        self.worker = ImageStitchWorker(
            self.files, self.output_path.text(), direction, align, bg
        )
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.stitch_finished)
        self.worker.start()

    def stitch_finished(self, success, message):
        self.start_btn.setEnabled(True)
        self.status_label.setText("")
        if success:
            QMessageBox.information(None, "完成", message)
        else:
            QMessageBox.critical(None, "错误", message)


class ImageToPDF(ToolPlugin):
    """图片转PDF工具"""
    name = "图片转PDF"
    description = "将多张图片合并为一个PDF文件"
    icon = "📄"

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        title = QLabel("📄 图片转PDF工具")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f1f5f9;")
        layout.addWidget(title)

        desc = QLabel("将多张图片合并为一个PDF文件，支持拖拽排序")
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

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
                font-weight: 600;
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

        # 新增：压缩选项
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
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
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
        # 使用 set 去重，避免同一行的多个单元格索引被重复处理
        indices = sorted(set([i.row() for i in self.table.selectedIndexes()]), reverse=True)
        for i in indices:
            if 0 <= i < len(self.files):
                self.files.pop(i)
        self.update_table()

    def move_up(self):
        row = self.table.currentRow()
        if row > 0:
            self.files[row], self.files[row-1] = self.files[row-1], self.files[row]
            self.update_table()
            self.table.selectRow(row-1)

    def move_down(self):
        row = self.table.currentRow()
        if row < len(self.files) - 1:
            self.files[row], self.files[row+1] = self.files[row+1], self.files[row]
            self.update_table()
            self.table.selectRow(row+1)

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
        import io
        from PIL import Image

        img = Image.open(image_path)
        if img.mode in ('RGBA', 'LA', 'P'):
            # 转为 RGB（去掉透明通道，用白色背景）
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
                # 使用img2pdf
                if self.compress:
                    # 压缩所有图片
                    compressed_images = []
                    for i, img_path in enumerate(self.files):
                        buf = self.compress_image(img_path, self.quality)
                        compressed_images.append(buf)
                        self.progress.emit(i + 1)

                    with open(self.output, "wb") as f:
                        f.write(img2pdf.convert(compressed_images))
                else:
                    # 不压缩，直接用原图
                    for i, _ in enumerate(self.files):
                        self.progress.emit(i + 1)
                    with open(self.output, "wb") as f:
                        f.write(img2pdf.convert(self.files))
            elif FITZ_AVAILABLE:
                # 使用PyMuPDF
                doc = fitz.open()
                for i, img_path in enumerate(self.files):
                    if self.compress:
                        # 使用压缩后的图片
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
                # 使用PIL
                images = []
                for i, f in enumerate(self.files):
                    if self.compress:
                        # 使用压缩后的图片
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


class WelcomePage(QWidget):
    """欢迎页面"""
    def __init__(self, plugins=None, parent=None):
        super().__init__(parent)
        self.plugins = plugins or {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)

        # Logo/标题
        logo = QLabel("🧰")
        logo.setStyleSheet("font-size: 72px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        title = QLabel("工具箱")
        title.setStyleSheet("""
            font-size: 36px;
            font-weight: 800;
            color: #f1f5f9;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("高效、美观、可扩展的桌面工具集合")
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: #94a3b8;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # 特性卡片
        features = QWidget()
        features_layout = QHBoxLayout(features)
        features_layout.setSpacing(16)

        for icon, text, desc in [
            ("🖼️", "图片压缩", "批量压缩，保持质量"),
            ("📄", "图片转PDF", "多图合并，一键转换"),
            ("🔄", "图片格式转换", "格式转换，保持质量"),
            ("📐", "图片拼接", "多图合并，自由拼接"),
            ("📏", "图片批量缩放", "批量缩放，精确控制"),
        ]:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border-radius: 12px;
                    border: 1px solid #334155;
                    padding: 20px;
                }
            """)
            card_layout = QVBoxLayout(card)

            icon_label = QLabel(icon)
            icon_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            font = icon_label.font()
            font.setPointSize(24)
            font.setBold(True)
            icon_label.setFont(font)

            icon_label.setMinimumSize(48, 48)

            card_layout.setStretch(0, 2)
            card_layout.setStretch(1, 1)

            card_layout.addWidget(icon_label)

            text_label = QLabel(text)
            font = text_label.font()
            font.setPointSize(14)
            font.setBold(True)
            text_label.setFont(font)
            text_label.setStyleSheet("color: #f1f5f9;")
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(text_label)

            desc_label = QLabel(desc)
            desc_font = desc_label.font()
            desc_font.setPointSize(11)
            desc_label.setFont(desc_font)
            desc_label.setStyleSheet("color: #94a3b8;")
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(desc_label)

            features_layout.addWidget(card)

        layout.addWidget(features)

        # 提示
        hint = QLabel("👈 从左侧菜单选择工具开始使用")
        hint.setStyleSheet("""
            font-size: 14px;
            color: #6366f1;
            margin-top: 20px;
        """)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch()


# ==================== 设置插件 ====================
class SettingsPlugin(ToolPlugin):
    """设置插件 - 包含通用设置和关于信息"""

    name = "设置"
    description = "应用程序设置和关于信息"
    icon = "⚙️"
    version = "1.0.0"

    def create_ui(self) -> QWidget:
        """创建设置页面UI"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # 标题
        title = QLabel("⚙️ 设置")
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: 800;
            color: #f1f5f9;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #334155;")
        line.setMaximumHeight(1)
        layout.addWidget(line)

        # 通用设置卡片
        general_card = Card(title="通用设置")

        # 主题设置
        theme_label = QLabel("外观:")
        theme_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #f1f5f9;")
        general_card.content_layout.addWidget(theme_label)

        theme_btn_layout = QHBoxLayout()

        light_theme_btn = QPushButton("☀️ 浅色主题")
        light_theme_btn.setMinimumHeight(44)
        light_theme_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #0f172a;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        light_theme_btn.clicked.connect(lambda: self.set_theme("light"))

        dark_theme_btn = QPushButton("🌙 深色主题")
        dark_theme_btn.setMinimumHeight(44)
        dark_theme_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        dark_theme_btn.clicked.connect(lambda: self.set_theme("dark"))

        theme_btn_layout.addWidget(light_theme_btn)
        theme_btn_layout.addWidget(dark_theme_btn)
        theme_btn_layout.addStretch()

        general_card.content_layout.addLayout(theme_btn_layout)
        general_card.content_layout.addStretch()

        # 关于卡片
        about_card = Card(title="关于")

        # 版本信息
        version_label = QLabel(f"版本: v{self.version}")
        version_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #f1f5f9;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(version_label)

        # 功能描述
        desc_label = QLabel("批量处理工具，支持图片压缩、PDF转换、格式转换和拼接")
        desc_label.setStyleSheet("color: #94a3b8; font-size: 14px;")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(desc_label)

        # 官方网站
        website_label = QLabel("<a href='https://www.example.com' style='color: #6366f1; text-decoration: none;'>🌐 访问官方网站</a>")
        website_label.setOpenExternalLinks(True)
        website_label.setStyleSheet("""
            font-size: 15px;
            font-weight: 500;
            padding: 8px;
        """)
        website_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(website_label)

        # 版权信息
        copyright_label = QLabel("© 2023 工具箱开发团队")
        copyright_label.setStyleSheet("color: #64748b; font-size: 12px;")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(copyright_label)

        about_card.content_layout.addStretch()

        # 将卡片添加到主布局
        layout.addWidget(general_card)
        layout.addWidget(about_card)
        layout.addStretch()

        return widget

    def set_theme(self, theme_name):
        """设置主题"""
        if theme_name == "light":
            theme = Theme.LIGHT
        else:
            theme = Theme.DARK

        # 保存主题设置
        self.save_theme_setting(theme_name)

        # 发射信号或更新UI
        print(f"主题已切换为: {theme_name}")

    def save_theme_setting(self, theme_name):
        """保存主题设置"""
        settings = QSettings("Toolbox", "App")
        settings.setValue("theme", theme_name)


# ==================== 主窗口 ====================
class ToolboxWindow(QMainWindow):
    def __init__(self, app=None):
        super().__init__()
        self._app = app
        self.setWindowTitle(f"工具箱 v{__version__}")
        self.setMinimumSize(1200, 800)

        # 加载设置
        self.settings = QSettings("Toolbox", "App")
        self.load_geometry()

        # 初始化插件系统
        self.plugins: Dict[str, ToolPlugin] = {}
        self.current_plugin = None

        self.setup_ui()
        self.register_builtin_plugins()
        self.load_plugins()

        # 系统托盘
        self.setup_tray()

        # 菜单栏
        self.setup_menu()

    def setup_ui(self):
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)

        # 主布局
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMaximumWidth(260)
        self.sidebar.setMinimumWidth(260)
        self.sidebar.setStyleSheet("""
            QFrame#sidebar {
                background-color: #0f172a;
                border-right: 1px solid #1e293b;
            }
        """)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(8)

        # Logo
        logo_layout = QHBoxLayout()
        logo_icon = QLabel("🧰")
        logo_icon.setStyleSheet("font-size: 28px;")
        logo_text = QLabel("工具箱")
        logo_text.setStyleSheet("""
            font-size: 20px;
            font-weight: 700;
            color: #f1f5f9;
        """)
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #334155;")
        line.setMaximumHeight(1)
        sidebar_layout.addWidget(line)

        # 导航按钮容器
        self.nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(0, 8, 0, 0)
        self.nav_layout.setSpacing(4)
        sidebar_layout.addWidget(self.nav_widget)

        sidebar_layout.addStretch()

        # 底部信息
        version = QLabel(f"v{__version__}")
        version.setStyleSheet("color: #475569; font-size: 12px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(version)

        main_layout.addWidget(self.sidebar)

        # 内容区域
        self.content = QStackedWidget()
        self.content.setStyleSheet("""
            QStackedWidget {
                background-color: #0f172a;
            }
        """)

        # 欢迎页
        self.welcome_page = WelcomePage(self.plugins)
        self.content.addWidget(self.welcome_page)

        main_layout.addWidget(self.content, 1)

        # 全局样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f172a;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QLabel {
                color: #f1f5f9;
            }
            QMessageBox {
                background-color: #1e293b;
            }
            QMessageBox QLabel {
                color: #f1f5f9;
            }
            QDialog {
                background-color: #0f172a;
            }
        """)

    def register_plugin(self, plugin_class):
        """注册插件"""
        try:
            plugin = plugin_class(self)
            self.plugins[plugin.name] = plugin

            # 创建导航按钮
            btn = SidebarButton(plugin.name, plugin.icon)
            from functools import partial
            btn.clicked.connect(partial(self.switch_plugin, plugin.name))
            self.nav_layout.addWidget(btn)

            # 添加页面
            widget = plugin.get_widget()
            self.content.addWidget(widget)

        except Exception as e:
            print(f"注册插件失败 {plugin_class.name}: {e}")

    def register_builtin_plugins(self):
        """注册内置插件"""
        self.register_plugin(ImageCompressor)
        self.register_plugin(ImageToPDF)
        self.register_plugin(FormatConverter)
        self.register_plugin(ImageStitcher)
        # 注册设置插件
        self.register_plugin(SettingsPlugin)

    def load_plugins(self):
        """从plugins目录加载外部插件"""
        plugins_dir = Path("plugins")
        if not plugins_dir.exists():
            return

        for file in plugins_dir.glob("*.py"):
            try:
                spec = importlib.util.spec_from_file_location(file.stem, file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        attr.__name__ != 'ToolPlugin' and
                        any(c.__name__ == 'ToolPlugin' for c in attr.__mro__)):
                        self.register_plugin(attr)
            except Exception as e:
                print(f"加载插件失败 {file}: {e}")

    def switch_plugin(self, name):
        """切换插件页面"""
        # 更新按钮状态
        for i in range(self.nav_layout.count()):
            widget = self.nav_layout.itemAt(i).widget()
            if isinstance(widget, SidebarButton):
                widget.setChecked(name in widget.text())

        # 切换页面
        if name in self.plugins:
            widget = self.plugins[name].get_widget()
            index = self.content.indexOf(widget)
            if index >= 0:
                self.content.setCurrentIndex(index)
                self.current_plugin = name

    def setup_tray(self):
        """设置系统托盘"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self)
            self.tray.setToolTip("工具箱")

            # 设置图标
            current_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(current_dir, "icon.ico")
            if os.path.exists(icon_path):
                self.tray.setIcon(QIcon(icon_path))
            else:
                # 如果没有自定义图标，使用简单的彩色图标
                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor("#6366f1"))
                self.tray.setIcon(QIcon(pixmap))

            menu = QMenu()
            show_action = menu.addAction("显示")
            show_action.triggered.connect(self.show)
            quit_action = menu.addAction("退出")
            quit_action.triggered.connect(QApplication.quit)

            self.tray.setContextMenu(menu)
            self.tray.activated.connect(self.tray_activated)
            self.tray.show()

    def setup_menu(self):
        """设置顶部菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu('文件')
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(exit_action)

        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        settings_action = QAction('设置', self)
        settings_action.setShortcut('Ctrl+S')
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

    def show_settings(self):
        """显示设置页面"""
        self.switch_plugin("设置")

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def closeEvent(self, event):
        self.save_geometry()
        event.accept()

    def save_geometry(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

    def load_geometry(self):
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1200, 800)
            self.move(
                QApplication.primaryScreen().geometry().center() -
                self.rect().center()
            )


# ==================== 入口 ====================
def main():
    app = QApplication(sys.argv)

    # 设置应用属性
    app.setApplicationName("工具箱")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Toolbox")
    app.setOrganizationDomain("toolbox.com")

    # 设置字体
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)

    # 设置任务栏和窗口图标
    current_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(current_dir, "icon.ico")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
        app.setDesktopFileName("toolbox.desktop")
        app.setWindowIcon(app_icon)

    # 创建并显示窗口
    window = ToolboxWindow(app)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
