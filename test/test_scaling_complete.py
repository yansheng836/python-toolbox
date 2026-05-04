# -*- encoding: utf-8 -*-
"""
test_scaling_complete.py - Module for toolbox
"""

#!/usr/bin/env python3
import sys
import os

# 添加当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("=== 完整测试图片缩放功能 ===\n")

try:
    # 导入必要的模块
    from PyQt6.QtWidgets import QApplication
    print("[OK] PyQt6 导入成功")
except Exception as e:
    print(f"[ERROR] PyQt6 导入失败: {e}")
    sys.exit(1)

try:
    # 导入主程序
    import toolbox
    print("[OK] toolbox 导入成功")

    # 创建QApplication
    app = QApplication([])

    # 创建窗口
    window = toolbox.ToolboxWindow()
    print("[OK] ToolboxWindow 创建成功")

    # 检查插件
    print(f"\n已注册的插件数量: {len(window.plugins)}")
    for name, plugin in window.plugins.items():
        print(f"  - {name}: {plugin.name}")

    # 测试缩放插件
    scaler_plugin = None
    for name, plugin in window.plugins.items():
        if "图片批量缩放" in plugin.name:
            scaler_plugin = plugin
            print(f"\n[OK] 找到缩放插件: {name}")
            break

    if scaler_plugin:
        print("\n测试缩放插件UI创建...")
        try:
            ui = scaler_plugin.get_widget()
            print(f"[OK] UI创建成功: {type(ui)}")

            # 检查UI是否有效
            if ui and hasattr(ui, 'select_files'):
                print("[OK] UI方法正常")
            else:
                print("[WARNING] UI方法可能有问题")

        except Exception as e:
            print(f"[ERROR] UI创建失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n[ERROR] 未找到缩放插件")

    print("\n测试完成")

except Exception as e:
    print(f"\n[ERROR] 测试失败: {e}")
    import traceback
    traceback.print_exc()