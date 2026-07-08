# -*- encoding: utf-8 -*-
"""
插件自动发现、UI 创建和主题切换测试
"""

import pytest
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from toolbox import Theme


# ==================== 插件加载测试 ====================


class TestPluginLoading:
    """测试插件自动发现和加载"""

    def test_plugins_loaded(self, loaded_plugins):
        """所有插件都应被加载"""
        assert len(loaded_plugins) >= 8, f"只加载了 {len(loaded_plugins)} 个插件"

    def test_specific_plugins_present(self, loaded_plugins):
        """核心插件应存在（中文名称）"""
        expected_names = [
            "图片压缩",
            "图片缩放",
            "图片格式转换",
            "图片拼接",
            "图片转PDF",
            "PDF合并",
            "PDF拆分",
            "文件去重",
        ]
        plugin_names = [p.name for p in loaded_plugins.values()]
        for name in expected_names:
            assert name in plugin_names, f"缺少插件: {name}"

    def test_plugin_has_required_attributes(self, loaded_plugins):
        """每个插件都应有 name, description, icon, version, order"""
        for name, plugin in loaded_plugins.items():
            assert hasattr(plugin, "name"), f"{name} 缺少 name"
            assert hasattr(plugin, "description"), f"{name} 缺少 description"
            assert hasattr(plugin, "icon"), f"{name} 缺少 icon"
            assert hasattr(plugin, "version"), f"{name} 缺少 version"
            assert hasattr(plugin, "order"), f"{name} 缺少 order"
            assert plugin.name, f"{name} 的 name 为空"

    def test_plugin_order_unique(self, loaded_plugins):
        """插件 order 应唯一（或至少有排序）"""
        orders = [p.order for p in loaded_plugins.values()]
        assert len(orders) == len(set(orders)), "插件 order 不唯一"

    def test_plugin_has_get_widget(self, loaded_plugins):
        """每个插件都应有 get_widget 方法"""
        for name, plugin in loaded_plugins.items():
            assert hasattr(plugin, "get_widget"), f"{name} 缺少 get_widget"


# ==================== UI 创建测试 ====================


class TestPluginUI:
    """测试插件的 UI 创建"""

    def test_all_uis_created(self, loaded_plugins, qapp):
        """所有插件的 UI 都应创建成功"""
        for name, plugin in loaded_plugins.items():
            widget = plugin.get_widget()
            assert widget is not None, f"{name} create_ui 返回 None"
            assert isinstance(widget, QWidget), f"{name} 返回的不是 QWidget"

    def test_ui_has_layout(self, loaded_plugins, qapp):
        """UI 应有布局"""
        for name, plugin in loaded_plugins.items():
            widget = plugin.get_widget()
            assert widget.layout() is not None, f"{name} 没有 layout"

    def test_ui_has_title_label(self, loaded_plugins, qapp):
        """UI 应有 title_label（可能通过 _setup_header 或手动创建）"""
        plugins_without_title = []
        for name, plugin in loaded_plugins.items():
            if not hasattr(plugin, "title_label") or plugin.title_label is None:
                plugins_without_title.append(name)
        # SettingsPlugin 也可能没有 title_label，但核心插件都应有
        assert len(plugins_without_title) <= 1, f"缺少 title_label: {plugins_without_title}"


# ==================== 主题切换测试 ====================


class TestThemeSwitching:
    """测试插件的主题切换"""

    def test_update_theme_dark(self, loaded_plugins, qapp):
        """所有插件都应能切换深色主题"""
        failures = []
        for name, plugin in loaded_plugins.items():
            try:
                # 先创建 UI
                plugin.get_widget()
                plugin.update_theme(Theme.DARK)
            except Exception as e:
                failures.append(f"{name}: {e}")
        assert not failures, f"主题切换失败:\n" + "\n".join(failures)

    def test_update_theme_light(self, loaded_plugins, qapp):
        """所有插件都应能切换浅色主题"""
        failures = []
        for name, plugin in loaded_plugins.items():
            try:
                plugin.get_widget()
                plugin.update_theme(Theme.LIGHT)
            except Exception as e:
                failures.append(f"{name}: {e}")
        assert not failures, f"主题切换失败:\n" + "\n".join(failures)

    def test_theme_switch_back_and_forth(self, loaded_plugins, qapp):
        """主题切换不应抛出异常"""
        plugin = next(iter(loaded_plugins.values()))
        plugin.get_widget()
        for _ in range(3):
            plugin.update_theme(Theme.DARK)
            plugin.update_theme(Theme.LIGHT)

    def test_update_theme_without_ui(self, qapp):
        """未创建 UI 时 update_theme 不应崩溃"""
        from plugins.image_compressor import ImageCompressor

        plugin = ImageCompressor()
        # 不调用 get_widget()，直接切换主题
        plugin.update_theme(Theme.DARK)
        plugin.update_theme(Theme.LIGHT)


# ==================== 插件特有功能测试 ====================


class TestSpecificPlugins:
    """特定插件功能测试"""

    def test_image_compressor_has_ui_components(self, qapp):
        """图片压缩插件 UI 组件完整性"""
        from plugins.image_compressor import ImageCompressor

        plugin = ImageCompressor()
        widget = plugin.get_widget()
        assert hasattr(plugin, "file_panel")
        assert hasattr(plugin, "format_combo")
        assert hasattr(plugin, "quality_slider")
        assert hasattr(plugin, "output_path")
        assert hasattr(plugin, "action_panel")

    def test_image_scaler_has_ui_components(self, qapp):
        """图片缩放插件 UI 组件完整性"""
        from plugins.image_scaler import ImageScaler

        plugin = ImageScaler()
        widget = plugin.get_widget()
        inner = widget
        assert hasattr(inner, "file_panel") or hasattr(plugin, "file_panel")
        assert hasattr(inner, "scale_type_combo") or hasattr(plugin, "scale_type_combo")

    def test_format_converter_has_ui_components(self, qapp):
        """格式转换插件 UI 组件完整性"""
        from plugins.image_format_converter import FormatConverter

        plugin = FormatConverter()
        widget = plugin.get_widget()
        assert hasattr(plugin, "fmt_combo")
        assert hasattr(plugin, "file_panel")

    def test_pdf_merger_has_ui_components(self, qapp):
        """PDF合并插件 UI 组件完整性"""
        from plugins.pdf_merger import PDFMerger

        plugin = PDFMerger()
        widget = plugin.get_widget()
        # PDFMerger 使用内层 Widget（PDFMergerWidget），属性在 plugin 上通过 wrapper 暴露
        assert hasattr(plugin, "title_label") or hasattr(widget, "file_panel")