# -*- encoding: utf-8 -*-
"""
真实词典校验：确保生产 i18n/ 词典与源码引用一致

test_p3_* 使用自建假词典验证重放链路，本文件改为加载真实 en.json/zh_CN.json，
避免英文文案在生产词典缺失或键名拼错时测试仍然通过。
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import PLUGIN_MODULES
from scripts.check_i18n import check_code_references, check_dictionaries

I18N_DIR = PROJECT_ROOT / "i18n"


def _load(name):
    return json.loads((I18N_DIR / name).read_text(encoding="utf-8"))


def test_real_dictionaries_are_consistent():
    """真实 zh_CN.json / en.json 的键、占位符与结构完全一致"""
    assert check_dictionaries(I18N_DIR) == []


def test_plugin_names_and_descriptions_exist_in_both_languages():
    """每个插件页标题与描述在中英文词典中都存在"""
    zh = _load("zh_CN.json")
    en = _load("en.json")
    missing = []
    for plugin in PLUGIN_MODULES:
        for suffix in ("name", "description"):
            key = f"plugin.{plugin['id']}.{suffix}"
            if key not in zh or key not in en:
                missing.append(key)
    assert missing == []


def test_source_references_resolve_against_real_dictionary():
    """源码中 t()/bind()/bind_combo() 的常量 key 都能在真实词典中找到"""
    assert check_code_references(I18N_DIR, PROJECT_ROOT) == []
