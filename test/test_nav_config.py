# -*- encoding: utf-8 -*-
"""
nav_config 单元测试：导航顺序/隐藏配置的解析、合并与持久化

对应设计文档 docs/2026-10-18-导航栏排序与隐藏方案分析.md。
纯逻辑测试，不启动 GUI。
"""

import config
from common import nav_config
from common.app_settings import AppSettings


def _default_ids(modules=None):
    """按 config 默认 order 排序的、参与导航排序的 id 列表"""
    modules = modules if modules is not None else config.PLUGIN_MODULES
    return nav_config.manageable_ids(modules)


# ==================== manageable_ids ====================


def test_manageable_ids_excludes_pinned_plugin():
    """order>=999 的固定项（设置）不参与排序，也不可隐藏"""
    assert "settings" not in _default_ids()


def test_manageable_ids_follows_order_value():
    modules = [
        {"id": "b", "order": 20},
        {"id": "a", "order": 10},
        {"id": "pinned", "order": nav_config.PINNED_ORDER},
    ]
    assert nav_config.manageable_ids(modules) == ["a", "b"]


# ==================== parse_list ====================


def test_parse_list_strips_blank_and_duplicates():
    assert nav_config.parse_list(" a, b ,,a,, c ") == ["a", "b", "c"]


def test_parse_list_handles_empty_values():
    assert nav_config.parse_list("") == []
    assert nav_config.parse_list(None) == []


# ==================== resolve_order ====================


def test_resolve_order_falls_back_to_default():
    assert nav_config.resolve_order(["a", "b", "c"], []) == ["a", "b", "c"]


def test_resolve_order_appends_new_plugins_at_end():
    """新版本新增的插件（不在保存顺序里）追加到末尾"""
    assert nav_config.resolve_order(["a", "b", "c"], ["c", "a"]) == ["c", "a", "b"]


def test_resolve_order_drops_stale_ids_and_duplicates():
    assert nav_config.resolve_order(["a", "b"], ["ghost", "b", "b", "a"]) == ["b", "a"]


# ==================== resolve_hidden ====================


def test_resolve_hidden_filters_unknown_and_pinned():
    """未知 id 与固定项（如 settings）不会进入隐藏集合"""
    assert nav_config.resolve_hidden(["a", "b"], ["b", "ghost", "b", "settings"]) == ["b"]


# ==================== load / save / reset ====================


def test_load_nav_state_without_settings_returns_defaults():
    order, hidden = nav_config.load_nav_state(None, config.PLUGIN_MODULES)
    assert order == _default_ids()
    assert hidden == []


def test_save_and_load_roundtrip(tmp_path):
    settings = AppSettings(config_dir=tmp_path)
    order = list(reversed(_default_ids()))
    hidden = [_default_ids()[0]]
    nav_config.save_nav_state(settings, order, hidden)

    reloaded = AppSettings(config_dir=tmp_path)
    assert nav_config.load_nav_state(reloaded, config.PLUGIN_MODULES) == (order, hidden)


def test_reset_nav_state_restores_defaults(tmp_path):
    settings = AppSettings(config_dir=tmp_path)
    nav_config.save_nav_state(settings, list(reversed(_default_ids())), [_default_ids()[0]])
    nav_config.reset_nav_state(settings)

    reloaded = AppSettings(config_dir=tmp_path)
    order, hidden = nav_config.load_nav_state(reloaded, config.PLUGIN_MODULES)
    assert order == _default_ids()
    assert hidden == []


def test_manual_edit_with_spaces_is_tolerated(tmp_path):
    """手工编辑 config.ini 带空格/空项时仍能正确解析"""
    settings = AppSettings(config_dir=tmp_path)
    ids = _default_ids()
    settings.set(nav_config.SECTION, nav_config.KEY_ORDER, f" {ids[1]} , ,{ids[0]} ")
    settings.save()

    order, _ = nav_config.load_nav_state(AppSettings(config_dir=tmp_path), config.PLUGIN_MODULES)
    assert order[:2] == [ids[1], ids[0]]
    assert set(order) == set(ids)
