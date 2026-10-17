# -*- encoding: utf-8 -*-
"""
scripts/check_i18n.py 的单元测试

覆盖：key 覆盖（MISSING/EXTRA）、占位符一致性（PLACEHOLDER）、复数结构（STRUCTURE）、
空值（EMPTY）、JSON 合法性（INVALID_JSON）、fragments key 冲突（CONFLICT）。
全部使用 tmp_path 构造临时词典目录，不依赖真实 i18n/ 内容，无需 qapp。
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.check_i18n import (
    check_dictionaries,
    check_fragments,
    extract_placeholders,
    main,
)


# ==================== 辅助 ====================


def make_dict_dir(tmp_path, name="i18n"):
    """在 tmp_path 下创建一个词典目录"""
    d = tmp_path / name
    d.mkdir()
    return d


def write_dict(dir_path, file_name, data):
    """以 UTF-8 写入一个 JSON 词典文件"""
    (dir_path / file_name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ==================== 词典校验 ====================


def test_valid_pair_ok(tmp_path):
    """zh_CN + en key 集合一致、占位符一致 → 0 错误"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"a.hello": "你好，{name}", "a.count": "{count} 项"})
    write_dict(d, "en.json", {"a.hello": "Hello, {name}", "a.count": "{count} items"})
    assert check_dictionaries(d) == []


def test_missing_key_detected(tmp_path):
    """en 少一个 key → 1 个 MISSING 错误"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"a.hello": "你好", "a.bye": "再见"})
    write_dict(d, "en.json", {"a.hello": "Hello"})
    errors = check_dictionaries(d)
    assert len(errors) == 1
    assert "MISSING" in errors[0]
    assert "a.bye" in errors[0]
    assert "en.json" in errors[0]


def test_extra_key_detected(tmp_path):
    """en 多一个 key → EXTRA 错误"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"a.hello": "你好"})
    write_dict(d, "en.json", {"a.hello": "Hello", "en.only": "Only in English"})
    errors = check_dictionaries(d)
    assert len(errors) == 1
    assert "EXTRA" in errors[0]
    assert "en.only" in errors[0]


def test_placeholder_mismatch(tmp_path):
    """zh 含 {name} 而 en 缺失 → PLACEHOLDER 错误"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"greet": "你好 {name}"})
    write_dict(d, "en.json", {"greet": "Hello"})
    errors = check_dictionaries(d)
    assert len(errors) == 1
    assert "PLACEHOLDER" in errors[0]
    assert "greet" in errors[0]


def test_structure_mismatch(tmp_path):
    """zh 为复数 dict 而 en 为纯字符串 → STRUCTURE 错误"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"items": {"one": "{count} 项", "other": "{count} 项"}})
    write_dict(d, "en.json", {"items": "{count} items"})
    errors = check_dictionaries(d)
    assert len(errors) == 1
    assert "STRUCTURE" in errors[0]
    assert "items" in errors[0]


def test_plural_inner_placeholder_mismatch(tmp_path):
    """两侧均为复数 dict，但 one 子项占位符不一致 → PLACEHOLDER（key.one）"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"items": {"one": "{count} 项", "other": "{count} 项"}})
    write_dict(d, "en.json", {"items": {"one": "1 item", "other": "{count} items"}})
    errors = check_dictionaries(d)
    assert len(errors) == 1
    assert "PLACEHOLDER" in errors[0]
    assert "items.one" in errors[0]


def test_empty_value(tmp_path):
    """value 为空字符串 → EMPTY 错误"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"k": "值"})
    write_dict(d, "en.json", {"k": ""})
    errors = check_dictionaries(d)
    assert len(errors) == 1
    assert "EMPTY" in errors[0]
    assert "k" in errors[0]
    assert "en.json" in errors[0]


def test_invalid_json(tmp_path):
    """垃圾文件 → INVALID_JSON 错误，不抛异常"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"k": "值"})
    (d / "en.json").write_text("{ not valid json !!", encoding="utf-8")
    errors = check_dictionaries(d)  # 不应抛出异常
    assert len(errors) == 1
    assert "INVALID_JSON" in errors[0]
    assert "en.json" in errors[0]


def test_missing_zh_cn_baseline(tmp_path):
    """直接调用时缺 zh_CN.json 基准 → 返回 MISSING 错误（CLI 层会转为提示并跳过）"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "en.json", {"k": "value"})
    errors = check_dictionaries(d)
    assert len(errors) == 1
    assert "MISSING" in errors[0]
    assert "zh_CN.json" in errors[0]


# ==================== fragments 冲突校验 ====================


def test_fragment_conflict(tmp_path):
    """两个 fragment 同 key 不同值 → CONFLICT；同 key 同值 → 提示不计错误"""
    fdir = tmp_path / "fragments"
    fdir.mkdir()
    write_dict(fdir, "a.json", {"k.one": "值A", "same.key": "相同"})
    write_dict(fdir, "b.json", {"k.one": "值B", "same.key": "相同"})
    errors, notes = check_fragments(fdir)
    assert len(errors) == 1
    assert "CONFLICT" in errors[0]
    assert "k.one" in errors[0]
    assert not any("same.key" in e for e in errors)
    assert any("same.key" in note for note in notes)


# ==================== 占位符提取 ====================


def test_placeholder_regex_ignores_escapes():
    """{{literal}} 是转义块，不算占位符"""
    assert extract_placeholders("{{literal}}") == set()
    assert extract_placeholders("{{literal}} {name}") == {"name"}
    assert extract_placeholders("你好 {name}，共 {count} 个") == {"name", "count"}
    assert extract_placeholders("无占位符") == set()


# ==================== CLI（main） ====================


def test_main_ok_exit_0(tmp_path, capsys):
    """词典全部一致 → 退出码 0，汇总 OK"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"k": "值"})
    write_dict(d, "en.json", {"k": "value"})
    assert main(["--dir", str(d)]) == 0
    assert "OK: 2 files checked" in capsys.readouterr().out


def test_main_error_exit_1(tmp_path, capsys):
    """存在 MISSING 错误 → 退出码 1，汇总错误数"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"k": "值"})
    write_dict(d, "en.json", {})
    assert main(["--dir", str(d)]) == 1
    out = capsys.readouterr().out
    assert "MISSING" in out
    assert "1 errors, 2 files checked" in out


def test_main_no_zh_cn_hint_exit_0(tmp_path, capsys):
    """没有 zh_CN.json → 输出提示、跳过词典校验、退出码 0（不崩溃）"""
    d = make_dict_dir(tmp_path)
    assert main(["--dir", str(d)]) == 0
    out = capsys.readouterr().out
    assert "提示" in out
    assert "OK: 0 files checked" in out


def test_main_fragments_conflict_exit_1(tmp_path, capsys):
    """--fragments 模式下 fragment 冲突 → 退出码 1"""
    d = make_dict_dir(tmp_path)
    write_dict(d, "zh_CN.json", {"k": "值"})
    write_dict(d, "en.json", {"k": "value"})
    fdir = d / "fragments"
    fdir.mkdir()
    write_dict(fdir, "a.json", {"x": "1"})
    write_dict(fdir, "b.json", {"x": "2"})
    assert main(["--dir", str(d), "--fragments"]) == 1
    out = capsys.readouterr().out
    assert "CONFLICT" in out
    assert "4 files checked" in out
