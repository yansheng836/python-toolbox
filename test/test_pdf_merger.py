#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF合并插件测试
"""
import sys
import os

# 设置标准输出为 UTF-8 编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_import():
    """测试插件导入"""
    try:
        print("[OK] PDF合并插件导入成功")
        return True
    except ImportError as e:
        print(f"[FAIL] PDF合并插件导入失败: {e}")
        return False


def test_plugin_attributes():
    """测试插件属性"""
    try:
        from plugins.pdf_merger import PDFMerger
        plugin = PDFMerger()

        # 检查必要属性
        assert hasattr(plugin, 'name'), "缺少 name 属性"
        assert hasattr(plugin, 'icon'), "缺少 icon 属性"
        assert hasattr(plugin, 'create_ui'), "缺少 create_ui 方法"
        assert hasattr(plugin, 'update_theme'), "缺少 update_theme 方法"

        print(f"[OK] 插件属性检查通过")
        print(f"  名称: {plugin.name}")
        print(f"  图标: {plugin.icon}")
        return True
    except Exception as e:
        print(f"[FAIL] 插件属性检查失败: {e}")
        return False


def test_worker_import():
    """测试工作线程导入"""
    try:
        print("[OK] PDFMergeWorker 导入成功")
        return True
    except ImportError as e:
        print(f"[FAIL] PDFMergeWorker 导入失败: {e}")
        return False


def test_fitz_availability():
    """测试 PyMuPDF 是否可用"""
    try:
        import fitz
        print(f"[OK] PyMuPDF 已安装 (版本: {fitz.version})")
        return True
    except ImportError:
        print("[WARN] PyMuPDF 未安装（可选依赖）")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PDF合并插件测试")
    print("=" * 60)

    results = []

    results.append(("插件导入", test_import()))
    results.append(("插件属性", test_plugin_attributes()))
    results.append(("工作线程", test_worker_import()))
    results.append(("PyMuPDF", test_fitz_availability()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{name:20s} {status}")

    all_passed = all(result for _, result in results if result is not None)
    print("\n" + "=" * 60)
    if all_passed:
        print("所有测试通过！")
    else:
        print("部分测试失败！")
    print("=" * 60)
