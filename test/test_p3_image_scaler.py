# -*- encoding: utf-8 -*-
"""
P3 i18n 测试 — image_scaler 插件

覆盖：中文词典文本、英文切换 retranslate_ui、组合框稳定 data、worker 消息。
运行：cd test && python -m pytest test_p3_image_scaler.py -v
"""

import pytest

from common import i18n
from common.i18n import t
from plugins.image_scaler import ImageScaler, ScalingWorker


@pytest.fixture
def scaler(qapp):
    """构造 ImageScaler 插件与 widget；create_ui() 会写入 plugin.widget"""
    from toolbox import Theme

    i18n.set_language("zh_CN")
    plugin = ImageScaler.__new__(ImageScaler)
    plugin.icon = "🔍"
    plugin.name = t("plugin.image_scaler.name")
    plugin.description = t("plugin.image_scaler.description")
    plugin.widget = None
    plugin.theme = Theme.DARK
    widget = plugin.create_ui()
    yield plugin, widget
    widget.deleteLater()
    i18n.set_language("zh_CN")


@pytest.fixture
def en_dict():
    """注入临时英文词典，测试结束后恢复原词典与语言"""
    saved = dict(i18n.manager._dicts)
    saved_current = i18n.manager.current_language
    i18n.manager._dicts["en"] = {
        "plugin.image_scaler.name": "Image Scaler",
        "plugin.image_scaler.description": "Batch resize images",
        "plugin.image_scaler.card.select_images": "Select Images",
        "plugin.image_scaler.card.settings": "Scaling Settings",
        "plugin.image_scaler.label.scale_type": "Scale mode:",
        "plugin.image_scaler.label.scale_value": "Scale value:",
        "plugin.image_scaler.label.width": "Width:",
        "plugin.image_scaler.label.height": "Height:",
        "plugin.image_scaler.checkbox.maintain_aspect": "Maintain aspect ratio",
        "plugin.image_scaler.label.quality": "Image quality:",
        "plugin.image_scaler.label.output_dir": "Output directory:",
        "plugin.image_scaler.placeholder.output_dir": "Saved next to the source image",
        "plugin.image_scaler.button.browse": "Browse",
        "plugin.image_scaler.button.start": "Start Scaling",
        "plugin.image_scaler.combo.percent": "Percentage",
        "plugin.image_scaler.combo.width": "Specify width",
        "plugin.image_scaler.combo.height": "Specify height",
        "plugin.image_scaler.combo.95": "High quality (95)",
        "plugin.image_scaler.combo.85": "Standard (85)",
        "plugin.image_scaler.combo.75": "Smaller file (75)",
        "plugin.image_scaler.combo.50": "Smallest file (50)",
        "plugin.image_scaler.suffix.auto": " (auto)",
        "plugin.image_scaler.filter.images": "Image files (*.png *.jpg);;All files (*.*)",
    }
    yield
    i18n.manager._dicts.clear()
    i18n.manager._dicts.update(saved)
    i18n.set_language(saved_current)


