# -*- encoding: utf-8 -*-
"""
check_plugins.py - Module for toolbox
"""

#!/usr/bin/env python3
import sys
import os

# 添加当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    import toolbox

    # 创建应用但不显示
    app = toolbox.QApplication([])

    # 创建窗口
    window = toolbox.ToolboxWindow()

    print(f"已注册的插件数量: {len(window.plugins)}")
    print("\n插件详细信息:")

    for name, plugin in window.plugins.items():
        print(f"\n插件名称: {plugin.name}")
        try:
            print(f"图标: {repr(plugin.icon)}")
        except UnicodeEncodeError:
            print("图标: [特殊字符]")
        print(f"类型: {type(plugin)}")

        # 检查是否有get_widget方法
        if hasattr(plugin, 'get_widget'):
            try:
                widget = plugin.get_widget()
                print(f"UI类: {type(widget)}")
                print("UI创建成功")
            except Exception as e:
                print(f"UI创建失败: {e}")
        else:
            print("没有get_widget方法")

        # 检查是否在导航布局中
        found = False
        for i in range(window.nav_layout.count()):
            widget = window.nav_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'text'):
                if plugin.name in widget.text():
                    found = True
                    print("✓ 在导航栏中找到")
                    break
        if not found:
            print("✗ 在导航栏中未找到")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()