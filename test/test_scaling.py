#!/usr/bin/env python3
import sys

# 添加当前目录到路径
sys.path.append('.')

try:
    from plugins.image_scaler import ImageScaler, ImageScalerWidget
    print("[OK] ImageScaler 导入成功")
    print(f"类名: {ImageScaler.__name__}")
    print(f"基类: {[base.__name__ for base in ImageScaler.__mro__]}")

    # 测试创建UI
    widget = ImageScalerWidget()
    print("[OK] ImageScalerWidget 创建成功")

except Exception as e:
    print(f"[ERROR] 错误: {e}")
    import traceback
    traceback.print_exc()

# 测试主程序中的插件注册
try:
    import toolbox
    print("\n[OK] toolbox 导入成功")

    # 创建QApplication
    app = toolbox.QApplication([])

    # 创建窗口
    window = toolbox.ToolboxWindow()

    # 检查插件
    print(f"\n注册的插件数量: {len(window.plugins)}")
    scaler_plugins = []
    for name, plugin in window.plugins.items():
        if "Scaler" in name or "Scal" in name:
            scaler_plugins.append((name, plugin))
            print(f"  - {name}: {plugin.name}")

    if scaler_plugins:
        print("\n测试缩放插件UI创建:")
        for name, plugin in scaler_plugins:
            # 测试创建UI
            try:
                ui = plugin.create_ui()
                print(f"    [OK] {name} UI创建成功: {type(ui)}")
            except Exception as e:
                print(f"    [ERROR] {name} UI创建失败: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("\n未找到缩放插件")

except Exception as e:
    print(f"\n[ERROR] toolbox 测试失败: {e}")
    import traceback
    traceback.print_exc()