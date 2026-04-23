#!/usr/bin/env python3
import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QFileInfo

def test_icon():
    app = QApplication(sys.argv)

    # 检查图标文件
    icon_path = "icon.ico"
    print(f"图标文件路径: {os.path.abspath(icon_path)}")
    print(f"图标文件存在: {QFileInfo(icon_path).exists()}")

    # 加载图标
    icon = QIcon(icon_path)
    print(f"图标是否为空: {icon.isNull()}")

    if not icon.isNull():
        sizes = icon.availableSizes()
        print(f"可用尺寸: {sizes}")

        # 创建测试窗口
        window = QMainWindow()
        window.setWindowTitle("图标测试")
        window.setWindowIcon(icon)
        window.setFixedSize(300, 200)

        label = QLabel("检查窗口图标", window)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        window.setCentralWidget(label)

        window.show()
        return app.exec()
    else:
        print("图标加载失败！")
        return 1

if __name__ == "__main__":
    sys.exit(test_icon())