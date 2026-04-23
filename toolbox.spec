# -*- mode: python ; coding: utf-8 -*-

import sys
import os

block_cipher = None

a = Analysis(
    ['toolbox.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('plugins', 'plugins'),
    ],
    hiddenimports=[
        'PIL',
        'PIL._imagingtk',
        'PIL._tkinter_finder',
        'PyQt6.sip',
        'img2pdf',
        'fitz',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pandas',
        'numpy',
        'scipy',
        'unittest',
        'email',
        'http.server',
        'xmlrpc',
        'pydoc',
        'lib2to3',
        'distutils',
        'setuptools',
        'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.QtSql',
        'PyQt6.QtTest',
        'PyQt6.QtXml',
        'PyQt6.QtXmlPatterns',
        'PyQt6.QtBluetooth',
        'PyQt6.QtPositioning',
        'PyQt6.QtQuick',
        'PyQt6.QtQml',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtWebChannel',
        'PyQt6.QtWebSockets',
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
    name='Toolbox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI 模式
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Windows 图标
)

# macOS 特定配置
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='Toolbox.app',
        icon='assets/icon.icns',
        bundle_identifier='com.yourcompany.toolbox',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'LSMinimumSystemVersion': '10.14',
            'NSHighResolutionCapable': 'True',
        },
    )