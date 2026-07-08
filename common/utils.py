# -*- encoding: utf-8 -*-
"""
工具函数模块
包含多个插件共用的辅助函数
"""

import os

# ==================== 模块可用性检查 ====================
try:
    from PIL import Image
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


def get_image_size(file_path):
    """获取图片尺寸文本"""
    if not PIL_AVAILABLE:
        return "N/A"
    try:
        with Image.open(file_path) as img:
            return f"{img.width} x {img.height}"
    except Exception as e:
        print(f"get_image_size error: {e}")
        return "读取失败"


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
        return "未知"


def get_create_time(file_path):
    """获取文件创建时间文本"""
    try:
        import time
        t = os.path.getctime(file_path)
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
    except OSError as e:
        print(f"get_create_time error: {e}")
        return "未知"


def get_modify_time(file_path):
    """获取文件修改时间文本"""
    try:
        import time
        t = os.path.getmtime(file_path)
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
    except OSError as e:
        print(f"get_modify_time error: {e}")
        return "未知"


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


# 图片类插件通用的表格列定义
IMAGE_COLUMNS = [
    ("文件名", lambda f: os.path.basename(f)),
    ("尺寸", get_image_size),
    ("大小", get_file_size)
]

# PDF类插件通用的表格列定义
PDF_COLUMNS = [
    ("文件名", lambda f: os.path.basename(f)),
    ("页数", get_pdf_pages),
    ("大小", get_file_size)
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
        return False, (
            f"输出目录被占用或无法写入：\n{dir_path}\n\n"
            f"请检查目录权限，或关闭可能占用该目录的程序。"
        )
    except Exception as e:
        return False, f"无法访问输出目录：{str(e)}"


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
        return False, (
            f"目标文件被占用，无法写入：\n{file_path}\n\n"
            f"请先关闭该文件（如在 WPS、Adobe Reader 等软件中打开），然后重试。"
        )
    except Exception as e:
        return False, f"无法访问目标文件：{str(e)}"


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
