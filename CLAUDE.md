# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

```
toolbox/
├── toolbox.py              # Main application file
├── requirements.txt        # Python dependencies
├── icon.ico               # Application icon
└── test/                 # Test files directory
    ├── test_button.py      # Button UI component tests
    ├── test_icon.py        # Icon and theme tests  
    ├── test_plugin.py      # Plugin system tests
    ├── test_scaling.py     # Image scaling functionality tests
    ├── test_scaling_complete.py  # Complete scaling workflow tests
    ├── test_scaling_function.py  # Scaling function unit tests
    ├── test_sidebar.py     # Sidebar navigation tests
    ├── create_test_images.py  # Test image generator
    ├── check_plugins.py    # Plugin validation tests
    ├── debug_plugins.py    # Plugin debugging utilities
    ├── final_test.py       # End-to-end application tests
    ├── simple_check.py     # Quick system checks
    ├── simple_test.py      # Basic functionality tests
    └── toolbox2.py        # Backup/alternative implementation
```

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python toolbox.py

# Run tests
cd test/
python -m unittest discover -v

# Build executable (Windows, recommended)
pyinstaller toolbox.spec

# Build single-file EXE (Windows, quick)
pyinstaller --onefile --windowed toolbox.py

# Build with UPX compression
pyinstaller --upx-dir=/path/to/upx toolbox.spec
```

## Architecture

`toolbox.py` is a single-file PyQt6 desktop app (工具箱 - "Toolbox") with a plugin-based architecture.

### Core Structure

- `ToolboxWindow` — main window; owns the sidebar (`QVBoxLayout`) and a `QStackedWidget` for tool pages
- `Theme` — dark/light color palette constants; applied via Qt stylesheets
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

## Testing

All test files are located in the `test/` directory. Test files use a `test_` prefix for easy identification. Common test patterns:

- `test_button.py` - Button UI component tests
- `test_icon.py` - Icon and theme tests  
- `test_plugin.py` - Plugin system tests
- `test_scaling.py` - Image scaling functionality tests
- `test_sidebar.py` - Sidebar navigation tests

When adding new features, create corresponding test files in the `test/` directory to maintain code quality and stability.
