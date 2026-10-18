# -*- encoding: utf-8 -*-
"""
工具函数模块
包含多个插件共用的辅助函数
"""

import os
from collections import namedtuple

from common.i18n import t

# ==================== 模块可用性检查 ====================
try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError as e:
    print(f"Warning: {e}")
    PIL_AVAILABLE = False

try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError as e:
    print(f"Warning: {e}")
    FITZ_AVAILABLE = False

try:
    import img2pdf
    IMG2PDF_AVAILABLE = True
except ImportError as e:
    print(f"Warning: {e}")
    IMG2PDF_AVAILABLE = False
    img2pdf = None


def load_oriented_image(file_path):
    """读取图片并返回应用 EXIF 方向后的独立图像副本"""
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is not installed")
    with Image.open(file_path) as src_img:
        src_img.load()
        oriented_img = ImageOps.exif_transpose(src_img)
        try:
            return oriented_img.copy()
        finally:
            oriented_img.close()


def get_image_size(file_path):
    """获取图片尺寸文本（应用 EXIF 方向）"""
    if not PIL_AVAILABLE:
        return "N/A"
    try:
        with load_oriented_image(file_path) as img:
            return f"{img.width} x {img.height}"
    except Exception as e:
        print(f"get_image_size error: {e}")
        return t("common.cell.read_failed")


def get_file_size(file_path):
    """获取文件大小文本"""
    try:
        size = os.path.getsize(file_path)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    except OSError as e:
        print(f"get_file_size error: {e}")
        return t("common.cell.unknown")


def get_create_time(file_path):
    """获取文件创建时间文本"""
    try:
        import time
        stamp = os.path.getctime(file_path)
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stamp))
    except OSError as e:
        print(f"get_create_time error: {e}")
        return t("common.cell.unknown")


def get_modify_time(file_path):
    """获取文件修改时间文本"""
    try:
        import time
        stamp = os.path.getmtime(file_path)
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stamp))
    except OSError as e:
        print(f"get_modify_time error: {e}")
        return t("common.cell.unknown")


def get_pdf_pages(file_path):
    """获取PDF页数"""
    if not FITZ_AVAILABLE:
        return "N/A"
    try:
        doc = fitz.open(file_path)
        pages = len(doc)
        doc.close()
        return str(pages)
    except Exception as e:
        print(f"get_pdf_pages error: {e}")
        return "N/A"


# 列定义：id 为稳定标识（列宽/排序按 id 匹配），label 为显示文本（i18n 时翻译），func 为取值函数
Column = namedtuple("Column", "id label func")

# 图片类插件通用的表格列定义
IMAGE_COLUMNS = [
    Column("filename", "文件名", lambda f: os.path.basename(f)),
    Column("dimensions", "尺寸", get_image_size),
    Column("size", "大小", get_file_size),
]

# PDF类插件通用的表格列定义
PDF_COLUMNS = [
    Column("filename", "文件名", lambda f: os.path.basename(f)),
    Column("pages", "页数", get_pdf_pages),
    Column("size", "大小", get_file_size),
]


# ==================== Windows 保留设备名称 ====================
# 打开这些名称的文件会导致 open() 无限阻塞或行为异常
WINDOWS_RESERVED_NAMES = frozenset({
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
})


def is_reserved_filename(filename):
    """检查文件名（不含路径）是否为 Windows 保留设备名称"""
    name_without_ext = os.path.splitext(filename)[0].upper()
    return name_without_ext in WINDOWS_RESERVED_NAMES


def check_dir_writable(dir_path):
    """检查目录是否可写

    尝试在目录中创建临时文件来验证可写性。
    返回 (is_writable: bool, error_message: str)
    """
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        test_file = os.path.join(dir_path, ".write_test.tmp")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        return True, ""
    except PermissionError:
        return False, t("common.error.dir_locked", dir=dir_path)
    except Exception as e:
        return False, t("common.error.dir_access", error=str(e))


def check_file_writable(file_path):
    """检查文件是否可写入（未被其他程序锁定）

    尝试以追加模式打开文件来验证可写性。
    返回 (is_writable: bool, error_message: str)
    """
    try:
        with open(file_path, 'ab') as _:
            pass
        return True, ""
    except PermissionError:
        return False, t("common.error.file_locked", path=file_path)
    except Exception as e:
        return False, t("common.error.file_access", error=str(e))


# ==================== 主题样式生成器 ====================
# 这些函数生成 PyQt6 控件的主题化 stylesheet 字符串
# 注意：theme 参数应为 Theme.DARK 或 Theme.LIGHT 字典


def get_combo_style(theme):
    """生成 QComboBox 的主题样式表"""
    return f"""
        QComboBox {{
            background-color: {theme['bg']};
            border: 1px solid {theme['surface']};
            border-radius: 6px;
            padding: 6px;
            color: {theme['text']};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme['bg_secondary']};
            color: {theme['text']};
            selection-background-color: {theme['primary']};
            selection-color: {theme['text']};
            padding: 4px;
            border: none;
        }}
    """


def get_lineedit_style(theme):
    """生成 QLineEdit 的主题样式表"""
    return f"""
        QLineEdit {{
            background-color: {theme['bg']};
            border: 1px solid {theme['surface']};
            border-radius: 6px;
            padding: 6px;
            color: {theme['text']};
        }}
    """


def get_spinbox_style(theme):
    """生成 QSpinBox 的主题样式表"""
    return f"""
        QSpinBox {{
            background-color: {theme['bg']};
            border: 1px solid {theme['surface']};
            border-radius: 6px;
            padding: 4px;
            color: {theme['text']};
            text-align: left;
        }}
    """
