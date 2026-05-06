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
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

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

def main():
    print("="*60)
    print("工具箱应用自动化打包脚本")
    print("="*60)

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

    # 步骤 3: 清理旧文件
    print_step(3, "清理旧的打包文件")
    # dirs_to_clean = ['build', 'dist']
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

    # 检查 dist 目录
    dist_dir = Path('dist')
    if not dist_dir.exists():
        print("✗ dist 目录不存在")
        return 1

    # 查找可执行文件
    exe_files = list(dist_dir.glob('*.exe'))
    if not exe_files:
        print("✗ 未找到可执行文件")
        return 1

    exe_file = exe_files[0]
    file_size = exe_file.stat().st_size / (1024 * 1024)  # MB

    print(f"\n✓ 打包成功!")
    print(f"  可执行文件: {exe_file}")
    print(f"  文件大小: {file_size:.2f} MB")

    # 步骤 6: 转换并复制用户手册
    print_step(6, "转换用户手册为 DOCX")
    # 读取版本号，定义输出文件名
    import re
    version = "2.0.1"
    config_path = Path("config.py")
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8")
        match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
        if match:
            version = match.group(1)
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
    print(f"\n可执行文件位置: {exe_file.absolute()}")
    if docx_path.exists():
        print(f"用户手册: {docx_path}")
    print("\n测试建议:")
    print("  1. 运行应用，检查是否能正常启动")
    print("  2. 右键文件 → 属性 → 详细信息，查看版本信息")
    print("  3. 测试所有功能模块（图片压缩、PDF转换、格式转换、拼接、缩放、设置）")
    print("  4. 测试主题切换功能")
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
