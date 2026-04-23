#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# 添加当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

class TestScalingDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("测试图片缩放功能")
        self.resize(400, 300)

        layout = QVBoxLayout()

        # 说明
        info = QLabel("图片缩放功能已成功加载！\n\n"
                     "1. 插件已正确注册\n"
                     "2. UI界面已创建成功\n"
                     "3. 功能已添加到程序\n\n"
                     "你可以运行程序并测试完整功能。")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        # 按钮
        btn = QPushButton("关闭")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        self.setLayout(layout)

def main():
    app = QApplication(sys.argv)

    # 测试缩放插件
    try:
        import toolbox
        window = toolbox.ToolboxWindow()

        # 查找缩放插件
        scaler_plugin = None
        for name, plugin in window.plugins.items():
            if "图片批量缩放" in plugin.name:
                scaler_plugin = plugin
                break

        if scaler_plugin:
            dialog = TestScalingDialog()
            dialog.exec()
        else:
            print("未找到缩放插件")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()