#!/usr/bin/env python3
import sys
import os

# 添加当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from PyQt6.QtWidgets import QApplication

try:
    import toolbox
    from toolbox import SidebarButton

    # 创建应用
    app = QApplication([])

    # 创建窗口
    window = toolbox.ToolboxWindow()

    print(f"已注册的插件数量: {len(window.plugins)}")
    print("\n插件列表:")
    for name, plugin in window.plugins.items():
        print(f"  - {name}: {plugin.name}, {plugin.icon}")

    # 尝试创建按钮
    print("\n尝试创建按钮:")
    for name, plugin in window.plugins.items():
        try:
            btn = SidebarButton(plugin.name, plugin.icon)
            print(f"[OK] 创建按钮成功: {plugin.name}")
            print(f"  按钮文本: {btn.text()}")
        except Exception as e:
            print(f"[ERROR] 创建按钮失败 {plugin.name}: {e}")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()