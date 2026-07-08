# -*- encoding: utf-8 -*-
"""
pytest conftest — 共享 fixtures

在运行测试前需要先安装依赖：
    pip install pytest pytest-qt Pillow PyMuPDF
"""

import os
import sys
from pathlib import Path

# 将项目根目录添加到 sys.path，使各插件能正常 import
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


# ==================== 应用 fixture ====================


@pytest.fixture(scope="session")
def qapp():
    """会话级 QApplication，所有测试共用"""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ==================== 测试图片 fixture ====================


def _make_test_images(target_dir, count=5):
    """在 target_dir 中生成 count 张测试图片，返回文件路径列表"""
    images = []
    colors = [
        ("red", (255, 0, 0)),
        ("green", (0, 255, 0)),
        ("blue", (0, 0, 255)),
        ("yellow", (255, 255, 0)),
        ("cyan", (0, 255, 255)),
    ]
    for i in range(count):
        color_name, rgb = colors[i % len(colors)]
        w, h = 200 + i * 50, 150 + i * 30
        img = Image.new("RGB", (w, h), rgb)
        path = target_dir / f"test_{i+1}_{color_name}.png"
        img.save(path)
        images.append(str(path))
    return images


@pytest.fixture
def test_images(tmp_path):
    """生成 5 张测试图片，返回路径列表"""
    return _make_test_images(tmp_path, count=5)


@pytest.fixture
def few_test_images(tmp_path):
    """生成 2 张测试图片，用于快速测试"""
    return _make_test_images(tmp_path, count=2)


@pytest.fixture
def test_pdf(tmp_path):
    """生成一个测试 PDF 文件（需要 PyMuPDF）"""
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "Test PDF Page 1", fontsize=20)
        page2 = doc.new_page(width=595, height=842)
        page2.insert_text((72, 72), "Test PDF Page 2", fontsize=20)
        path = str(tmp_path / "test.pdf")
        doc.save(path)
        doc.close()
        return path
    except ImportError:
        pytest.skip("PyMuPDF not installed")


# ==================== 插件加载 fixture ====================


@pytest.fixture
def loaded_plugins(qapp):
    """返回所有已加载的插件字典 {name: plugin}"""
    from toolbox import ToolboxWindow

    window = ToolboxWindow()
    window.load_plugins()
    return window.plugins


# ==================== 输出目录 fixture ====================


@pytest.fixture
def output_dir(tmp_path):
    """返回一个干净的临时输出目录"""
    d = tmp_path / "output"
    d.mkdir(exist_ok=True)
    return str(d)