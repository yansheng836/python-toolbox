# -*- encoding: utf-8 -*-
"""
final_test.py - Module for toolbox
"""

#!/usr/bin/env python3
import sys
import os

# 添加当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("=== 完整测试图片缩放功能 ===\n")

try:
    import toolbox
    from PyQt6.QtWidgets import QApplication

    # 创建应用
    app = QApplication([])
    window = toolbox.ToolboxWindow()

    print("[OK] 程序启动成功")
    print(f"[OK] 已加载 {len(window.plugins)} 个插件:")

    # 检查所有插件
    for name, plugin in window.plugins.items():
        print(f"  - {name}: {plugin.name}")

        # 测试每个插件的UI创建
        try:
            ui = plugin.get_widget()
            print(f"    [OK] UI创建成功: {type(ui).__name__}")
        except Exception as e:
            print(f"    [ERROR] UI创建失败: {e}")

    # 特殊检查缩放插件
    scaler_found = False
    for name, plugin in window.plugins.items():
        if "缩放" in plugin.name or "Scaler" in plugin.name:
            scaler_found = True
            print(f"\n[OK] 找到缩放插件: {plugin.name}")

            # 检查UI的方法
            ui = plugin.get_widget()
            if hasattr(ui, 'select_files'):
                print("[OK] select_files 方法存在")
            if hasattr(ui, 'start_scaling'):
                print("[OK] start_scaling 方法存在")
            if hasattr(ui, 'progress_bar'):
                print("[OK] progress_bar 属性存在")

    if not scaler_found:
        print("\n[ERROR] 未找到缩放插件")

    print("\n测试完成！")

except Exception as e:
    print(f"\n[ERROR] 测试失败: {e}")
    import traceback
    traceback.print_exc()