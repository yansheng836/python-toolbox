# -*- encoding: utf-8 -*-
"""
图片格式转换插件 i18n 迁移测试

覆盖：zh_CN 词典文本、retranslate_ui 英中切换、组合框稳定 data、
worker 完成/失败消息走词典（不启动线程）。
"""

import pytest

from PIL import Image

from common import i18n
from plugins.image_format_converter import FormatConverter, FormatConvertWorker
from toolbox import Theme


@pytest.fixture(autouse=True)
def reset_language():
    """每个用例从 zh_CN 开始，避免语言状态泄漏"""
    i18n.set_language("zh_CN")
    yield
    i18n.set_language("zh_CN")


@pytest.fixture
def converter(qapp):
    plugin = FormatConverter.__new__(FormatConverter)
    plugin.id = "image_format_converter"
    plugin.icon = "🔁"
    plugin.name = "图片格式转换"
    plugin.description = "批量转换图片格式，支持JPEG/PNG/WebP/BMP/TIFF/GIF"
    plugin.widget = None
    plugin.theme = Theme.DARK
    widget = plugin.create_ui()
    yield plugin, widget
    widget.deleteLater()


@pytest.fixture
def en_dict():
    """注入临时 en 词典，用例结束后恢复原状"""
    saved = dict(i18n.manager._dicts)
    saved_current = i18n.manager.current_language
    i18n.manager._dicts["en"] = {
        "plugin.image_format_converter.name": "Image Format Converter",
        "plugin.image_format_converter.description": "Batch convert image formats",
        "plugin.image_format_converter.card.select_images": "Select Images",
        "plugin.image_format_converter.card.settings": "Conversion Settings",
        "plugin.image_format_converter.label.target_format": "Target format:",
        "plugin.image_format_converter.label.output_dir": "Output directory:",
        "plugin.image_format_converter.placeholder.output_dir": "Save next to originals by default",
        "plugin.image_format_converter.button.browse": "Browse",
        "plugin.image_format_converter.button.start": "Start Conversion",
        "plugin.image_format_converter.dialog.select_output_dir": "Select Output Directory",
        "plugin.image_format_converter.filter.images": (
            "Image files (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif *.gif)"
        ),
        "plugin.image_format_converter.msg.converting": "Converting: {name}",
        "plugin.image_format_converter.msg.success": "Converted {count} images!",
        "plugin.image_format_converter.error.convert_failed": "Conversion failed: {error}",
    }
    yield
    i18n.manager._dicts.clear()
    i18n.manager._dicts.update(saved)
    i18n.set_language(saved_current)


def test_texts_use_dictionary_zh(converter):
    """创建后关键文本等于 zh_CN 词典原文"""
    plugin, _ = converter
    assert plugin.title_label.text() == "🔁 图片格式转换"
    assert plugin.title_label.text() == (
        f"{plugin.icon} {i18n.t('plugin.image_format_converter.name')}"
    )
    assert plugin.desc_label.text() == i18n.t(
        "plugin.image_format_converter.description")
    assert plugin.file_card.title_label.text() == "选择图片"
    assert plugin.settings_card.title_label.text() == "转换设置"
    assert plugin.target_format_label.text() == "目标格式:"
    assert plugin.output_dir_label.text() == "输出目录:"
    assert plugin.output_path.placeholderText() == "默认保存到原图目录"
    assert plugin.browse_btn.text() == "浏览"
    assert plugin.action_panel.btn.text() == "开始转换"
    assert plugin.file_panel.file_filter == (
        "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif *.gif)"
    )


