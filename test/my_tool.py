# -*- encoding: utf-8 -*-
"""
my_tool.py - Module for toolbox
"""

from toolbox import ToolPlugin
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class MyTool(ToolPlugin):
    name = "我的工具"
    description = "这是一个示例插件"
    icon = "🚀"

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Hello World!"))
        return widget