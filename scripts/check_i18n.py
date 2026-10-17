#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
i18n 词典校验脚本 — key 覆盖、占位符一致性、复数结构、空值与 JSON 合法性

依据 docs/2026-10-17-多语言国际化方案分析.md §6.2 / §6.8。

用法：
    python scripts/check_i18n.py                 # 校验 i18n/ 下所有词典
    python scripts/check_i18n.py --dir <dir>     # 校验指定目录（测试用）
    python scripts/check_i18n.py --fragments     # 额外校验 i18n/fragments/*.json 之间的 key 冲突

退出码：0 全部通过；1 有错误。
纯标准库实现（json、re、argparse、pathlib）。
"""

import argparse
import json
import re
import sys
from pathlib import Path

# 源语言基准文件名
SOURCE_LOCALE = "zh_CN"
# 复数结构允许的子键
PLURAL_KEYS = {"one", "other"}
# 占位符：{name}，忽略 {{ }} 转义
PLACEHOLDER_RE = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
ESCAPED_PLACEHOLDER_RE = re.compile(r"\{\{|\}\}")


def _safe_repr(value):
    """将值转为 ASCII 安全的表示形式，避免非 GBK/终端编码字符导致输出崩溃"""
    return ascii(value)


def extract_placeholders(text):
    """提取字符串中的 {name} 占位符集合，忽略 {{ / }} 转义"""
    unescaped = ESCAPED_PLACEHOLDER_RE.sub("\x00", text)
    return set(PLACEHOLDER_RE.findall(unescaped))


def is_plural(value):
    """判断 value 是否为复数结构 {"one": ..., "other": ...}"""
    return isinstance(value, dict) and set(value) <= PLURAL_KEYS


def _compare_values(errors, file_name, key, base, other):
    """按规则 2/4 递归比较一个 key 下的两个值（复数结构已由调用方确认一致）"""
    if isinstance(base, dict) and isinstance(other, dict):
        # 复数子结构（或防御性处理畸形 dict）：仅递归两侧都存在的子键
        for sub_key in sorted(PLURAL_KEYS):
            if sub_key in base and sub_key in other:
                _compare_values(
                    errors, file_name, f"{key}.{sub_key}",
                    base[sub_key], other[sub_key],
                )
        return
    if isinstance(other, str) and not other:
        errors.append(f"ERROR: {file_name}: {key} - EMPTY: 值为空字符串")
        return
    if isinstance(base, str) and isinstance(other, str):
        if extract_placeholders(base) != extract_placeholders(other):
            errors.append(
                f"ERROR: {file_name}: {key} - PLACEHOLDER: "
                f"占位符不一致，期望 {sorted(extract_placeholders(base))}，"
                f"实际 {sorted(extract_placeholders(other))}"
            )


def check_fragments(fragments_dir):
    """校验 fragments/*.json 之间的 key 冲突

    返回 (errors, notes)：errors 为 CONFLICT 错误列表；notes 为
    同 key 同值的提示列表（不计入错误）。
    """
    errors = []
    notes = []
    fragment_files = sorted(fragments_dir.glob("*.json"))
    # key -> [(file, value), ...]
    seen = {}
    for fragment_file in fragment_files:
        try:
            data = json.loads(fragment_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
            errors.append(f"ERROR: {fragment_file.name}: - INVALID_JSON: {e}")
            continue
        if not isinstance(data, dict):
            errors.append(
                f"ERROR: {fragment_file.name}: - INVALID_JSON: 顶层必须是 JSON 对象"
            )
            continue
        for key, value in data.items():
            seen.setdefault(key, []).append((fragment_file.name, value))
    for key in sorted(seen):
        entries = seen[key]
        if len(entries) < 2:
            continue
        first_file, first_value = entries[0]
        for file_name, value in entries[1:]:
            if value == first_value:
                notes.append(
                    f"NOTE: {key} 在 {first_file} 与 {file_name} 中重复（值相同）"
                )
            else:
                errors.append(
                    f"ERROR: fragments: {key} - CONFLICT: "
                    f"{first_file}={_safe_repr(first_value)} 与 "
                    f"{file_name}={_safe_repr(value)} 值不同"
                )
    return errors, notes


def check_dictionaries(dir_path):
    """校验 dir_path 下所有 <locale>.json 与 zh_CN.json 的一致性，返回错误列表"""
    errors = []
    base_file = dir_path / f"{SOURCE_LOCALE}.json"
    if not base_file.exists():
        errors.append(
            f"ERROR: {base_file.name}: - MISSING: 缺少源语言基准文件 {base_file.name}"
        )
        return errors

    try:
        base_data = json.loads(base_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        errors.append(f"ERROR: {base_file.name}: - INVALID_JSON: {e}")
        return errors
    if not isinstance(base_data, dict):
        errors.append(
            f"ERROR: {base_file.name}: - INVALID_JSON: 顶层必须是 JSON 对象"
        )
        return errors

    dict_files = sorted(dir_path.glob("*.json"))
    for dict_file in dict_files:
        if dict_file.name == base_file.name:
            continue
        try:
            data = json.loads(dict_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errors.append(f"ERROR: {dict_file.name}: - INVALID_JSON: {e}")
            continue
        if not isinstance(data, dict):
            errors.append(
                f"ERROR: {dict_file.name}: - INVALID_JSON: 顶层必须是 JSON 对象"
            )
            continue
        _check_pair(errors, dict_file.name, base_data, data)

    # zh_CN 自身的空值与复数子结构检查
    _check_self(errors, base_file.name, base_data)
    return errors


def _check_pair(errors, file_name, base_data, data):
    """比较一个目标语言词典与基准词典"""
    for key in sorted(base_data.keys() - data.keys()):
        errors.append(f"ERROR: {file_name}: {key} - MISSING: 缺少 key")
    for key in sorted(data.keys() - base_data.keys()):
        errors.append(f"ERROR: {file_name}: {key} - EXTRA: 多余 key")
    for key in sorted(base_data.keys() & data.keys()):
        base_value = base_data[key]
        other_value = data[key]
        base_plural = is_plural(base_value)
        other_plural = is_plural(other_value)
        if base_plural != other_plural:
            errors.append(
                f"ERROR: {file_name}: {key} - STRUCTURE: "
                f"复数结构不一致，基准为"
                f"{'复数 dict' if base_plural else '纯字符串'}，"
                f"{'目标为纯字符串' if base_plural else '目标为复数 dict'}"
            )
        elif base_plural:
            # 复数结构子键集合必须一致（都是 {one,other} 的子集）
            if set(base_value) != set(other_value):
                errors.append(
                    f"ERROR: {file_name}: {key} - STRUCTURE: "
                    f"复数子键不一致，基准 {sorted(base_value)}，"
                    f"实际 {sorted(other_value)}"
                )
            else:
                _compare_values(errors, file_name, key, base_value, other_value)
        else:
            _compare_values(errors, file_name, key, base_value, other_value)


def _check_self(errors, file_name, data):
    """对基准词典自身做空值与复数子结构检查"""
    for key in sorted(data):
        value = data[key]
        if is_plural(value):
            for sub_key in sorted(value):
                sub_value = value[sub_key]
                if isinstance(sub_value, str) and not sub_value:
                    errors.append(
                        f"ERROR: {file_name}: {key}.{sub_key} - EMPTY: 值为空字符串"
                    )
        elif isinstance(value, str) and not value:
            errors.append(f"ERROR: {file_name}: {key} - EMPTY: 值为空字符串")


def main(argv=None):
    """CLI 入口，返回退出码"""
    # 输出不可编码字符时降级为 ?，避免报告中途因 UnicodeEncodeError 崩溃
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(
        description="校验 i18n 词典的 key 覆盖、占位符一致性与复数结构"
    )
    parser.add_argument(
        "--dir",
        default="i18n",
        help="词典目录（默认 i18n/）",
    )
    parser.add_argument(
        "--fragments",
        action="store_true",
        help="额外校验 <dir>/fragments/*.json 之间的 key 冲突",
    )
    args = parser.parse_args(argv)

    dir_path = Path(args.dir)
    errors = []
    files_checked = 0

    if not dir_path.is_dir():
        print(f"ERROR: 目录不存在：{dir_path}")
        return 1

    has_base = (dir_path / f"{SOURCE_LOCALE}.json").exists()
    if not has_base:
        print(
            f"提示：{dir_path / (SOURCE_LOCALE + '.json')} 不存在，"
            f"跳过词典一致性校验。"
        )

    if args.fragments:
        fragments_dir = dir_path / "fragments"
        if not fragments_dir.is_dir():
            print(f"提示：{fragments_dir} 不存在，跳过 fragments 冲突校验。")
        else:
            fragment_files = list(fragments_dir.glob("*.json"))
            files_checked += len(fragment_files)
            fragment_errors, fragment_notes = check_fragments(fragments_dir)
            for note in fragment_notes:
                print(note)
            errors.extend(fragment_errors)

    if has_base:
        dict_files = [p for p in dir_path.glob("*.json") if p.is_file()]
        files_checked += len(dict_files)
        errors.extend(check_dictionaries(dir_path))

    for error in errors:
        print(error)

    if errors:
        print(f"{len(errors)} errors, {files_checked} files checked")
        return 1
    print(f"OK: {files_checked} files checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
