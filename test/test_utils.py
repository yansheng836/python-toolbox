# -*- encoding: utf-8 -*-
"""
测试 common/utils.py 中的共享工具函数
"""

import os
import tempfile
import pytest

from common.utils import (
    WINDOWS_RESERVED_NAMES,
    is_reserved_filename,
    check_dir_writable,
    check_file_writable,
    get_combo_style,
    get_lineedit_style,
    get_spinbox_style,
    get_file_size,
    IMAGE_COLUMNS,
    PDF_COLUMNS,
)


class TestWindowsReservedNames:
    """测试 Windows 保留设备名称"""

    def test_contains_standard_names(self):
        assert "CON" in WINDOWS_RESERVED_NAMES
        assert "PRN" in WINDOWS_RESERVED_NAMES
        assert "AUX" in WINDOWS_RESERVED_NAMES
        assert "NUL" in WINDOWS_RESERVED_NAMES
        assert "COM1" in WINDOWS_RESERVED_NAMES
        assert "COM9" in WINDOWS_RESERVED_NAMES
        assert "LPT1" in WINDOWS_RESERVED_NAMES
        assert "LPT9" in WINDOWS_RESERVED_NAMES

    def test_not_contains_normal_names(self):
        assert "README" not in WINDOWS_RESERVED_NAMES
        assert "main" not in WINDOWS_RESERVED_NAMES

    def test_com10_not_included(self):
        assert "COM10" not in WINDOWS_RESERVED_NAMES


class TestIsReservedFilename:
    """测试 is_reserved_filename 函数"""

    def test_reserved_name_detected(self):
        assert is_reserved_filename("con.log")
        assert is_reserved_filename("NUL.txt")
        assert is_reserved_filename("COM1.jpg")
        assert is_reserved_filename("LPT3.pdf")

    def test_normal_names_not_detected(self):
        assert not is_reserved_filename("readme.txt")
        assert not is_reserved_filename("image.jpg")
        assert not is_reserved_filename("CONFIG.py")

    def test_empty_filename(self):
        # 空文件名的 basename 是空字符串，不在保留列表中
        assert not is_reserved_filename("")


class TestCheckDirWritable:
    """测试目录可写性检查"""

    def test_writable_dir(self, tmp_path):
        writable, msg = check_dir_writable(str(tmp_path))
        assert writable is True
        assert msg == ""

    def test_writable_new_dir(self, tmp_path):
        new_dir = str(tmp_path / "new_folder")
        writable, msg = check_dir_writable(new_dir)
        assert writable is True
        assert msg == ""
        assert os.path.exists(new_dir)

    def test_non_existent_parent(self, tmp_path):
        # 检查不存在的路径（check_dir_writable 内部会 makedirs）
        new_dir = str(tmp_path / "a" / "b" / "c")
        writable, msg = check_dir_writable(new_dir)
        assert writable is True  # makedirs(exist_ok=True) 会创建
        assert os.path.exists(new_dir)


class TestCheckFileWritable:
    """测试文件可写性检查"""

    def test_new_file(self, tmp_path):
        path = str(tmp_path / "new.txt")
        writable, msg = check_file_writable(path)
        assert writable is True
        assert msg == ""

    def test_existing_file(self, tmp_path):
        path = str(tmp_path / "existing.txt")
        with open(path, "w") as f:
            f.write("hello")
        writable, msg = check_file_writable(path)
        assert writable is True
        assert msg == ""


class TestStyleGenerators:
    """测试主题样式生成器"""

    DARK_THEME = {
        "bg": "#0f172a",
        "bg_secondary": "#1e293b",
        "surface": "#334155",
        "text": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "primary": "#6366f1",
    }

    def test_get_combo_style_contains_keys(self):
        style = get_combo_style(self.DARK_THEME)
        assert "#0f172a" in style  # bg
        assert "#334155" in style  # surface
        assert "#f1f5f9" in style  # text
        assert "QComboBox" in style
        assert "QAbstractItemView" in style

    def test_get_lineedit_style_contains_keys(self):
        style = get_lineedit_style(self.DARK_THEME)
        assert "#0f172a" in style  # bg
        assert "#334155" in style  # surface
        assert "QLineEdit" in style

    def test_get_spinbox_style_contains_keys(self):
        style = get_spinbox_style(self.DARK_THEME)
        assert "#0f172a" in style  # bg
        assert "#334155" in style  # surface
        assert "QSpinBox" in style


class TestFileSize:
    """测试文件大小格式化"""

    def test_get_file_size_small(self, tmp_path):
        path = str(tmp_path / "small.txt")
        with open(path, "w") as f:
            f.write("hello")
        size = get_file_size(path)
        assert "B" in size

    def test_get_file_size_large_mock(self, tmp_path):
        path = str(tmp_path / "large.txt")
        size_bytes = 2 * 1024 * 1024  # 2 MB
        with open(path, "wb") as f:
            f.write(b"x" * size_bytes)
        size = get_file_size(path)
        assert "MB" in size or "B" in size


class TestTableColumns:
    """测试表格列定义"""

    def test_image_columns_structure(self):
        assert len(IMAGE_COLUMNS) >= 3
        names = [col[0] for col in IMAGE_COLUMNS]
        assert "文件名" in names
        assert "尺寸" in names
        assert "大小" in names

    def test_pdf_columns_structure(self):
        assert len(PDF_COLUMNS) >= 3
        names = [col[0] for col in PDF_COLUMNS]
        assert "文件名" in names
        assert "页数" in names
        assert "大小" in names