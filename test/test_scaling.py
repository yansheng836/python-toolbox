# -*- encoding: utf-8 -*-
"""
test_scaling.py - image_scaler 冒烟脚本（非 pytest 用例）

pytest 收集会跳过：模块级已用 `if __name__ == "__main__":` 守卫，
不会被当作 test_*.py 测试执行。
"""

#!/usr/bin/env python3


def _run_smoke():
    """导入与 UI 创建冒烟检查；仅作为独立脚本运行时执行"""
    from plugins.image_scaler import ImageScaler, ImageScalerWidget
    print("[OK] ImageScaler 导入成功")
    print(f"类名: {ImageScaler.__name__}")
    print(f"基类: {[base.__name__ for base in ImageScaler.__mro__]}")
    widget = ImageScalerWidget()
    print(f"[OK] ImageScalerWidget 创建成功: {type(widget).__name__}")

    import toolbox
    print("")
    print("[OK] toolbox 导入成功")
    app = toolbox.QApplication([])
    window = toolbox.ToolboxWindow()
    print("")
    print(f"注册的插件数量: {len(window.plugins)}")
    for name, plugin in window.plugins.items():
        if "Scaler" in name or "Scal" in name:
            print(f"  - {name}: {plugin.name}")
            try:
                ui = plugin.create_ui()
                print(f"    [OK] UI 创建成功: {type(ui).__name__}")
            except Exception as e:
                print(f"    [ERROR] UI 创建失败: {e}")
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    _run_smoke()
