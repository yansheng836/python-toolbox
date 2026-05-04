# -*- encoding: utf-8 -*-
"""
simple_test.py - Module for toolbox
"""

import sys
import os

# 添加当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print(f"当前目录: {current_dir}")
print(f"Python路径: {sys.path[0]}")

try:
    print("\n尝试导入 PIL...")
    print("[OK] PIL 导入成功")
except ImportError as e:
    print(f"[ERROR] PIL 导入失败: {e}")

try:
    print("\n尝试导入 toolbox...")
    import toolbox
    print("[OK] toolbox 导入成功")

    # 创建QApplication
    app = toolbox.QApplication([])

    # 创建窗口
    window = toolbox.ToolboxWindow()

    print(f"\n已注册的插件:")
    for name, plugin in window.plugins.items():
        print(f"  - {name}: {plugin.name}")

        if "Scaler" in name or "Scal" in name:
            print("    [OK] 找到缩放插件！")

except Exception as e:
    print(f"[ERROR] toolbox 导入失败: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n尝试直接导入插件...")
    plugins_dir = os.path.join(current_dir, "plugins")
    if os.path.exists(plugins_dir):
        sys.path.insert(0, plugins_dir)
        from image_scaler import ImageScaler
        print("[OK] ImageScaler 导入成功")
        print(f"  名称: {ImageScaler.name}")
        print(f"  图标: {ImageScaler.icon}")
    else:
        print("[ERROR] 插件目录不存在")
except Exception as e:
    print(f"[ERROR] ImageScaler 导入失败: {e}")
    import traceback
    traceback.print_exc()