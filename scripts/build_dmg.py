#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS .dmg 打包脚本
将 .app 打包为 .dmg 格式（带拖拽安装界面）
"""

import sys
import os
import subprocess
from pathlib import Path


def create_dmg_with_create_dmg(app_path: str, output_path: str, app_name: str):
    """使用 create-dmg 创建带拖拽界面的 .dmg"""
    # 获取 app 文件名
    app_filename = os.path.basename(app_path)
    # 去掉 .app 后缀
    app_name_short = app_filename.replace(".app", "")

    cmd = [
        "create-dmg",
        "--window-size", "600", "400",
        "--icon-size", "100",
        "--app-drop-link", "450", "185",
        output_path,
        app_path,
    ]

    print(f"执行: create-dmg {app_filename} -> {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"错误: {result.stderr}")
        return False
    return True


def create_dmg_with_hdiutil(app_path: str, output_path: str):
    """使用 hdiutil 创建 .dmg（系统自带）"""
    volname = os.path.basename(app_path).replace(".app", "")
    dmg_temp = output_path.replace(".dmg", "_temp.dmg")

    # 创建临时 .dmg
    cmd = [
        "hdiutil", "create",
        "-volname", volname,
        "-srcfolder", app_path,
        "-ov",
        "-format", "UDZO",
        dmg_temp,
    ]

    print(f"执行: hdiutil create {volname} -> {dmg_temp}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"错误: {result.stderr}")
        return False

    # 重命名
    if os.path.exists(output_path):
        os.remove(output_path)
    os.rename(dmg_temp, output_path)
    return True


def main():
    print("=" * 60)
    print("macOS .dmg 打包脚本")
    print("=" * 60)

    # 查找 .app 文件
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("错误: dist 目录不存在")
        return 1

    app_files = list(dist_dir.glob("*.app"))
    if not app_files:
        print("错误: dist 目录中没有 .app 文件")
        print("请先运行 build_macos.py 生成 .app")
        return 1

    app_path = str(app_files[0])
    print(f"找到 .app: {app_path}")

    # 从 config.py 读取版本号
    config_path = Path("config.py")
    version = "0.0.0"
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8")
        import re
        match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
        if match:
            version = match.group(1)

    output_path = str(dist_dir / f"工具箱-v{version}.dmg")
    print(f"输出: {output_path}")

    # 尝试使用 create-dmg（需要安装）
    create_dmg_result = subprocess.run(
        ["which", "create-dmg"],
        capture_output=True,
    )

    if create_dmg_result.returncode == 0:
        print("\n使用 create-dmg 创建 .dmg...")
        success = create_dmg_with_create_dmg(app_path, output_path, "工具箱")
    else:
        print("\ncreate-dmg 未安装，使用 hdiutil 创建 .dmg...")
        print("提示: npm install -g create-dmg 可安装更美观的打包工具")
        success = create_dmg_with_hdiutil(app_path, output_path)

    if success:
        print(f"\n✓ .dmg 创建成功!")
        print(f"  文件: {output_path}")
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  大小: {file_size:.2f} MB")
    else:
        print("\n✗ .dmg 创建失败")
        return 1

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
