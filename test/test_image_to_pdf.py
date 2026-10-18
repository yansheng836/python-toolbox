# -*- encoding: utf-8 -*-
"""
图片转 PDF 的方向和页面比例测试
"""

import pytest
from PIL import Image

fitz = pytest.importorskip("pymupdf")

from plugins.image_to_pdf import PDFWorker


def _run_worker(files, output, page_size):
    """直接运行 PDF worker，返回完成信号结果。"""
    results = []
    worker = PDFWorker(files, str(output), page_size, compress=False)
    worker.result.connect(lambda success, message: results.append((success, message)))
    worker.run()
    assert results, "PDF worker 未发出完成信号"
    return results[-1]


def _render_non_white_bbox(page):
    """获取 PDF 页面中非白色内容的边界框。"""
    pixmap = page.get_pixmap(alpha=False)
    samples = pixmap.samples
    channels = pixmap.n
    points = []
    for y in range(pixmap.height):
        for x in range(pixmap.width):
            offset = (y * pixmap.width + x) * channels
            pixel = samples[offset:offset + 3]
            if min(pixel) < 240:
                points.append((x, y))
    assert points, "PDF 页面没有检测到非白色内容"
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def test_exif_orientation_is_applied_before_pdf_conversion(tmp_path):
    """EXIF Orientation=6 的横向像素应生成竖向 PDF 页面。"""
    source = tmp_path / "portrait-with-exif.jpg"
    output = tmp_path / "portrait.pdf"
    exif = Image.Exif()
    exif[274] = 6
    image = Image.new("RGB", (120, 60), (220, 40, 40))
    image.save(source, exif=exif)
    image.close()

    success, message = _run_worker([str(source)], output, "original")

    assert success, message
    with fitz.open(output) as document:
        page = document[0]
        assert page.rect.height > page.rect.width


def test_image_without_exif_keeps_landscape_orientation(tmp_path):
    """没有 EXIF 方向的横向图片应保持横向 PDF 页面。"""
    source = tmp_path / "landscape.jpg"
    output = tmp_path / "landscape.pdf"
    image = Image.new("RGB", (120, 60), (40, 80, 220))
    image.save(source)
    image.close()

    success, message = _run_worker([str(source)], output, "original")

    assert success, message
    with fitz.open(output) as document:
        page = document[0]
        assert page.rect.width > page.rect.height


def test_smart_scaling_uses_oriented_dimensions(tmp_path):
    """智能缩放应使用应用 EXIF 方向后的图片宽度。"""
    portrait_source = tmp_path / "portrait-with-exif.jpg"
    landscape_source = tmp_path / "landscape.jpg"
    output = tmp_path / "smart-scaled.pdf"
    exif = Image.Exif()
    exif[274] = 6
    portrait = Image.new("RGB", (120, 60), (220, 40, 40))
    portrait.save(portrait_source, exif=exif)
    portrait.close()
    landscape = Image.new("RGB", (100, 80), (40, 80, 220))
    landscape.save(landscape_source)
    landscape.close()

    success, message = _run_worker(
        [str(portrait_source), str(landscape_source)], output, "smart"
    )

    assert success, message
    with fitz.open(output) as document:
        portrait_page = document[0]
        assert portrait_page.rect.height > portrait_page.rect.width
        assert portrait_page.rect.width == pytest.approx(75, abs=0.1)
        assert portrait_page.rect.height == pytest.approx(150, abs=0.1)


@pytest.mark.parametrize("page_size", ["A4", "A3"])
def test_fixed_page_size_preserves_image_aspect_ratio(tmp_path, page_size):
    """A4 和 A3 页面应保持图片比例并在白色页面中留白。"""
    source = tmp_path / f"wide-{page_size}.png"
    output = tmp_path / f"wide-{page_size}.pdf"
    image = Image.new("RGB", (400, 200), (30, 180, 70))
    image.save(source)
    image.close()

    success, message = _run_worker([str(source)], output, page_size)

    assert success, message
    with fitz.open(output) as document:
        page = document[0]
        expected_size = {
            "A4": (595, 842),
            "A3": (842, 1191),
        }[page_size]
        assert page.rect.width == pytest.approx(expected_size[0], abs=0.1)
        assert page.rect.height == pytest.approx(expected_size[1], abs=0.1)
        bbox = _render_non_white_bbox(page)
        content_width = bbox[2] - bbox[0] + 1
        content_height = bbox[3] - bbox[1] + 1
        assert content_width / content_height == pytest.approx(2.0, abs=0.15)
        assert bbox[1] > 0 or bbox[3] < page.rect.height - 1
