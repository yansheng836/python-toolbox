#!/usr/bin/env python3
import sys
import os

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import toolbox
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QSizePolicy
from PyQt6.QtCore import Qt

class IconTestWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图标自适应测试")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 测试不同大小的容器
        self.small_container = QWidget()
        small_layout = QVBoxLayout(self.small_container)
        small_label = QLabel("小容器 (300x200)")
        small_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        small_label.setStyleSheet("font-size: 14px; color: #94a3b8;")
        small_layout.addWidget(small_label)
        self.small_container.setFixedSize(300, 200)
        self.small_container.setStyleSheet("background-color: #1e293b; border-radius: 8px;")

        self.medium_container = QWidget()
        medium_layout = QVBoxLayout(self.medium_container)
        medium_label = QLabel("中容器 (400x300)")
        medium_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        medium_label.setStyleSheet("font-size: 16px; color: #94a3b8;")
        medium_layout.addWidget(medium_label)
        self.medium_container.setFixedSize(400, 300)
        self.medium_container.setStyleSheet("background-color: #1e293b; border-radius: 8px;")

        self.large_container = QWidget()
        large_layout = QVBoxLayout(self.large_container)
        large_label = QLabel("大容器 (500x400)")
        large_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        large_label.setStyleSheet("font-size: 18px; color: #94a3b8;")
        large_layout.addWidget(large_label)
        self.large_container.setFixedSize(500, 400)
        self.large_container.setStyleSheet("background-color: #1e293b; border-radius: 8px;")

        # 创建图标标签（使用与WelcomePage相同的设置）
        self.icon_label = QLabel("🖼️")
        self.icon_label.setMinimumSize(60, 60)
        self.icon_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("""
            font-size: 2em;
            font-weight: bold;
        """)
        self.icon_label.setScaledContents(False)

        # 添加到布局
        layout.addWidget(QLabel("测试不同容器大小下的图标自适应效果："))
        layout.addWidget(self.small_container)
        small_layout.addWidget(self.icon_label)

        layout.addWidget(self.medium_container)
        medium_layout.addWidget(self.icon_label)

        layout.addWidget(self.large_container)
        large_layout.addWidget(self.icon_label)

        # 测试按钮
        self.test_btn = QPushButton("切换图标并触发重绘")
        self.test_btn.clicked.connect(self.test_icon_scaling)
        layout.addWidget(self.test_btn)

        layout.addStretch()

    def test_icon_scaling(self):
        """测试图标缩放效果"""
        # 循环切换图标
        icons = ["🖼️", "📏", "📄", "🔌", "🎨", "⚡"]
        current = self.icon_label.text()
        try:
            idx = icons.index(current)
            self.icon_label.setText(icons[(idx + 1) % len(icons)])
        except ValueError:
            self.icon_label.setText("🖼️")

        # 触发重绘
        self.icon_label.update()
        self.update()

def test_icon_scaling():
    """测试图标自适应缩放"""
    app = QApplication([])

    widget = IconTestWidget()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    test_icon_scaling()