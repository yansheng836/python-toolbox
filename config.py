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

# 功能模块信息（插件配置，单一数据源）
# 首页展示和插件加载均从此配置读取，避免维护多份
# order: 排序权重，数值越小排在越前面
PLUGIN_MODULES = [
    {
        "name": "图片压缩",
        "icon": "🗜️",
        "description": "批量压缩JPG/PNG/WebP图片，可调整质量以减小文件体积",
        "order": 5,
        "module": "plugins.image_compressor",
        "class": "ImageCompressor",
    },
    {
        "name": "图片格式转换",
        "icon": "🔁",
        "description": "批量转换图片格式，支持JPEG/PNG/WebP/BMP/TIFF/GIF",
        "order": 10,
        "module": "plugins.image_format_converter",
        "class": "FormatConverter",
    },
    {
        "name": "图片拼接",
        "icon": "🧩",
        "description": "多张图片横向或纵向拼接合并为一张，支持自定义对齐",
        "order": 15,
        "module": "plugins.image_stitcher",
        "class": "ImageStitcher",
    },
    {
        "name": "图片转PDF",
        "icon": "🖨️",
        "description": "将多张图片合并为一个PDF文件，支持拖拽排序",
        "order": 20,
        "module": "plugins.image_to_pdf",
        "class": "ImageToPDF",
    },
    {
        "name": "图片缩放",
        "icon": "🔍",
        "description": "批量缩放图片尺寸，支持按比例或指定宽高，保持画质",
        "order": 25,
        "module": "plugins.image_scaler",
        "class": "ImageScaler",
    },
    {
        "name": "PDF合并",
        "icon": "📚",
        "description": "将多个PDF文件合并为一个，支持拖拽排序和调整顺序",
        "order": 100,
        "module": "plugins.pdf_merger",
        "class": "PDFMerger",
    },
    {
        "name": "PDF拆分",
        "icon": "✂️",
        "description": "将PDF拆分为图片或单页PDF文件，支持自定义页数",
        "order": 105,
        "module": "plugins.pdf_splitter",
        "class": "PDFSplitter",
    },
    {
        "name": "文件去重",
        "icon": "🧹",
        "description": "按内容Hash查找重复文件，预览后按需删除释放空间",
        "order": 200,
        "module": "plugins.file_deduplicator",
        "class": "FileDeduplicator",
    },
    # 设置插件（内置，在 toolbox.py 中定义）
    {
        "name": "设置",
        "icon": "⚙️",
        "description": "切换深浅主题、查看版本和关于信息",
        "order": 999,
        "module": "toolbox",
        "class": "SettingsPlugin",
    },
]

# 兼容旧代码：FEATURE_MODULES 从 PLUGIN_MODULES 派生，排除设置插件（不显示在首页）
FEATURE_MODULES = [
    (p["icon"], p["name"], p["description"])
    for p in PLUGIN_MODULES if p["order"] < 999
]

# 欢迎页面配置
WELCOME_CONFIG = {
    "title": "工具箱",
    "subtitle": "离线、高效、美观的桌面工具集合",
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
