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
