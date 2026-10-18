# ToolBox

![Build and Deploy](https://img.shields.io/github/actions/workflow/status/yansheng836/python-toolbox/main.yml?style=flat&label=Build%20and%20Deploy) ![GitHub commit activity](https://img.shields.io/github/commit-activity/m/yansheng836/python-toolbox) [![GitHub Issues](https://img.shields.io/github/issues/yansheng836/python-toolbox)](https://github.com/yansheng836/python-toolbox/issues) [![GitHub Pull Requests](https://img.shields.io/github/issues-pr/yansheng836/python-toolbox)](https://github.com/yansheng836/python-toolbox/pulls) [![GitHub Tag](https://img.shields.io/github/v/tag/yansheng836/python-toolbox)](https://github.com/yansheng836/python-toolbox/tags) [![GitHub Release](https://img.shields.io/github/v/release/yansheng836/python-toolbox)](https://github.com/yansheng836/python-toolbox/releases) ![GitHub Repo stars](https://img.shields.io/github/stars/yansheng836/python-toolbox) ![GitHub forks](https://img.shields.io/github/forks/yansheng836/python-toolbox) [![Codacy Badge](https://app.codacy.com/project/badge/Grade/0238d17f5c0b438d9b63044c1bac6728)](https://app.codacy.com/gh/yansheng836/python-toolbox/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade) [![GitHub License](https://img.shields.io/github/license/yansheng836/python-toolbox)](https://github.com/yansheng836/python-toolbox/blob/main/LICENSE.txt)

[![ToolBox](README.assets/ToolBox.png)](https://github.com/yansheng836/python-toolbox)

<div align="center">
**Offline · Efficient · Beautiful** — a desktop toolbox for everyday file processing

[Features](#features) · [Screenshots](#screenshots) · [Quick Start](#quick-start) · [Usage Guide](#usage-guide) · [Plugin Development](#plugin-development) · [User Manual](UserManual.en.md)

English | [简体中文](README.md)

</div>

---

## Features

| Icon | Tool | Description |
|:----:|------|-------------|
| 🗜️ | **Image Compressor** | Batch-compress JPG/PNG/WebP with adjustable quality; supports format conversion |
| 🔁 | **Image Format Converter** | Batch-convert between six formats: JPEG/PNG/WebP/BMP/TIFF/GIF |
| 🧩 | **Image Stitcher** | Merge multiple images into one horizontally or vertically, with alignment options |
| 🖨️ | **Image to PDF** | Combine multiple images into a single PDF; supports drag-and-drop reordering |
| 🔍 | **Image Scaler** | Batch-resize images by percentage, width, height, or exact dimensions |
| 📚 | **PDF Merger** | Merge multiple PDFs into one; supports drag-and-drop reordering |
| 📃 | **PDF Splitter** | Split a PDF into images or single-page PDFs; supports custom page counts |
| 🔂 | **File Deduplicator** | Finds duplicate files by size pre-filtering + content hashing; supports rule-based sorting preview |

### Common Features

- 🌙 **Dark/Light themes** — one-click switching with automatic preference memory
- 🖱️ **Drag-and-drop** — most tools accept files dragged directly into the list
- 📊 **File list** — a consistent experience with add/remove/reorder/clear
- 📈 **Progress display** — real-time progress and status updates
- 🔌 **Fully offline** — everything runs locally; no data ever leaves your machine
- 🧩 **Plugin extensibility** — drop a Python file into `plugins/` and it loads automatically
- ↔️ **Collapsible sidebar** — toggle via the collapse button or the `Ctrl+B` shortcut

---

## Screenshots

| Feature | Screenshot |
|:---:|:---:|
| **Home** | ![Home](README.assets/首页.png) |
| **Image Compressor** | ![Image Compressor](README.assets/图片压缩.png) |
| **Image Format Converter** | ![Image Format Converter](README.assets/图片格式转换.png) |
| **Image Stitcher** | ![Image Stitcher](README.assets/图片拼接.png) |
| **Image to PDF** | ![Image to PDF](README.assets/图片转PDF.png) |
| **Image Scaler** | ![Image Scaler](README.assets/图片缩放.png) |
| **PDF Merger** | ![PDF Merger](README.assets/PDF合并.png) |
| **PDF Splitter** | ![PDF Splitter](README.assets/PDF拆分.png) |
| **File Deduplicator** | ![File Deduplicator](README.assets/文件去重.png) |
| **Settings** | ![Settings](README.assets/设置.png) |

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Package overview:**

| Package | Purpose |
|---------|---------|
| PyQt6 | GUI framework |
| Pillow (PIL) | Image processing |
| img2pdf | PDF conversion (primary) |
| PyMuPDF (fitz) | PDF conversion (fallback) |

### 2. Run the Application

```bash
python main.py
```

### 3. Build an EXE (Windows)

```bash
# Recommended: build from the spec file (includes all required modules)
pyinstaller toolbox.spec

# Compress with UPX to reduce size
pyinstaller --upx-dir=/path/to/upx toolbox.spec
```

> ⚠️ **Note**: Always build with `toolbox.spec`. Running `pyinstaller main.py` directly will miss the dynamically loaded plugin modules.

---

## Usage Guide

### Image Compressor

1. Click "Image Compressor" in the left sidebar
2. Add images (multi-select and drag-and-drop supported)
3. Choose the output format (Keep original / JPG / PNG / WebP)
4. Adjust the quality slider (70–85% recommended)
5. Click "Start Compression"

### Image Format Converter

1. Click "Image Format Converter" in the left sidebar
2. Add images and pick a target format (JPEG / PNG / WebP / BMP / TIFF / GIF)
3. Adjust the conversion quality
4. Click "Start Conversion"

### Image Stitcher

1. Click "Image Stitcher" in the left sidebar
2. Add images (at least 2) and arrange their order
3. Choose the stitch direction: horizontal / vertical
4. Set the output image quality
5. Click "Start Stitching"

### Image to PDF

1. Click "Image to PDF" in the left sidebar
2. Add images (drag-and-drop reordering supported)
3. Choose the output quality (High / Standard / Compressed)
4. Choose the output file path
5. Click "Start Conversion"

### Image Scaler

1. Click "Image Scaler" in the left sidebar
2. Add images and choose a scaling mode (percentage / width / height / exact dimensions)
3. Set the scaling parameters and check "Keep aspect ratio"
4. Click "Start Scaling"

### PDF Merger

1. Click "PDF Merger" in the left sidebar
2. Add PDF files (drag-and-drop reordering supported)
3. Arrange the PDF order (move up / move down)
4. Choose the output file path
5. Click "Start Merge"

### PDF Splitter

1. Click "PDF Splitter" in the left sidebar
2. Add one PDF file
3. Choose the output format (single-page PDFs / images)
4. Set the pages-per-file (single-page PDF mode) or the image format (image mode)
5. Click "Start Splitting"

### File Deduplicator

1. Click "File Deduplicator" in the left sidebar
2. Choose a folder to scan; scanning starts automatically (three-stage filtering: file size → quick hash → full hash, for a major speedup)
3. Choose a deduplication rule and click "Sort by Rule" to preview keep/delete markers
4. After reviewing, check the groups you want to clean up
5. Click "Delete Duplicates" and confirm

---

## Plugin Development

ToolBox supports plugins. Drop a Python file into the `plugins/` directory and it will be loaded automatically.

### Creating a Plugin

Create `plugins/my_tool.py`:

```python
# -*- encoding: utf-8 -*-
"""
My tool plugin
"""
from toolbox import ToolPlugin, Card, AnimatedButton, Theme
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MyTool(ToolPlugin):
    name = "我的工具"
    description = "工具描述"
    icon = "🔧"

    def create_ui(self) -> QWidget:
        """Create the tool UI"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Hello, World!"))
        return widget

    def update_theme(self, theme):
        """Respond to theme switches (required)"""
        pass
```

### Plugin Configuration

Add an entry to the `PLUGIN_MODULES` list in `config.py`:

```python
PLUGIN_MODULES = [
    # ... other plugins ...
    {
        "name": "我的工具",
        "icon": "🔧",
        "description": "工具描述",
        "order": 30,  # sort weight; lower values come first
        "module": "plugins.my_tool",
        "class": "MyTool",
    },
]
```

### Existing Plugins

| File | Class | Function |
|------|-------|----------|
| `plugins/image_compressor.py` | `ImageCompressor` | Image compression |
| `plugins/image_format_converter.py` | `FormatConverter` | Image format conversion |
| `plugins/image_stitcher.py` | `ImageStitcher` | Image stitching |
| `plugins/image_to_pdf.py` | `ImageToPDF` | Image to PDF |
| `plugins/image_scaler.py` | `ImageScaler` | Image scaling |
| `plugins/pdf_merger.py` | `PDFMerger` | PDF merging |
| `plugins/pdf_splitter.py` | `PDFSplitter` | PDF splitting |
| `plugins/file_deduplicator.py` | `FileDeduplicator` | File deduplication |

---

## Configuration System

Application configuration lives in `config.py`:

| Setting | Description |
|---------|-------------|
| `APP_NAME`, `APP_VERSION` | Application name and version |
| `APP_DESCRIPTION`, `APP_COPYRIGHT` | Application description and copyright |
| `APP_WEBSITE_URL` | Official website link |
| `PLUGIN_MODULES` | Plugin list (name, icon, description, order) |
| `UI_CONFIG` | Window size, sidebar width, and other UI settings |
| `THEME_CONFIG` | Theme-related configuration |
| `WELCOME_CONFIG` | Welcome page text content |

Edit `config.py` to customize the app's appearance and info without touching the main program.

---

## Building & Release

### Requirements

- Python 3.8+
- Windows (other platforms may work after adjusting the spec file)

### Build Steps

```bash
# 1. Generate the version info file
python generate_version_info.py

# 2. Verify packaging dependencies
python verify_packaging.py

# 3. Build the EXE
pyinstaller toolbox.spec
```

The built EXE is located in the `dist/` directory.

---

## TODO

### Completed ✅

- [x] Image compression (batch, adjustable quality)
- [x] Image format conversion (JPEG/PNG/WebP/BMP/TIFF/GIF)
- [x] Image stitching (horizontal/vertical)
- [x] Image to PDF (multi-image merge)
- [x] Image scaling (percentage / exact dimensions)
- [x] PDF merging (multi-file merge)
- [x] PDF splitting (into images or single-page PDFs)
- [x] File deduplication (by content hash)
- [x] Dark/light theme switching
- [x] Automatic plugin discovery and loading

### Planned 🔨

- [ ] Batch image watermarking (text or image watermark)
- [ ] Batch image rotation/flipping
- [ ] Batch image cropping
- [ ] Batch file renaming (regex, numbering, and date rules)

### Pending Improvements

None yet

---

PRs are welcome for new plugins and features!

---

## License

This project is open source under the [MIT License](./LICENSE.txt). Feel free to use and contribute.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yansheng836/python-toolbox&type=Timeline)](https://star-history.com/#yansheng836/python-toolbox&Timeline)

## Visitors

<a href="https://info.flagcounter.com/nYwQ"><img src="https://s01.flagcounter.com/count2/nYwQ/bg_FFFFFF/txt_000000/border_CCCCCC/columns_2/maxflags_12/viewers_0/labels_1/pageviews_1/flags_0/percent_0/" alt="Flag Counter" border="0"></a>

---

<div align="center">
**ToolBox** — Making file processing simpler 🚀
</div>
