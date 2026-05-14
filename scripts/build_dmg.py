#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS .dmg 打包脚本
使用 hdiutil 将 .app 打包为 .dmg 格式
"""

import sys
import os
import subprocess
from pathlib import Path


def create_dmg_with_hdiutil(app_path: str, output_path: str):
    """使用 hdiutil 创建 .dmg（系统自带，稳定可靠）"""
    volname = os.path.basename(app_path).replace(".app", "")

    cmd = [
        "hdiutil", "create",
        "-volname", volname,
        "-srcfolder", app_path,
        "-ov",
        "-format", "UDZO",
        output_path,
    ]

    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"错误: {result.stderr}")
        return False
    return True


def main():
    print("=" * 60)
    print("macOS .dmg 打包脚本")
    print("=" * 60)

    dist_dir = Path("dist")
    dist_dir.mkdir(parents=True, exist_ok=True)

    app_files = list(dist_dir.glob("*.app"))
    if not app_files:
        print("错误: dist 目录中没有 .app 文件")
        return 1

    app_path = str(app_files[0])
    print(f"找到 .app: {app_path}")

    # 版本号从命令行参数获取（CI 中传递），否则从 config.py 读取
    version = sys.argv[1] if len(sys.argv) > 1 else ""
    if not version:
        config_path = Path("config.py")
        if config_path.exists():
            content = config_path.read_text(encoding="utf-8")
            import re
            match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
            if match:
                version = match.group(1)

    if not version:
        version = "0.0.0"

    dmg_name = f"工具箱-v{version}.dmg"
    output_path = str(dist_dir / dmg_name)
    print(f"输出: {output_path}")

    print("\n使用 hdiutil 创建 .dmg...")
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
