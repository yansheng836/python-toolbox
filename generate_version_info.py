#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动从 config.py 生成 PyInstaller 版本信息文件
"""

import sys
import os
import io

# 设置标准输出为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_COPYRIGHT
except ImportError:
    print("错误: 无法导入 config.py")
    sys.exit(1)

# 解析版本号
version_parts = APP_VERSION.split('.')
while len(version_parts) < 4:
    version_parts.append('0')
version_tuple = ', '.join(version_parts[:4])

# 提取公司名称（从版权信息中）
company_name = APP_COPYRIGHT.replace('©', '').replace('(c)', '').strip()
if ' ' in company_name:
    # 移除年份，只保留公司名
    parts = company_name.split()
    company_name = ' '.join([p for p in parts if not p.isdigit()])

# 生成版本信息文件内容
version_info_content = f"""# UTF-8
#
# 用于 PyInstaller 的版本信息文件
# 自动从 config.py 生成
#
# 应用名称: {APP_NAME}
# 版本: {APP_VERSION}
# 描述: {APP_DESCRIPTION}
# 版权: {APP_COPYRIGHT}
#

VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers 和 prodvers 应该是四个整数的元组
    filevers=({version_tuple}),
    prodvers=({version_tuple}),
    # 包含 VS_FF_DEBUG, VS_FF_PRERELEASE, VS_FF_PATCHED, VS_FF_PRIVATEBUILD, VS_FF_INFOINFERRED, VS_FF_SPECIALBUILD 等标志
    mask=0x3f,
    flags=0x0,
    # 操作系统类型 (VOS_NT_WINDOWS32)
    OS=0x40004,
    # 文件类型 (VFT_APP)
    fileType=0x1,
    # 文件子类型
    subtype=0x0,
    # 文件日期
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'080404b0',  # 中文(中国) + Unicode
        [StringStruct(u'CompanyName', u'{company_name}'),
        StringStruct(u'FileDescription', u'{APP_DESCRIPTION}'),
        StringStruct(u'FileVersion', u'{APP_VERSION}.0'),
        StringStruct(u'InternalName', u'{APP_NAME}'),
        StringStruct(u'LegalCopyright', u'{APP_COPYRIGHT}'),
        StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
        StringStruct(u'ProductName', u'{APP_NAME}'),
        StringStruct(u'ProductVersion', u'{APP_VERSION}.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])  # 中文(中国)
  ]
)
"""

# 写入文件
output_file = 'version_info.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(version_info_content)

print(f"✓ 版本信息文件已生成: {output_file}")
print(f"  应用名称: {APP_NAME}")
print(f"  版本号: {APP_VERSION}")
print(f"  描述: {APP_DESCRIPTION}")
print(f"  版权: {APP_COPYRIGHT}")
