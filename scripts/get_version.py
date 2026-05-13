#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""获取应用版本信息并写入 GITHUB_OUTPUT"""

import re
import sys
from pathlib import Path


def get_version_info(output_fields):
    """从 config.py 读取应用信息并写入 GITHUB_OUTPUT"""
    config_path = Path("config.py")
    if not config_path.exists():
        print("Error: config.py not found", file=sys.stderr)
        sys.exit(1)

    content = config_path.read_text(encoding="utf-8")

    pattern = re.compile(r'(APP_VERSION|APP_NAME|APP_DESCRIPTION)\s*=\s*"([^"]+)"')
    info = {}
    for match in pattern.finditer(content):
        info[match.group(1)] = match.group(2)

    app_name = info.get("APP_NAME", "工具箱")
    version = info.get("APP_VERSION", "0.0.0")
    description = info.get("APP_DESCRIPTION", "")

    output_path = Path(os.environ.get("GITHUB_OUTPUT", ""))
    if not output_path:
        print("Error: GITHUB_OUTPUT not set", file=sys.stderr)
        sys.exit(1)

    with open(output_path, "a", encoding="utf-8") as out:
        if "version" in output_fields:
            print(f"version={version}", file=out)
        if "app_name" in output_fields:
            print(f"app_name={app_name}", file=out)
        if "exe_name" in output_fields:
            exe_name = f"{app_name}ToolBox-v{version}.exe"
            print(f"exe_name={exe_name}", file=out)
        if "docx_name" in output_fields:
            # 输出纯 ASCII 格式，中文在调用处拼接
            print(f"docx_name=manual-{version}.docx", file=out)
        if "description" in output_fields:
            print(f"description={description}", file=out)

    print(f"Version info written: version={version}, app_name={app_name}")


if __name__ == "__main__":
    import os
    fields = sys.argv[1:] if len(sys.argv) > 1 else ["version", "app_name"]
    get_version_info(fields)
