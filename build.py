#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化打包脚本
执行完整的打包流程：验证依赖 → 生成版本信息 → 清理旧文件 → 打包
"""

import sys
import os
import io
import subprocess
import shutil
from pathlib import Path

# 设置标准输出为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def print_step(step_num, title):
    """打印步骤标题"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {title}")
    print('='*60)

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n执行: {description}")
    print(f"命令: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

    if result.returncode == 0:
        print(f"✓ {description} 成功")
        if result.stdout:
            print(result.stdout)
        return True
    else:
        print(f"✗ {description} 失败")
        if result.stderr:
            print(f"错误信息:\n{result.stderr}")
        return False

def get_app_info():
    """从 config.py 读取应用信息"""
    import re
    config_path = Path("config.py")
    defaults = {
        "APP_NAME": "工具箱",
        "APP_VERSION": "2.0.1",
        "APP_DESCRIPTION": "批量处理工具",
        "APP_COPYRIGHT": "© 2026 yansheng836",
    }
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8")
        for key in defaults:
            match = re.search(rf'{key}\s*=\s*"([^"]+)"', content)
            if match:
                defaults[key] = match.group(1)
    return defaults


def main():
    print("="*60)
    print("工具箱应用自动化打包脚本")
    print("="*60)

    # 读取应用信息（供后续步骤使用）
    app_info = get_app_info()
    app_name = app_info["APP_NAME"]
    version = app_info["APP_VERSION"]
    exe_name = f"{app_name}ToolBox-v{version}.exe"
    exe_path = Path("dist") / exe_name

    # 步骤 1: 生成版本信息
    print_step(1, "生成版本信息文件")
    if not run_command("python generate_version_info.py", "生成版本信息"):
        print("\n警告: 版本信息生成失败，将使用现有的 version_info.txt")

    # 步骤 2: 验证依赖
    print_step(2, "验证打包依赖")
    if not run_command("python verify_packaging.py", "验证依赖"):
        print("\n错误: 依赖验证失败，请检查缺失的模块")
        response = input("\n是否继续打包? (y/N): ")
        if response.lower() != 'y':
            print("打包已取消")
            return 1

    # 步骤 3: 清理旧文件（仅清理 build，保留 dist 中的历史版本）
    print_step(3, "清理旧的打包文件")
    dirs_to_clean = ['build']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"删除目录: {dir_name}")
            shutil.rmtree(dir_name)
            print(f"✓ {dir_name} 已删除")
        else:
            print(f"○ {dir_name} 不存在，跳过")

    # 步骤 4: 执行打包
    print_step(4, "执行 PyInstaller 打包")
    if not run_command("pyinstaller toolbox.spec", "PyInstaller 打包"):
        print("\n错误: 打包失败")
        return 1

    # 步骤 5: 验证打包结果
    print_step(5, "验证打包结果")

    if not exe_path.exists():
        print(f"✗ 未找到目标可执行文件: {exe_name}")
        # 列出 dist 目录中的所有 exe 文件供参考
        dist_dir = Path('dist')
        if dist_dir.exists():
            exe_files = list(dist_dir.glob('*.exe'))
            if exe_files:
                print(f"\ndist 目录中现有的 exe 文件:")
                for f in exe_files:
                    print(f"  - {f.name}")
        return 1

    file_size = exe_path.stat().st_size / (1024 * 1024)  # MB

    print(f"\n✓ 打包成功!")
    print(f"  可执行文件: {exe_path}")
    print(f"  文件大小: {file_size:.2f} MB")

    # 步骤 6: 转换并复制用户手册
    print_step(6, "转换用户手册为 DOCX")
    docx_name = f"用户手册-{version}.docx"
    docx_path = Path("dist") / docx_name

    try:
        # 使用 pandoc 转换
        pandoc_cmd = f'pandoc "用户手册.md" -o "{docx_path}"'
        if run_command(pandoc_cmd, f"转换用户手册为 {docx_name}"):
            print(f"✓ 用户手册已保存到: {docx_path}")
        else:
            print(f"⚠ 警告: pandoc 转换失败，跳过此步骤（请确保已安装 pandoc）")
    except Exception as e:
        print(f"⚠ 警告: 转换用户手册时出错: {e}")

    # 步骤 7: 打包完成提示
    print_step(7, "打包完成提示")
    print("\n" + "="*60)
    print("打包完成!")
    print("="*60)
    print(f"\n可执行文件位置: {exe_path.absolute()}")
    if docx_path.exists():
        print(f"用户手册: {docx_path}")
    print("\n测试建议:")
    print("  1. 运行应用，检查是否能正常启动")
    print("  2. 右键文件 → 属性 → 详细信息，查看版本信息")
    print("  3. 测试所有功能模块:")
    print("     - 图片压缩（质量调节、输出格式）")
    print("     - 图片格式转换（JPEG/PNG/WebP/BMP/TIFF/GIF）")
    print("     - 图片拼接（横向/纵向合并、对齐方式）")
    print("     - 图片转PDF（拖拽排序、压缩选项）")
    print("     - 图片缩放（按宽度/高度/百分比）")
    print("     - PDF合并（多文件合并、拖拽排序）")
    print("     - PDF拆分（按页拆分、输出为图片或PDF）")
    print("     - 文件去重（哈希扫描、删除规则）")
    print("  4. 测试主题切换功能（深色/浅色模式）")
    print("  5. 测试窗口响应式布局（正常/最大化/全屏）")
    print("\n" + "="*60)

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n打包已被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
