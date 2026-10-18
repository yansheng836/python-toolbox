# -*- encoding: utf-8 -*-
"""图片拼接插件 i18n 迁移测试：词典文本、retranslate_ui、组合框稳定 data"""

import pytest

from common import i18n
from common.i18n import t
from plugins.image_stitcher import ImageStitchWorker, ImageStitcher


EN_DICT = {
    "plugin.image_stitcher.name": "Image Stitcher",
    "plugin.image_stitcher.description": "Stitch images horizontally or vertically",
    "plugin.image_stitcher.card.select_images": "Select images",
    "plugin.image_stitcher.card.settings": "Stitch settings",
    "plugin.image_stitcher.label.direction": "Direction:",
    "plugin.image_stitcher.label.align": "Alignment:",
    "plugin.image_stitcher.label.bg_color": "Background color:",
    "plugin.image_stitcher.label.output_file": "Output file:",
    "plugin.image_stitcher.placeholder.output_path": "Choose save path...",
    "plugin.image_stitcher.button.browse": "Browse",
    "plugin.image_stitcher.button.start": "Start stitching",
    "plugin.image_stitcher.combo.horizontal": "Horizontal (left to right)",
    "plugin.image_stitcher.combo.vertical": "Vertical (top to bottom)",
    "plugin.image_stitcher.combo.start": "Top/left align",
    "plugin.image_stitcher.combo.center": "Center align",
    "plugin.image_stitcher.combo.end": "Bottom/right align",
    "plugin.image_stitcher.combo.max_size": "Smart scale",
    "plugin.image_stitcher.filter.images": "Images (*.jpg *.png)",
    "plugin.image_stitcher.msg.processing": (
        "Processing: {name} ({index}/{total}), batch {batch}/{batch_total}"
    ),
    "column.filename": "File name",
    "column.dimensions": "Dimensions",
    "column.size": "Size",
    "column.created": "Created",
}


@pytest.fixture
def stitcher_widget(qapp):
    """构造插件 UI（不启动工作线程）"""
    plugin = ImageStitcher.__new__(ImageStitcher)
    plugin.icon = "🧩"
    plugin.name = "图片拼接"
    plugin.description = ""
    plugin.widget = None
    plugin._test_widget = plugin.create_ui()  # 持有引用，避免 Qt 对象被回收
    return plugin


@pytest.fixture
def en_dict():
    """注入临时英文词典，测试结束后恢复原状"""
    saved = dict(i18n.manager._dicts)
    saved_current = i18n.manager.current_language
    i18n.manager._dicts["en"] = dict(EN_DICT)
    yield
    i18n.manager._dicts.clear()
    i18n.manager._dicts.update(saved)
    i18n.set_language(saved_current)


def _header_texts(plugin):
    table = plugin.file_panel.table
    return [
        table.horizontalHeaderItem(i).text()
        for i in range(table.columnCount())
    ]


def test_texts_use_dictionary_zh(stitcher_widget):
    """创建后关键文本等于 zh_CN 词典原文"""
    i18n.set_language("zh_CN")
    plugin = stitcher_widget

    assert plugin.title_label.text() == f"🧩 {t('plugin.image_stitcher.name')}"
    assert plugin.desc_label.text() == t("plugin.image_stitcher.description")
    assert plugin.file_card.title_label.text() == t("plugin.image_stitcher.card.select_images")
    assert plugin.settings_card.title_label.text() == t("plugin.image_stitcher.card.settings")
    assert plugin.direction_label.text() == t("plugin.image_stitcher.label.direction")
    assert plugin.align_label.text() == t("plugin.image_stitcher.label.align")
    assert plugin.bg_color_label.text() == t("plugin.image_stitcher.label.bg_color")
    assert plugin.output_file_label.text() == t("plugin.image_stitcher.label.output_file")
    assert plugin.output_path.placeholderText() == t("plugin.image_stitcher.placeholder.output_path")
    assert plugin.browse_btn.text() == t("plugin.image_stitcher.button.browse")
    assert plugin.action_panel.btn.text() == t("plugin.image_stitcher.button.start")

    # 表头列标签走 column.* 词典
    assert _header_texts(plugin) == [
        t("column.filename"),
        t("column.dimensions"),
        t("column.size"),
        t("column.created"),
    ]


def test_retranslate_switches_to_english(stitcher_widget, en_dict):
    """切换 en 后 retranslate_ui 把关键文本变为英文，切回 zh_CN 恢复"""
    plugin = stitcher_widget

    i18n.set_language("en")
    plugin.retranslate_ui()

    assert plugin.title_label.text() == f"🧩 {t('plugin.image_stitcher.name')}"
    assert plugin.direction_label.text() == "Direction:"
    assert plugin.align_label.text() == "Alignment:"
    assert plugin.output_path.placeholderText() == "Choose save path..."
    assert plugin.browse_btn.text() == "Browse"
    assert plugin.action_panel.btn.text() == "Start stitching"
    assert _header_texts(plugin) == ["File name", "Dimensions", "Size", "Created"]
    assert plugin.file_panel.file_filter == EN_DICT["plugin.image_stitcher.filter.images"]

    i18n.set_language("zh_CN")
    plugin.retranslate_ui()

    assert plugin.direction_label.text() == t("plugin.image_stitcher.label.direction")
    assert plugin.browse_btn.text() == t("plugin.image_stitcher.button.browse")
    assert _header_texts(plugin)[0] == t("column.filename")


def test_combo_keeps_stable_data(stitcher_widget, en_dict):
    """组合框每项 data 非空；切换语言后 currentData 不变"""
    plugin = stitcher_widget

    for combo in (plugin.dir_combo, plugin.align_combo):
        for i in range(combo.count()):
            assert combo.itemData(i)

    assert plugin.dir_combo.currentData() == "vertical"
    assert plugin.align_combo.currentData() == "max_size"

    i18n.set_language("en")
    assert plugin.dir_combo.currentData() == "vertical"
    assert plugin.align_combo.currentData() == "max_size"
    assert plugin.dir_combo.currentText() == EN_DICT["plugin.image_stitcher.combo.vertical"]

    i18n.set_language("zh_CN")
    assert plugin.dir_combo.currentData() == "vertical"
    assert plugin.dir_combo.currentText() == t("plugin.image_stitcher.combo.vertical")


def test_worker_messages_use_dictionary(qapp):
    """worker 状态消息使用词典格式化（不启动线程）"""
    worker = ImageStitchWorker([], "", "horizontal", "start", (255, 255, 255))
    messages = []
    worker.status.connect(messages.append)

    worker._emit_processing_status("C:\\imgs\\a.png", 2, 5, 0, 2)

    assert messages == [t(
        "plugin.image_stitcher.msg.processing",
        name="a.png",
        index=2,
        total=5,
        batch=1,
        batch_total=2,
    )]
