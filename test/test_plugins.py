#!/usr/bin/env python3
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from toolbox import QApplication, ToolboxWindow

    print("成功导入toolbox模块")

    # 创建应用但不显示
    app = QApplication([])

    # 创建窗口
    window = ToolboxWindow()

    print(f"\n已注册的插件数量: {len(window.plugins)}")
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

    print("\n✅ 插件检查完成")

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
