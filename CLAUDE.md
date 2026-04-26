# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

```
toolbox/
├── main.py                 # Application entry point
├── toolbox.py              # Main application file (ToolboxWindow class)
├── config.py               # Global configuration (app info, UI, theme)
├── menu_system.py          # Menu system (standalone, for reference)
├── settings_page.py        # Settings page (standalone, for reference)
├── requirements.txt        # Python dependencies
├── favicon.ico             # Application icon
├── plugins/                # Plugin directory
│   ├── image_scaler.py     # Image batch scaling plugin
│   ├── pdf_merger.py      # PDF merge plugin
│   └── pdf_splitter.py    # PDF split plugin
└── test/                   # Test files directory
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
python main.py

# Run tests
cd test/
python -m unittest discover -v

# Generate version info file (before building)
python generate_version_info.py

# Verify packaging dependencies (before building)
python verify_packaging.py

# Build executable (Windows, recommended)
pyinstaller toolbox.spec

# Build single-file EXE (Windows, quick - not recommended, use toolbox.spec instead)
pyinstaller --onefile --windowed main.py

# Build with UPX compression
pyinstaller --upx-dir=/path/to/upx toolbox.spec
```

## Architecture

`toolbox.py` is a single-file PyQt6 desktop app (工具箱 - "Toolbox") with a plugin-based architecture.

### Core Structure

- `ToolboxWindow` — main window; owns the sidebar (`QVBoxLayout`) and a `QStackedWidget` for tool pages
- `Theme` — dark/light color palette constants; applied via Qt stylesheets
- `ToolPlugin` (abstract base) — all tools inherit this; must implement `create_ui() -> QWidget`
- Built-in tools: `ImageCompressor`, `ImageToPDF`, `FormatConverter`, `ImageStitcher`, `PDFMerger`, `PDFSplitter`
- External plugins: auto-discovered from `plugins/` via `importlib`; added dynamically to sidebar and stack
- `SettingsPlugin` — settings page with theme switching (dark/light) and about information
- `WelcomePage` — landing page showing feature cards

### Configuration System

`config.py` centralizes all app configuration:
- `APP_NAME`, `APP_VERSION`, `APP_DESCRIPTION`, `APP_COPYRIGHT` — basic app info
- `APP_WEBSITE_URL`, `APP_WEBSITE_LINK_TEXT` — website link in settings
- `FEATURE_MODULES` — list of feature cards shown on welcome page
- `UI_CONFIG` — window size, sidebar width, corner radius settings
- `THEME_CONFIG` — default theme and color settings
- `WELCOME_CONFIG` — welcome page text content

### Adding a Tool / Plugin

Inherit `ToolPlugin`, implement `create_ui()`, and drop the file in `plugins/`. Example:

```python
from toolbox import ToolPlugin, Card, AnimatedButton
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MyTool(ToolPlugin):
    name = "我的工具"
    description = "工具描述"
    icon = "🔧"
    
    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Hello, World!"))
        return widget
    
    def update_theme(self, theme):
        """Optional: update UI when theme changes"""
        pass
```

### Threading

Long operations run in `QThread` workers (`CompressionWorker`, `PDFWorker`, `PDFMergeWorker`, `PDFSplitWorker`, `FormatConvertWorker`, `ImageStitchWorker`, `ScalingWorker`) that emit progress signals — never block the main thread.

### Theme System

- Two themes: `Theme.DARK` (default) and `Theme.LIGHT`
- Theme switching via `SettingsPlugin` with persistent storage using `QSettings`
- All plugins can implement `update_theme(theme)` to respond to theme changes
- Global stylesheet applied to main window with theme-specific colors

### PDF Conversion

`PDFWorker` tries libraries in order: `img2pdf` → `PyMuPDF` → `PIL`. All three are in `requirements.txt`.
Supports compression with adjustable quality (1-100%) for all three backends.

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

## Packaging

### Important: Dynamic Import Issue

PyInstaller cannot automatically detect modules loaded via `importlib` (dynamic imports). All plugins in the `plugins/` directory must be explicitly listed in `toolbox.spec`'s `hiddenimports` section.

**When adding a new plugin:**
1. Create the plugin file in `plugins/` (e.g., `plugins/my_plugin.py`)
2. Add `'plugins.my_plugin'` to `hiddenimports` in `toolbox.spec`
3. Run `python verify_packaging.py` to verify
4. Rebuild with `pyinstaller toolbox.spec`

See `PACKAGING_GUIDE.md` for detailed troubleshooting and best practices.
