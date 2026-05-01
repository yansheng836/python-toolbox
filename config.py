"""
工具箱应用配置文件
集中管理应用的全局配置信息
"""

# 应用基本信息
APP_NAME = "工具箱"
APP_VERSION = "1.0.2"
APP_DESCRIPTION = "批量处理工具，支持图片压缩、PDF转换、格式转换、拼接和PDF合并"
APP_COPYRIGHT = "© 2026 yansheng836"
APP_WEBSITE_URL = "https://github.com/yansheng836/python-toolbox"  # 官方网站URL
APP_WEBSITE_LINK_TEXT = "🌐 访问官方网站"

# 功能模块信息
FEATURE_MODULES = [
    ("🖼️", "图片压缩工具", "支持 JPG、PNG、WebP 格式，可批量处理并调整压缩质量"),
    ("📄", "图片转PDF工具", "将多张图片合并为一个PDF文件，支持拖拽排序"),
    ("🔄", "图片格式转换", "纯格式转换，保持原始质量，支持 JPEG / PNG / WebP / BMP / TIFF / GIF"),
    ("📐", "图片拼接", "多图合并，自由拼接，支持横向和纵向合并"),
    ("📏", "图片批量缩放", "批量缩放，精确控制，支持多种缩放模式"),
    ("📑", "PDF合并", "将多个PDF文件合并为一个，支持拖拽和顺序调整"),
    ("📐", "PDF拆分", "将PDF拆分为图片或单页PDF，支持设置拆分页数"),
]

# 欢迎页面配置
WELCOME_CONFIG = {
    "title": "工具箱",
    "subtitle": "高效、美观、可扩展的桌面工具集合",
    "hint": "👈 从左侧菜单选择工具开始使用",
    "feature_title": "功能特色",
}

# 全局标题样式配置
# UI间距配置
SPACING_SMALL = 8  # 小间距，用于标签和控件之间
SPACING_MEDIUM = 20  # 中间距，用于设置项之间

# UI配置
UI_CONFIG = {
    "window_title": f"工具箱 v{APP_VERSION}",
    # 窗口最小尺寸：像素值如 (1200, 800) 或百分比如 (0.7, 0.8) 表示70%宽、80%高
    "window_min_size": (0.7, 0.8),
    "window_max_size": None,  # None表示不限制，像素值如(1920, 1080)，百分比如(0.9, 0.9)
    "sidebar_width": 260,
    "card_corner_radius": 12,
    "input_corner_radius": 8,
    "button_corner_radius": 8,
}

# 字体大小配置
FONT_SIZE_12 = "12px"
FONT_SIZE_14 = "14px"
FONT_SIZE_16 = "16px"
FONT_SIZE_18 = "18px"
FONT_SIZE_20 = "20px"
FONT_SIZE_24 = "24px"

# 字体粗细配置
FONT_WEIGHT_600 = "600"
FONT_WEIGHT_700 = "700"
FONT_WEIGHT_800 = "800"

# 标题样式
TITLE_STYLES = {
    "font_size": FONT_SIZE_24,
    "font_weight": FONT_WEIGHT_700
}

# 主题配置（可以在运行时修改）
THEME_CONFIG = {
    "default_theme": "dark",  # 默认主题
    "primary_color": "#6366f1",
    "primary_hover": "#4f46e5",
}
