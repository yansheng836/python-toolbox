# -*- encoding: utf-8 -*-
"""PLUGIN_MODULES 稳定 id 校验"""

import re
from config import PLUGIN_MODULES


def test_each_plugin_has_id():
    for p in PLUGIN_MODULES:
        assert "id" in p, f"插件 {p.get('name')} 缺少 id 字段"


def test_ids_unique():
    ids = [p["id"] for p in PLUGIN_MODULES]
    assert len(ids) == len(set(ids)), f"id 重复: {ids}"


def test_ids_snake_case():
    pat = re.compile(r"^[a-z][a-z0-9_]*$")
    for p in PLUGIN_MODULES:
        assert pat.match(p["id"]), f"id 不符合 snake_case: {p['id']}"


def test_settings_id_present():
    settings = [p for p in PLUGIN_MODULES if p["class"] == "SettingsPlugin"]
    assert settings and settings[0]["id"] == "settings"
