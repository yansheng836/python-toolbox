# -*- encoding: utf-8 -*-
"""
test_button.py - Module for toolbox
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from toolbox import SidebarButton

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("按钮测试")
        self.resize(300, 400)

        layout = QVBoxLayout()

        # 测试创建按钮
        test_plugins = [
            ("图片压缩", "🖼️"),
            ("图片批量缩放", "📏"),
            ("图片转PDF", "📄"),
            ("图片格式转换", "🔄"),
            ("图片拼接", "📐"),
            ("我的工具", "🚀")
        ]

        for name, icon in test_plugins:
            try:
                btn = SidebarButton(name, icon)
                btn.setFixedHeight(50)
                layout.addWidget(btn)
                print(f"[OK] 创建按钮成功: {name}")
            except Exception as e:
                print(f"[ERROR] 创建按钮失败 {name}: {e}")

        self.setLayout(layout)

app = QApplication(sys.argv)
window = TestWindow()
window.show()
sys.exit(app.exec())