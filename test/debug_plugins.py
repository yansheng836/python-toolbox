import sys

# 添加当前目录到路径
sys.path.append('.')

try:
    import toolbox

    # 创建 QApplication
    app = toolbox.QApplication([])

    # 创建窗口
    window = toolbox.ToolboxWindow()

    print("=== 内置插件 ===")
    window.register_builtin_plugins()
    for name, plugin in window.plugins.items():
        print(f"  {name}: {plugin.name}")

    print("\n=== 加载外部插件 ===")
    window.load_plugins()
    for name, plugin in window.plugins.items():
        print(f"  {name}: {plugin.name}")

    print(f"\n总插件数: {len(window.plugins)}")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()