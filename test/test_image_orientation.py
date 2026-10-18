# -*- encoding: utf-8 -*-
"""
图片处理模块的 EXIF 方向回归测试
"""

from pathlib import Path

import pytest
from PIL import Image

from common.utils import get_image_size
from plugins.image_compressor import CompressionWorker
from plugins.image_format_converter import FormatConvertWorker
from plugins.image_scaler import ScalingWorker
from plugins.image_stitcher import ImageStitchWorker


def _make_orientation_six_jpeg(path, size=(120, 60), color=(220, 40, 40)):
    """创建像素横向、EXIF 显示为竖向的 JPEG。"""
    exif = Image.Exif()
    exif[274] = 6
    image = Image.new("RGB", size, color)
    image.save(path, exif=exif)
    image.close()


def _run_worker(worker):
    """同步运行 worker，返回完成信号结果。"""
    results = []
    worker.finished.connect(lambda success, message: results.append((success, message)))
    worker.run()
    assert results, "worker 未发出完成信号"
    return results[-1]


def test_get_image_size_reports_exif_oriented_dimensions(tmp_path):
    """尺寸显示应使用 EXIF 校正后的宽高。"""
    source = tmp_path / "portrait.jpg"
    _make_orientation_six_jpeg(source)

    assert get_image_size(str(source)) == "60 x 120"


def test_compressor_applies_exif_orientation(tmp_path):
    """压缩后的 JPEG 应包含校正后的竖向像素，而不是依赖 EXIF 标记。"""
    source = tmp_path / "portrait.jpg"
    _make_orientation_six_jpeg(source)
    output_dir = tmp_path / "compressed"

    success, message = _run_worker(
        CompressionWorker([str(source)], str(output_dir), "JPG", 75)
    )

    assert success, message
    output = next(output_dir.glob("*.jpg"))
    with Image.open(output) as image:
        assert image.size == (60, 120)
        assert image.getexif().get(274) is None


def test_format_converter_applies_exif_orientation(tmp_path):
    """格式转换应成功保存校正后的图像，而不是保存已关闭的源对象。"""
    source = tmp_path / "portrait.jpg"
    _make_orientation_six_jpeg(source)
    output_dir = tmp_path / "converted"

    success, message = _run_worker(
        FormatConvertWorker([str(source)], str(output_dir), "JPEG")
    )

    assert success, message
    output = next(output_dir.glob("*.jpg"))
    with Image.open(output) as image:
        assert image.size == (60, 120)
        assert image.getexif().get(274) is None


def test_scaler_uses_exif_oriented_aspect_ratio(tmp_path):
    """指定宽度缩放应按校正后的竖向宽高比计算高度。"""
    source = tmp_path / "portrait.jpg"
    _make_orientation_six_jpeg(source)
    output_dir = tmp_path / "scaled"

    success, message = _run_worker(
        ScalingWorker(
            [str(source)], str(output_dir), "width", 0, 85, True, width=60
        )
    )

    assert success, message
    output = next(output_dir.glob("*_scaled.*"))
    with Image.open(output) as image:
        assert image.size == (60, 120)
        assert image.getexif().get(274) is None


def test_stitcher_uses_exif_oriented_dimensions(tmp_path):
    """横向拼接应将 EXIF 竖图按校正后的宽度布局。"""
    portrait = tmp_path / "portrait.jpg"
    square = tmp_path / "square.png"
    output = tmp_path / "stitched.png"
    _make_orientation_six_jpeg(portrait)
    square_image = Image.new("RGB", (120, 120), (40, 80, 220))
    square_image.save(square)
    square_image.close()

    success, message = _run_worker(
        ImageStitchWorker(
            [str(portrait), str(square)], str(output), "horizontal", "start",
            (255, 255, 255),
        )
    )

    assert success, message
    with Image.open(output) as image:
        assert image.size == (180, 120)
