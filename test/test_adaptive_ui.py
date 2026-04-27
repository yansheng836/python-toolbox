#!/usr/bin/env python3
import sys
import os

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import toolbox
from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from config import FONT_SIZE_16

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("自适应UI测试")
        self.setGeometry(100, 100, 800, 600)

        # 创建主窗口
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 创建左侧窗口（较小）
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_label = QLabel("左侧小窗口\n(模拟小屏幕)")
        left_label.setStyleSheet(f"font-size: {FONT_SIZE_16};")
        left_layout.addWidget(left_label)
        left_widget.setMinimumWidth(300)
        splitter.addWidget(left_widget)

        # 创建右侧窗口（较大）
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_label = QLabel("右侧大窗口\n(模拟大屏幕)")
        right_label.setStyleSheet(f"font-size: {FONT_SIZE_16};")
        right_layout.addWidget(right_label)
        right_widget.setMinimumWidth(600)
        splitter.addWidget(right_widget)

        # 分割器初始位置
        splitter.setSizes([400, 800])

        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.addWidget(splitter)

        # 说明标签
        info = QLabel("拖动分割线测试自适应效果")
        info.setStyleSheet(f"color: #6366f1; font-size: {FONT_SIZE_16}; margin: 20px;")
        self.main_layout.addWidget(info)

def test_adaptive_ui():
    """测试自适应UI效果"""
    app = QApplication([])

    # 创建测试窗口
    test_window = TestWindow()
    test_window.show()

    # 创建并显示工具箱窗口
    toolbox_window = toolbox.ToolboxWindow(app)
    toolbox_window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    test_adaptive_ui()