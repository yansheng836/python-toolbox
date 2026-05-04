# -*- encoding: utf-8 -*-
"""
simple_check.py - Module for toolbox
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import toolbox

app = toolbox.QApplication([])
window = toolbox.ToolboxWindow()

print("=== 导航栏按钮检查 ===")
for i in range(window.nav_layout.count()):
    widget = window.nav_layout.itemAt(i).widget()
    if widget and hasattr(widget, 'text'):
        text = widget.text()
        try:
            print(f"按钮 {i}: {text}")
        except UnicodeEncodeError:
            print(f"按钮 {i}: [包含特殊字符]")

print("\n=== 插件列表 ===")
for name, plugin in window.plugins.items():
    print(f"插件: {plugin.name}")