def test_texts_use_dictionary_zh(scaler):
    """创建后关键文本等于 zh_CN 词典原文"""
    _, w = scaler

    assert w.title_label.text() == f"🔍 {t('plugin.image_scaler.name')}"
    assert w.desc_label.text() == t("plugin.image_scaler.description")
    assert w.file_card.title_label.text() == t("plugin.image_scaler.card.select_images")
    assert w.settings_card.title_label.text() == t("plugin.image_scaler.card.settings")
    assert w.scale_type_label.text() == t("plugin.image_scaler.label.scale_type")
    assert w.scale_value_label.text() == t("plugin.image_scaler.label.scale_value")
    assert w.width_label.text() == t("plugin.image_scaler.label.width")
    assert w.height_label.text() == t("plugin.image_scaler.label.height")
    assert w.maintain_aspect.text() == t(
        "plugin.image_scaler.checkbox.maintain_aspect"
    )
    assert w.quality_label.text() == t("plugin.image_scaler.label.quality")
    assert w.output_dir_label.text() == t("plugin.image_scaler.label.output_dir")
    assert w.output_path.placeholderText() == t(
        "plugin.image_scaler.placeholder.output_dir"
    )
    assert w.browse_btn.text() == t("plugin.image_scaler.button.browse")
    assert w.action_panel.btn.text() == t("plugin.image_scaler.button.start")
    assert w.file_panel.file_filter == t("plugin.image_scaler.filter.images")

    assert [w.scale_type_combo.itemText(i) for i in range(3)] == [
        t("plugin.image_scaler.combo.percent"),
        t("plugin.image_scaler.combo.width"),
        t("plugin.image_scaler.combo.height"),
    ]
    assert [w.quality_combo.itemText(i) for i in range(4)] == [
        t("plugin.image_scaler.combo.95"),
        t("plugin.image_scaler.combo.85"),
        t("plugin.image_scaler.combo.75"),
        t("plugin.image_scaler.combo.50"),
    ]


def test_retranslate_switches_to_english(scaler, en_dict):
    """切换到 en 后 retranslate_ui() 将关键文本替换为英文，切回后恢复中文"""
    plugin, w = scaler

    i18n.set_language("en")
    plugin.retranslate_ui()

    assert w.title_label.text() == "🔍 Image Scaler"
    assert w.desc_label.text() == "Batch resize images"
    assert w.file_card.title_label.text() == "Select Images"
    assert w.settings_card.title_label.text() == "Scaling Settings"
    assert w.scale_type_label.text() == "Scale mode:"
    assert w.browse_btn.text() == "Browse"
    assert w.action_panel.btn.text() == "Start Scaling"
    assert w.output_path.placeholderText() == "Saved next to the source image"
    assert w.file_panel.file_filter == "Image files (*.png *.jpg);;All files (*.*)"
    # 组合框由 bind_combo 自动重放
    assert w.scale_type_combo.itemText(0) == "Percentage"

    i18n.set_language("zh_CN")
    plugin.retranslate_ui()

    assert w.title_label.text() == f"🔍 {t('plugin.image_scaler.name')}"
    assert w.scale_type_label.text() == t("plugin.image_scaler.label.scale_type")
    assert w.browse_btn.text() == t("plugin.image_scaler.button.browse")


def test_combo_keeps_stable_data(scaler, en_dict):
    """组合框每项 data 非空；切语言后 currentData 不变"""
    plugin, w = scaler

    for i in range(w.scale_type_combo.count()):
        assert w.scale_type_combo.itemData(i) is not None
    for i in range(w.quality_combo.count()):
        assert isinstance(w.quality_combo.itemData(i), int)

    w.scale_type_combo.setCurrentIndex(w.scale_type_combo.findData("width"))
    w.quality_combo.setCurrentIndex(w.quality_combo.findData(75))
    assert w.scale_type_combo.currentData() == "width"
    assert w.quality_combo.currentData() == 75

    i18n.set_language("en")
    plugin.retranslate_ui()

    assert w.scale_type_combo.currentData() == "width"
    assert w.quality_combo.currentData() == 75
    assert w.scale_type_combo.currentText() == "Specify width"
    assert w.quality_combo.currentText() == "Smaller file (75)"


def test_worker_emits_dictionary_message(qapp, tmp_path, test_images):
    """worker 成功消息走 t() 词典（同步执行 run，不启动线程）"""
    i18n.set_language("zh_CN")
    worker = ScalingWorker(
        input_files=[test_images[0]],
        output_dir=str(tmp_path),
        scale_type="percent",
        scale_value=50,
        quality=85,
        maintain_aspect=True,
    )
    messages = []
    worker.result.connect(lambda ok, msg: messages.append((ok, msg)))

    worker.run()

    assert messages == [(True, t("plugin.image_scaler.msg.success", count=1, total=1))]
