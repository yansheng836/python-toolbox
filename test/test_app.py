#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试脚本 - 快速验证设置功能
"""

import sys
from PyQt6.QtWidgets import QApplication
from toolbox import ToolboxWindow

def main():
    app = QApplication(sys.argv)

    # 窗口标题
    app.setApplicationName("工具箱")
    app.setApplicationVersion("2.0.1")

    # 创建窗口
    window = ToolboxWindow(app)
    window.setWindowTitle("工具箱 v2.0.1 - 测试模式")
    window.show()

    print("程序启动成功")
    print("功能列表:")
    print("   - 顶部菜单栏: 文件 -> 退出")
    print("   - 工具 -> 设置 (快捷键 Ctrl+S)")
    print("   - 设置页面包含:")
    print("     * 通用设置 -> 浅色/深色主题切换")
    print("     * 关于 -> 版本信息和官网链接")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()