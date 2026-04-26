#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证打包后的应用是否包含所有必需的模块
在打包前运行此脚本以确保所有依赖都能被正确导入
"""

import sys
import importlib
import io

# 设置标准输出为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_imports():
    """测试所有关键模块是否可以导入"""
    modules_to_test = [
        # 核心模块
        ('toolbox', '主应用模块'),
        ('config', '配置模块'),

        # 插件模块
        ('plugins.image_scaler', '图片批量缩放插件'),
        ('plugins.pdf_merger', 'PDF合并插件'),
        ('plugins.file_deduplicator', '文件去重插件'),

        # 依赖库
        ('PIL', 'Pillow 图像处理库'),
        ('PIL.Image', 'PIL.Image'),
        ('PyQt6.QtWidgets', 'PyQt6 GUI'),
        ('PyQt6.QtCore', 'PyQt6 核心'),
        ('PyQt6.QtGui', 'PyQt6 GUI 组件'),
    ]

    # 可选依赖
    optional_modules = [
        ('img2pdf', 'img2pdf PDF转换库'),
        ('fitz', 'PyMuPDF PDF转换库'),
    ]

    print("=" * 60)
    print("验证打包依赖 - 必需模块")
    print("=" * 60)

    all_passed = True

    for module_name, description in modules_to_test:
        try:
            importlib.import_module(module_name)
            print(f"✓ {description:30s} [{module_name}]")
        except ImportError as e:
            print(f"✗ {description:30s} [{module_name}]")
            print(f"  错误: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    print("验证打包依赖 - 可选模块")
    print("=" * 60)

    for module_name, description in optional_modules:
        try:
            importlib.import_module(module_name)
            print(f"✓ {description:30s} [{module_name}]")
        except ImportError:
            print(f"○ {description:30s} [{module_name}] (未安装)")

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有必需模块验证通过！可以进行打包。")
    else:
        print("✗ 部分模块验证失败！请检查依赖安装。")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