def test_retranslate_switches_to_english(converter, en_dict):
    """切到 en 后 retranslate_ui 更新关键文本，切回 zh_CN 恢复"""
    plugin, _ = converter
    i18n.set_language("en")
    plugin.retranslate_ui()

    assert plugin.title_label.text() == "🔁 Image Format Converter"
    assert plugin.desc_label.text() == "Batch convert image formats"
    assert plugin.file_card.title_label.text() == "Select Images"
    assert plugin.settings_card.title_label.text() == "Conversion Settings"
    assert plugin.target_format_label.text() == "Target format:"
    assert plugin.output_dir_label.text() == "Output directory:"
    assert plugin.output_path.placeholderText() == (
        "Save next to originals by default")
    assert plugin.browse_btn.text() == "Browse"
    assert plugin.action_panel.btn.text() == "Start Conversion"
    assert "Image files" in plugin.file_panel.file_filter

    i18n.set_language("zh_CN")
    plugin.retranslate_ui()
    assert plugin.title_label.text() == "🔁 图片格式转换"
    assert plugin.file_card.title_label.text() == "选择图片"
    assert plugin.target_format_label.text() == "目标格式:"
    assert plugin.output_path.placeholderText() == "默认保存到原图目录"
    assert plugin.browse_btn.text() == "浏览"
    assert plugin.action_panel.btn.text() == "开始转换"


def test_combo_keeps_stable_data(converter, en_dict):
    """组合框每项 data 非空，切换语言后 currentData/文本不变"""
    plugin, _ = converter
    combo = plugin.fmt_combo
    for i in range(combo.count()):
        assert combo.itemData(i)

    idx = combo.findData("WebP")
    assert idx >= 0
    combo.setCurrentIndex(idx)

    i18n.set_language("en")
    plugin.retranslate_ui()
    assert plugin.fmt_combo.currentData() == "WebP"
    assert plugin.fmt_combo.currentText() == "WebP"


def test_worker_success_message_uses_dictionary(qapp, tmp_path):
    """worker 成功消息走词典（不启动线程，直接调用 run）"""
    worker = FormatConvertWorker([], str(tmp_path), "PNG")
    captured = []
    worker.result.connect(lambda ok, msg: captured.append((ok, msg)))

    worker.run()

    assert captured == [(True, "成功转换 0 张图片！")]


def test_worker_error_message_uses_dictionary(qapp, tmp_path, monkeypatch):
    """worker 失败消息走词典占位符（H8：单文件失败汇总，不中止整批）"""
    import plugins.image_format_converter as module

    def broken_loader(_path):
        raise ValueError("boom")

    monkeypatch.setattr(module, "load_oriented_image", broken_loader)
    worker = FormatConvertWorker(["fake.png"], str(tmp_path), "PNG")
    captured = []
    worker.result.connect(lambda ok, msg: captured.append((ok, msg)))

    worker.run()

    assert len(captured) == 1
    ok, msg = captured[0]
    assert ok is False
    # 汇总消息包含成功/失败计数与失败文件明细
    assert "成功 0 张，失败 1 张" in msg
    assert "fake.png: boom" in msg


def test_no_overwrite_when_output_conflicts_with_source(qapp, tmp_path):
    """H3：同目录同格式转换不得静默覆盖源文件（改写到 _converted 后缀）"""
    src = tmp_path / "a.png"
    Image.new("RGB", (80, 60), (10, 20, 30)).save(src)
    original_bytes = src.read_bytes()

    # 目标格式 PNG 且未指定输出目录 → 输出路径与源文件同名
    worker = FormatConvertWorker([str(src)], None, "PNG")
    captured = []
    worker.result.connect(lambda ok, msg: captured.append((ok, msg)))
    worker.run()

    assert captured and captured[0][0] is True
    # 源文件内容未被改写
    assert src.read_bytes() == original_bytes
    # 转换结果落到 _converted 后缀文件
    assert (tmp_path / "a_converted.png").exists()


def test_overwrite_allowed_when_output_dir_differs(qapp, tmp_path):
    """H3：指定独立输出目录时可正常输出，不加后缀"""
    src_dir = tmp_path / "src"
    out_dir = tmp_path / "out"
    src_dir.mkdir()
    out_dir.mkdir()
    src = src_dir / "pic.png"
    Image.new("RGB", (80, 60), (1, 2, 3)).save(src)

    worker = FormatConvertWorker([str(src)], str(out_dir), "PNG")
    captured = []
    worker.result.connect(lambda ok, msg: captured.append((ok, msg)))
    worker.run()

    assert captured and captured[0][0] is True
    assert (out_dir / "pic.png").exists()
