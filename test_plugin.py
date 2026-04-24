#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# 添加当前目录到路径
sys.path.append('.')

try:
    from plugins.image_scaler import ImageScaler
    print("[OK] ImageScaler 导入成功")
    print(f"  名称: {ImageScaler.name}")
    print(f"  图标: {ImageScaler.icon}")
except Exception as e:
    print(f"[ERROR] 导入失败: {e}")
    import traceback
    traceback.print_exc()

try:
    # 测试主程序加载
    import toolbox
    print("\n[OK] toolbox 模块导入成功")

    # 创建工具箱实例（不显示GUI）
    app = toolbox.QApplication([])
    window = toolbox.ToolboxWindow()
    window.load_plugins()

    print(f"\n已注册的插件数量: {len(window.plugins)}")
    for name, plugin in window.plugins.items():
        print(f"  - {name}: {plugin.name}")

except Exception as e:
    print(f"\n[ERROR] toolbox 测试失败: {e}")
    import traceback
    traceback.print_exc()