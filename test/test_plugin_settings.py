# -*- encoding: utf-8 -*-
"""
test_plugin_settings — 插件设置项持久化公共方法测试

覆盖 ToolPlugin 基类的 load_setting/save_setting/set_combo_by_data、
AppSettings.remove_section，以及一个插件（image_compressor）的端到端往返。
"""

from common.app_settings import AppSettings
from toolbox import ToolPlugin


# ==================== 辅助：最小可用的 ToolPlugin 子类 ====================


class _FakeParent:
    """模拟 ToolboxWindow：只暴露 app_settings 属性"""

    def __init__(self, settings):
        self.app_settings = settings


class _DummyPlugin(ToolPlugin):
    id = "dummy"

    def create_ui(self):
        return None  # 本测试不涉及 UI


def _make_plugin(tmp_path):
    settings = AppSettings(config_dir=tmp_path)
    return _DummyPlugin(parent=_FakeParent(settings)), settings


# ==================== 1. AppSettings.remove_section ====================


def test_remove_section_existing(tmp_path):
    s = AppSettings(config_dir=tmp_path)
    s.set("plugin.x", "k", "v")
    assert s.get("plugin.x", "k") == "v"
    s.remove_section("plugin.x")
    assert s.get("plugin.x", "k") is None


def test_remove_section_missing_is_noop(tmp_path):
    s = AppSettings(config_dir=tmp_path)
    s.remove_section("plugin.nonexistent")  # 不应抛异常


# ==================== 2. load_setting / save_setting 往返 ====================


def test_save_then_load_round_trip(tmp_path):
    plugin, settings = _make_plugin(tmp_path)
    plugin.save_setting("n", 42)
    plugin.save_setting("b", True)
    plugin.save_setting("s", "JPG")
    plugin.save_setting("e", "")  # 空字符串视为缺省
    settings.save()

    # 用新实例读回，模拟下次启动
    plugin2, _ = _make_plugin(tmp_path)
    assert plugin2.load_setting("n", 0, int) == 42
    assert plugin2.load_setting("b", False, bool) is True
    assert plugin2.load_setting("s", "keep") == "JPG"
    assert plugin2.load_setting("e", "fallback") == "fallback"


def test_load_setting_missing_returns_default(tmp_path):
    plugin, _ = _make_plugin(tmp_path)
    assert plugin.load_setting("absent", "d") == "d"
    assert plugin.load_setting("absent", 7, int) == 7
    assert plugin.load_setting("absent", False, bool) is False


def test_load_setting_bad_type_returns_default(tmp_path):
    plugin, settings = _make_plugin(tmp_path)
    settings.set("plugin.dummy", "bad", "not-an-int")
    assert plugin.load_setting("bad", 5, int) == 5


def test_load_setting_bool_variants(tmp_path):
    plugin, settings = _make_plugin(tmp_path)
    for raw, expected in (("1", True), ("true", True), ("0", False),
                         ("false", False), ("yes", True), ("no", False)):
        settings.set("plugin.dummy", "b", raw)
        assert plugin.load_setting("b", False, bool) is expected


# ==================== 3. set_combo_by_data ====================


def test_set_combo_by_data_str(qapp, tmp_path):
    from PyQt6.QtWidgets import QComboBox
    combo = QComboBox()
    combo.addItem("A4", "A4")
    combo.addItem("Smart", "smart")
    plugin, _ = _make_plugin(tmp_path)
    plugin.set_combo_by_data(combo, "smart")
    assert combo.currentData() == "smart"


def test_set_combo_by_data_int(qapp, tmp_path):
    from PyQt6.QtWidgets import QComboBox
    combo = QComboBox()
    for v in (95, 85, 75, 50):
        combo.addItem(str(v), v)
    plugin, _ = _make_plugin(tmp_path)
    plugin.set_combo_by_data(combo, 85)
    assert combo.currentData() == 85


def test_set_combo_by_data_no_match(qapp, tmp_path):
    from PyQt6.QtWidgets import QComboBox
    combo = QComboBox()
    combo.addItem("X", "x")
    combo.setCurrentIndex(0)
    plugin, _ = _make_plugin(tmp_path)
    plugin.set_combo_by_data(combo, "zzz")
    assert combo.currentIndex() == 0  # 不变


# ==================== 4. 端到端：image_compressor 往返 ====================


def test_image_compressor_round_trip(qapp, tmp_path):
    """save_settings 写入后，重建实例 load_settings 应还原控件值"""
    from plugins.image_compressor import ImageCompressor

    settings = AppSettings(config_dir=tmp_path)
    parent = _FakeParent(settings)
    p1 = ImageCompressor(parent=parent)
    p1.get_widget()
    # 改成与默认不同的值
    p1.format_combo.setCurrentIndex(p1.format_combo.findData("PNG"))
    p1.quality_slider.setValue(60)
    p1.output_path.setText("/tmp/out")
    p1.save_settings()
    settings.save()

    # 重建
    settings2 = AppSettings(config_dir=tmp_path)
    p2 = ImageCompressor(parent=_FakeParent(settings2))
    p2.get_widget()
    p2.load_settings()
    assert p2.format_combo.currentData() == "PNG"
    assert p2.quality_slider.value() == 60
    assert p2.output_path.text() == "/tmp/out"


def test_reset_settings_clears_values(qapp, tmp_path):
    from plugins.image_compressor import ImageCompressor

    settings = AppSettings(config_dir=tmp_path)
    p = ImageCompressor(parent=_FakeParent(settings))
    p.get_widget()
    p.quality_slider.setValue(40)
    p.save_settings()
    settings.save()

    # 用同一 INI 重建并 reset
    p2 = ImageCompressor(parent=_FakeParent(AppSettings(config_dir=tmp_path)))
    p2.get_widget()
    p2.reset_settings()
    # 默认质量 75（image_compressor create_ui 中的硬编码）
    assert p2.quality_slider.value() == 75
