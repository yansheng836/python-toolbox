# -*- encoding: utf-8 -*-
"""
test_p3_image_compressor — 图片压缩插件 i18n 迁移测试

覆盖：创建时使用词典原文、retranslate_ui 语言切换重放、下拉框稳定 data、
worker 用户可见消息经 t() 格式化（不启动线程）。
en.json 尚未存在（P4 阶段交付），测试通过向 manager._dicts 注入临时
en 词典来模拟语言切换，结束后恢复。
"""

import pytest

from common import i18n
from plugins.image_compressor import CompressionWorker, ImageCompressor


TEST_EN = {
    "plugin.image_compressor.name": "Image Compressor",
    "plugin.image_compressor.description": "Batch compress JPG/PNG/WebP images",
    "plugin.image_compressor.card.select_images": "Select images",
    "plugin.image_compressor.card.settings": "Compression settings",
    "plugin.image_compressor.label.format": "Output format:",
    "plugin.image_compressor.label.quality": "Quality:",
    "plugin.image_compressor.label.output_dir": "Output directory:",
    "plugin.image_compressor.placeholder.output_dir": "Defaults to source folder",
    "plugin.image_compressor.button.browse": "Browse",
    "plugin.image_compressor.button.start": "Compress",
    "plugin.image_compressor.filter.images": "Image files (*.jpg *.png)",
    "plugin.image_compressor.combo.keep": "Keep original",
}


@pytest.fixture
def en_dict():
    """注入临时 en 词典，测试结束恢复"""
    saved = dict(i18n.manager._dicts)
    saved_current = i18n.manager.current_language
    i18n.manager._dicts["en"] = dict(TEST_EN)
    yield
    i18n.manager._dicts.clear()
    i18n.manager._dicts.update(saved)
    i18n.set_language(saved_current)


@pytest.fixture
def compressor(qapp):
    """构造插件并创建 UI（不启动窗口/线程）"""
    from toolbox import Theme

    plugin = ImageCompressor.__new__(ImageCompressor)
    plugin.icon = "🗜️"
    plugin.name = "图片压缩"
    plugin.description = ""
    plugin.widget = None
    plugin.theme = Theme.DARK
    widget = plugin.create_ui()
    return plugin, widget


@pytest.mark.usefixtures("qapp")
def test_texts_use_dictionary_zh(compressor):
    """创建后关键文本等于 zh_CN 词典原文"""
    plugin, _ = compressor

    assert i18n.t("plugin.image_compressor.name") == "图片压缩"
    assert plugin.title_label.text() == f"🗜️ {i18n.t('plugin.image_compressor.name')}"
    assert plugin.desc_label.text() == i18n.t(
        "plugin.image_compressor.description")
    assert plugin.file_card.title_label.text() == i18n.t(
        "plugin.image_compressor.card.select_images")
    assert plugin.settings_card.title_label.text() == i18n.t(
        "plugin.image_compressor.card.settings")
    assert plugin.format_label.text() == "输出格式:"
    assert plugin.quality_caption_label.text() == "压缩质量:"
    assert plugin.output_dir_label.text() == "输出目录:"
    assert plugin.output_path.placeholderText() == i18n.t(
        "plugin.image_compressor.placeholder.output_dir")
    assert plugin.browse_btn.text() == "浏览"
    assert plugin.action_panel.btn.text() == "开始压缩"
    assert plugin.file_panel.file_filter == i18n.t(
        "plugin.image_compressor.filter.images")
    assert plugin.format_combo.itemText(0) == "保持原格式"


@pytest.mark.usefixtures("qapp")
def test_retranslate_switches_to_english(compressor, en_dict):
    """切 en 后 retranslate_ui 重放关键文本，切回 zh_CN 恢复"""
    plugin, _ = compressor

    i18n.set_language("en")
    plugin.retranslate_ui()

    assert plugin.title_label.text() == "🗜️ Image Compressor"
    assert plugin.desc_label.text() == "Batch compress JPG/PNG/WebP images"
    assert plugin.file_card.title_label.text() == "Select images"
    assert plugin.settings_card.title_label.text() == "Compression settings"
    assert plugin.format_label.text() == "Output format:"
    assert plugin.quality_caption_label.text() == "Quality:"
    assert plugin.output_dir_label.text() == "Output directory:"
    assert plugin.output_path.placeholderText() == "Defaults to source folder"
    assert plugin.browse_btn.text() == "Browse"
    assert plugin.action_panel.btn.text() == "Compress"
    assert plugin.file_panel.file_filter == "Image files (*.jpg *.png)"
    # 下拉框由 bind_combo 自动重放
    assert plugin.format_combo.itemText(
        plugin.format_combo.findData("keep")) == "Keep original"

    i18n.set_language("zh_CN")
    plugin.retranslate_ui()

    assert plugin.title_label.text() == "🗜️ 图片压缩"
    assert plugin.format_label.text() == "输出格式:"
    assert plugin.action_panel.btn.text() == "开始压缩"
    assert plugin.format_combo.itemText(
        plugin.format_combo.findData("keep")) == "保持原格式"


@pytest.mark.usefixtures("qapp")
def test_combo_keeps_stable_data(compressor, en_dict):
    """组合框每项 data 非空；切语言后 currentData 不变"""
    plugin, _ = compressor
    combo = plugin.format_combo

    for i in range(combo.count()):
        assert combo.itemData(i)

    combo.setCurrentIndex(combo.findData("PNG"))
    assert combo.currentData() == "PNG"

    i18n.set_language("en")
    assert combo.currentData() == "PNG"
    assert combo.itemText(combo.findData("JPG")) == "JPG"

    i18n.set_language("zh_CN")
    assert combo.currentData() == "PNG"


def test_worker_messages_use_dictionary(qapp):
    """worker 用户可见消息经词典格式化（不启动线程）"""
    worker = CompressionWorker([], None, "keep", 75)
    assert worker.format_code == "keep"
    assert i18n.t(
        "plugin.image_compressor.msg.processing", name="a.png") == "正在处理: a.png"
    assert i18n.t(
        "plugin.image_compressor.msg.compress_done", count=3) == "成功压缩 3 张图片！"
    assert i18n.t(
        "plugin.image_compressor.error.compress_failed", error="boom"
    ) == "压缩失败: boom"
