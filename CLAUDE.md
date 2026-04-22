# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python toolbox.py

# Build executable (Windows, recommended)
pyinstaller toolbox.spec

# Build single-file EXE (Windows, quick)
pyinstaller --onefile --windowed toolbox.py

# Build with UPX compression
pyinstaller --upx-dir=/path/to/upx toolbox.spec
```

> Note: The built executable currently has runtime issues (packaging succeeds but the app won't run). `toolbox2.py` is an older/alternative version.

## Architecture

`toolbox.py` is a single-file PyQt6 desktop app (工具箱 - "Toolbox") with a plugin-based architecture.

### Core Structure

- `ToolboxWindow` — main window; owns the sidebar (`QVBoxLayout`) and a `QStackedWidget` for tool pages
- `ThemeManager` / `Theme` — dark/light palette; generates Qt stylesheets
- `ToolPlugin` (abstract base) — all tools inherit this; must implement `create_ui() -> QWidget`
- Built-in tools: `ImageCompressor`, `ImageToPDF`
- External plugins: auto-discovered from `plugins/` via `importlib`; added dynamically to sidebar and stack

### Adding a Tool / Plugin

Inherit `ToolPlugin`, implement `create_ui()`, and drop the file in `plugins/`. See `plugins/my_tool.py` for a minimal example.

### Threading

Long operations run in `QThread` workers (`CompressionWorker`, `PDFWorker`) that emit progress signals — never block the main thread.

### PDF Conversion

`PDFWorker` tries libraries in order: `img2pdf` → `PyMuPDF` → `PIL`. All three are in `requirements.txt`.

### Key Dependencies

| Package | Role |
|---------|------|
| PyQt6 | GUI |
| Pillow | Image processing |
| img2pdf | Primary PDF conversion |
| PyMuPDF (fitz) | Fallback PDF conversion |
| pyinstaller | Build executables |
