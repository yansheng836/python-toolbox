#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Release Notes：基于当前标签与上一个标签之间的提交记录"""

import subprocess
import sys
import os
from pathlib import Path


def get_previous_tag(current_tag: str) -> str | None:
    """获取当前标签之前的上一个标签"""
    try:
        result = subprocess.run(
            ["git", "tag", "--sort=-creatordate"],
            capture_output=True,
            text=True,
            check=True,
        )
        tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
        if current_tag in tags:
            idx = tags.index(current_tag)
            if idx + 1 < len(tags):
                return tags[idx + 1]
        return None
    except Exception:
        return None


def get_commit_log(from_tag: str | None, to_tag: str) -> str:
    """获取两个标签之间的提交日志"""
    if from_tag:
        range_spec = f"{from_tag}..{to_tag}"
    else:
        range_spec = to_tag

    result = subprocess.run(
        ["git", "log", range_spec, "--pretty=format:%h|%s|%b"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return ""

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 2)
        sha = parts[0][:7]
        subject = parts[1] if len(parts) > 1 else ""
        body = parts[2] if len(parts) > 2 else ""

        # 解析 conventional commit 类型
        commit_type = ""
        if subject.startswith(("feat", "fix", "refactor", "docs", "test", "chore", "perf", "ci")):
            commit_type = subject.split(":")[0]
            subject = subject.split(":", 1)[1].strip() if ":" in subject else subject

        # 分类整理
        commits.append({
            "sha": sha,
            "type": commit_type,
            "subject": subject,
            "body": body.strip(),
        })

    return commits


def categorize_commits(commits: list) -> dict:
    """将提交按类型分类"""
    categories = {
        "feat": {"title": "✨ 新功能", "items": []},
        "fix": {"title": "🐛 Bug 修复", "items": []},
        "refactor": {"title": "🔧 代码重构", "items": []},
        "docs": {"title": "📝 文档更新", "items": []},
        "test": {"title": "🧪 测试相关", "items": []},
        "perf": {"title": "⚡ 性能优化", "items": []},
        "ci": {"title": "🤖 CI/CD", "items": []},
        "chore": {"title": "📦 其他变更", "items": []},
    }

    for c in commits:
        cat_key = c["type"] if c["type"] in categories else "chore"
        item_text = c["subject"]
        if c["body"]:
            item_text += f"\n  > {c['body']}"
        categories[cat_key]["items"].append(item_text)

    return categories


def generate_release_notes(current_tag: str) -> str:
    """生成完整的 Release Notes"""
    previous_tag = get_previous_tag(current_tag)
    commits = get_commit_log(previous_tag, current_tag)
    categories = categorize_commits(commits)

    # 版本信息
    version = current_tag.lstrip("v")
    lines = [
        f"## 📦 工具箱 v{version}",
        "",
    ]

    # 变更说明
    if previous_tag:
        lines.append(f"### 📋 变更日志（{previous_tag} → {current_tag}）")
    else:
        lines.append("### 📋 变更日志（首次发布）")
    lines.append("")

    # 按分类输出
    has_content = False
    for cat_key, cat_info in categories.items():
        if cat_info["items"]:
            has_content = True
            lines.append(f"#### {cat_info['title']}")
            for item in cat_info["items"]:
                lines.append(f"- {item}")
            lines.append("")

    if not has_content:
        lines.append("_暂无变更记录_")
        lines.append("")

    # 功能列表
    lines.extend([
        "### 🧰 功能列表",
        "- 🗜️ 图片压缩 — 批量压缩 JPG/PNG/WebP 图片",
        "- 🔁 图片格式转换 — 批量转换图片格式",
        "- 🧩 图片拼接 — 多张图片横向或纵向拼接",
        "- 🖨️ 图片转 PDF — 多张图片合并为 PDF",
        "- 🔍 图片缩放 — 批量缩放图片尺寸",
        "- 📚 PDF 合并 — 多个 PDF 合并为一个",
        "- ✂️ PDF 拆分 — PDF 拆分为图片或单页 PDF",
        "- 🧹 文件去重 — 按内容 Hash 查找重复文件",
        "",
    ])

    # 下载说明
    lines.extend([
        "### 📥 下载",
        "- **Windows**: `*.exe` 安装包",
        "- **macOS**: `*.app` 应用包",
        "- **用户手册**: `manual-{version}.docx`",
        "",
    ])

    # 相关链接
    lines.extend([
        "### 🔗 相关链接",
        "- 🌐 [官方网站](https://github.com/yansheng836/python-toolbox)",
        "- 🐛 [问题反馈](https://github.com/yansheng836/python-toolbox/issues)",
        "- 📄 [更新日志](https://github.com/yansheng836/python-toolbox/blob/main/CHANGELOG.md)",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_notes.py <tag_name>", file=sys.stderr)
        sys.exit(1)

    current_tag = sys.argv[1]
    notes = generate_release_notes(current_tag)

    # 写入 GITHUB_OUTPUT
    output_path = os.environ.get("GITHUB_OUTPUT", "")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as f:
            # 使用 heredoc 方式写入多行内容，避免特殊字符问题
            f.write(f"content<<EOF\n{notes}\nEOF\n")
    else:
        print(notes)
