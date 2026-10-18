# -*- encoding: utf-8 -*-
"""
nav_config — 侧边栏导航的顺序与可见性配置

设计依据 docs/2026-10-18-导航栏排序与隐藏方案分析.md：

- 配置以逗号分隔的插件 id 列表存于 config.ini 的 [nav] 段
- order 为空表示沿用 config.py 中 PLUGIN_MODULES 的默认顺序
- hidden 为隐藏的插件 id 列表
- 合并规则保证版本升级兼容：已删除的插件 id 被丢弃，新增插件按默认顺序追加到末尾
- 本模块只做纯逻辑与 INI 读写，不依赖 Qt，便于单测
"""

PINNED_ORDER = 999  # 与 config.py 中「设置」等固定项使用的哨兵值一致
SECTION = "nav"
KEY_ORDER = "order"
KEY_HIDDEN = "hidden"


def manageable_ids(plugin_modules):
    """返回参与排序的插件 id，按 PLUGIN_MODULES 的默认顺序（order 升序）

    order >= PINNED_ORDER 的固定项（如「设置」）不参与排序，也不可隐藏。
    """
    items = [
        p for p in plugin_modules
        if p.get("order", PINNED_ORDER) < PINNED_ORDER
    ]
    items.sort(key=lambda p: p.get("order", PINNED_ORDER))
    return [p["id"] for p in items]


def parse_list(value):
    """把 "a,b,c" 解析为去重后的 id 列表；空值返回空列表

    手工编辑配置可能带入空项、空格与重复项，这里一并清理。
    """
    if not value:
        return []
    result = []
    for part in str(value).split(","):
        item = part.strip()
        if item and item not in result:
            result.append(item)
    return result


def resolve_order(all_ids, saved_order):
    """合并已保存顺序与当前可用 id

    - saved_order 中仍存在的 id 保持相对顺序
    - 已不存在的 id 丢弃（打印提示，不静默）
    - 未出现在 saved_order 中的 id 按默认顺序追加到末尾
    """
    known = set(all_ids)
    stale = [pid for pid in (saved_order or []) if pid not in known]
    if stale:
        print(f"导航配置中的插件 id 不存在，已忽略：{', '.join(stale)}")

    ordered = []
    seen = set()
    for pid in (saved_order or []):
        if pid in known and pid not in seen:
            seen.add(pid)
            ordered.append(pid)
    for pid in all_ids:
        if pid not in seen:
            seen.add(pid)
            ordered.append(pid)
    return ordered


def resolve_hidden(all_ids, hidden_ids):
    """过滤未知/固定项 id 后的隐藏列表（保持输入顺序、去重）"""
    known = set(all_ids)
    result = []
    for pid in (hidden_ids or []):
        if pid in known and pid not in result:
            result.append(pid)
    return result


def load_nav_state(settings, plugin_modules):
    """读取并合并导航配置，返回 (order, hidden)

    settings 为 None（无持久化）时返回默认顺序与全部可见。
    """
    all_ids = manageable_ids(plugin_modules)
    if settings is None:
        return all_ids, []
    order = resolve_order(all_ids, parse_list(settings.get(SECTION, KEY_ORDER, "")))
    hidden = resolve_hidden(all_ids, parse_list(settings.get(SECTION, KEY_HIDDEN, "")))
    return order, hidden


def _save(settings):
    """落盘；失败只报告不抛出（与 AppSettings.load 的降级策略一致）"""
    try:
        settings.save()
    except OSError as e:
        print(f"警告：无法保存导航配置，本次修改将不会持久化：{e}")


def save_nav_state(settings, order, hidden):
    """写入导航配置并落盘；settings 为 None 时跳过"""
    if settings is None:
        return
    settings.set(SECTION, KEY_ORDER, ",".join(order))
    settings.set(SECTION, KEY_HIDDEN, ",".join(hidden))
    _save(settings)


def reset_nav_state(settings):
    """清空导航配置，恢复默认顺序与全部可见"""
    if settings is None:
        return
    settings.set(SECTION, KEY_ORDER, "")
    settings.set(SECTION, KEY_HIDDEN, "")
    _save(settings)
