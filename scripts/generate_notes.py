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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            check=True,
        )
        stdout = result.stdout or ""
        tags = [t.strip() for t in stdout.strip().split("\n") if t.strip()]
        if current_tag in tags:
            idx = tags.index(current_tag)
            if idx + 1 < len(tags):
                return tags[idx + 1]
        return None
    except Exception:
        return None


def get_commit_log(from_tag: str | None, to_tag: str) -> list:
    """获取两个标签之间的提交日志"""
    if from_tag:
        range_spec = f"{from_tag}..{to_tag}"
    else:
        range_spec = to_tag

    result = subprocess.run(
        ["git", "log", range_spec, "-z", "--pretty=format:%h|%s|%b"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        return []

    stdout = result.stdout.decode("utf-8", errors="replace")
    if not stdout.strip():
        return []

    commits = []
    for entry in stdout.strip().split("\0"):
        entry = entry.strip()
        if not entry or "|" not in entry:
            continue
        parts = entry.split("|", 2)
        sha = parts[0][:7]
        subject = parts[1] if len(parts) > 1 else ""
        body = parts[2].strip() if len(parts) > 2 else ""
        # 过滤掉 Co-Authored-By 等 git trailer 行
        if body:
            body = "\n".join(
                line for line in body.split("\n")
                if not line.strip().startswith("Co-Authored-By")
            )

        # 解析 conventional commit 类型
        commit_type = ""
        if subject.startswith(("feat", "fix", "refactor", "docs", "test", "chore", "perf", "ci")):
            commit_type = subject.split(":")[0]
            subject = subject.split(":", 1)[1].strip() if ":" in subject else subject

        # 过滤 Co-Authored-By 等非实际变更的行
        if not subject and not body:
            continue

        commits.append({
            "sha": sha,
            "type": commit_type,
            "subject": subject,
            "body": body,
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
            body_lines = [line for line in c["body"].split("\n") if line.strip()]
            indented_body = "\n".join(f"  > {line}" for line in body_lines)
            item_text += f"\n{indented_body}"
        categories[cat_key]["items"].append(item_text)

    return categories


def generate_release_notes(current_tag: str) -> str:
    """生成完整的 Release Notes"""
    previous_tag = get_previous_tag(current_tag)
    commits = get_commit_log(previous_tag, current_tag)
    if commits is None:
        commits = []
    categories = categorize_commits(commits)

    version = current_tag.lstrip("v")

    # 简要说明
    summary_parts = []
    for cat_key in ["feat", "fix", "perf", "refactor"]:
        if cat_key in categories and categories[cat_key]["items"]:
            summary_parts.append(f"**{categories[cat_key]['title']}**：{len(categories[cat_key]['items'])} 项")
    summary = "、".join(summary_parts) if summary_parts else "问题修复与功能改进"

    lines = [
        f"{summary}",
        "",
    ]

    lines.append("### 变更日志")
    if previous_tag:
        lines.append(f"对比范围 `{previous_tag}` → `{current_tag}`")
    else:
        lines.append("首次发布")
    lines.append("")

    # 按分类输出
    has_content = False
    for cat_key, cat_info in categories.items():
        if cat_info["items"]:
            has_content = True
            lines.append(f"**{cat_info['title']}**")
            for item in cat_info["items"]:
                lines.append(f"- {item}")
            lines.append("")

    if not has_content:
        lines.append("_暂无变更记录_")
        lines.append("")

    # 下载说明
    lines.extend([
        "### 下载",
        "",
        f"| 平台 | 文件 |",
        f"|------|------|",
        f"| Windows | `工具箱ToolBox-win-{version}.zip` |",
        f"| macOS | `工具箱ToolBox-mac-{version}.tar.gz` |",
        "",
    ])

    # 相关链接
    lines.extend([
        "### 相关链接",
        "",
        "- [官方网站](https://github.com/yansheng836/python-toolbox)",
        "- [问题反馈](https://github.com/yansheng836/python-toolbox/issues)",
        "- [更新日志](https://github.com/yansheng836/python-toolbox/blob/main/CHANGELOG.md)",
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