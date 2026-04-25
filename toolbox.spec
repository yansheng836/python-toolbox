# -*- mode: python ; coding: utf-8 -*-
"""
工具箱 (Toolbox) PyInstaller 配置文件
用于打包 PyQt6 桌面应用程序

使用方法:
    pyinstaller toolbox.spec

特性:
    - 单文件可执行程序
    - 包含 plugins 目录和 config.py
    - 包含版本信息和应用元数据
    - 排除不必要的模块以减小体积
    - 支持 Windows 和 macOS
    - UPX 压缩启用
    - Strip 调试符号

优化说明:
    1. 排除了不需要的 GUI 框架（tkinter）
    2. 排除了测试框架和开发工具
    3. 排除了不需要的网络协议模块
    4. 排除了所有不需要的 PyQt6 模块（只保留 QtCore、QtGui、QtWidgets）
    5. 排除了科学计算库（numpy、pandas、matplotlib 等）
    6. 启用 strip 移除调试符号
    7. 启用 UPX 压缩（但排除关键 DLL 以避免启动问题）
    8. 优化级别设置为 2（最高）

    注意：保留了 PyInstaller 需要的核心模块（zipfile、inspect、io 等）

预期效果:
    - 原始大小: ~250MB
    - 优化后: ~80-100MB（减少约 60%）
    - 更保守的排除策略确保稳定性
"""

import sys
import os

# 从 config.py 导入应用信息
try:
    from config import APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_COPYRIGHT
except ImportError:
    APP_NAME = "工具箱"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "批量处理工具"
    APP_COPYRIGHT = "© 2026 yansheng836"

block_cipher = None

a = Analysis(
    ['main.py'],  # 主入口点改为 main.py
    pathex=[],
    binaries=[],
    datas=[
        ('config.py', '.'),
        ('toolbox.py', '.'),
        ('menu_system.py', '.'),
        ('settings_page.py', '.'),
        ('plugins', 'plugins'),
        ('favicon.ico', '.'),
    ],
    hiddenimports=[
        # 项目模块
        'toolbox',
        'config',
        'menu_system',
        'settings_page',

        # 插件模块（动态加载的插件必须明确指定）
        'plugins.image_scaler',

        # PIL/Pillow 核心模块
        'PIL',
        'PIL.Image',
        'PIL.ImageFilter',
        'PIL.ImageEnhance',
        'PIL.ImageDraw',
        'PIL.ImageFont',

        # PyQt6 核心模块（确保包含）
        'PyQt6.sip',

        # PDF 转换库
        'img2pdf',
        'fitz',  # PyMuPDF
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI 框架（不需要的）
        'tkinter',
        '_tkinter',

        # 测试框架
        'unittest',
        'test',
        'tests',
        'doctest',
        'pytest',

        # 开发工具
        'pydoc',
        'lib2to3',
        'distutils',
        'setuptools',
        'pip',
        'wheel',
        'pkg_resources',

        # 网络协议（不需要的）
        'ftplib',
        'telnetlib',
        'poplib',
        'imaplib',
        'smtplib',
        'xmlrpc',

        # 数据库
        'sqlite3',

        # 异步/并发（如果不需要）
        # 注意：某些库可能需要这些，谨慎排除
        # 'asyncio',
        # 'concurrent',
        # 'multiprocessing',

        # 科学计算库（项目不需要）
        'matplotlib',
        'pandas',
        'numpy',
        'scipy',
        'sklearn',
        'tensorflow',
        'torch',
        'keras',

        # PyQt6 不需要的模块
        'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.QtNetworkAuth',
        'PyQt6.QtSql',
        'PyQt6.QtTest',
        'PyQt6.QtXml',
        'PyQt6.QtXmlPatterns',
        'PyQt6.QtBluetooth',
        'PyQt6.QtPositioning',
        'PyQt6.QtQuick',
        'PyQt6.QtQuickWidgets',
        'PyQt6.QtQml',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtWebChannel',
        'PyQt6.QtWebSockets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtDBus',
        'PyQt6.QtDesigner',
        'PyQt6.QtHelp',
        'PyQt6.QtNfc',
        'PyQt6.QtRemoteObjects',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'PyQt6.Qt3DCore',
        'PyQt6.Qt3DRender',
        'PyQt6.Qt3DInput',
        'PyQt6.Qt3DLogic',
        'PyQt6.Qt3DAnimation',
        'PyQt6.Qt3DExtras',
        'PyQt6.QtCharts',
        'PyQt6.QtDataVisualization',
    ],
    optimize=2,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,           # 使用 config.py 中的应用名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,              # 启用 strip 以移除调试符号
    upx=True,                # 启用 UPX 压缩
    upx_exclude=[
        'vcruntime140.dll',  # Windows 运行时库不压缩
        'python*.dll',       # Python DLL 不压缩
        'Qt6Core.dll',       # Qt 核心库不压缩（避免启动问题）
        'Qt6Gui.dll',
        'Qt6Widgets.dll',
    ],
    runtime_tmpdir=None,
    console=False,           # GUI 模式
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='favicon.ico',      # Windows 图标
    version='version_info.txt',  # 版本信息文件
)

# macOS 特定配置
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name=f'{APP_NAME}.app',
        icon='icon.icns',
        bundle_identifier='com.yansheng836.toolbox',
        info_plist={
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleVersion': APP_VERSION,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleName': APP_NAME,
            'CFBundleGetInfoString': APP_DESCRIPTION,
            'NSHumanReadableCopyright': APP_COPYRIGHT,
            'LSMinimumSystemVersion': '10.14',
            'NSHighResolutionCapable': 'True',
        },
    )