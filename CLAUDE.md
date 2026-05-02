# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Standards

### Code Reuse (MANDATORY)

**Rule: If identical or similar code appears 2+ times, you MUST abstract it into a shared class or method.**

- Before writing new code, check if similar logic already exists in `common/`, `toolbox.py`, or other plugins
- Duplicated code increases maintenance burden exponentially — every bug fix must be applied in multiple places
- Shared components should be placed in `common/` directory or the base class (`ToolPlugin`, `Theme`)
- When refactoring, update ALL occurrences that use the duplicated pattern, not just new code

### UI Styling and Theme Compliance (MANDATORY)

**Rule: When designing styles (especially colors), you MUST consider the current background color to ensure text remains readable.**

- **Dark theme background**: `#2d2d2d` (panels), `#1e1e1e` (window), `#3d3d3d` (sidebar)
- **Light theme background**: `#f5f5f5` (panels), `#ffffff` (window), `#e8e8e8` (sidebar)
- **Text colors**: Use `Theme.TEXT_PRIMARY`, `Theme.TEXT_SECONDARY` — NEVER hardcode text colors
- **Contrast check**: After applying styles, verify text is readable in BOTH themes
- **Common pitfalls**:
  - Setting dark text on dark background (or light on light)
  - Using `QMessageBox` with custom styles that don't adapt to theme
  - Forgetting that `QPushButton` text inherits parent widget's color in some Qt styles
  - Gradient buttons must define contrasting text colors for all states (normal, hover, pressed)

### File Encoding and Line Endings

- **File Encoding**: All Python files (new or modified) MUST use UTF-8 encoding
- **Line Endings**: All Python files (new or modified) MUST use LF (`\n`) line endings, not CRLF (`\r\n`)
- Configure your editor to use UTF-8 and LF for this project

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
│   ├── pdf_splitter.py    # PDF split plugin
│   └── file_deduplicator.py # File deduplication plugin (by content hash)
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

Long operations run in `QThread` workers that emit progress signals — never block the main thread.

**Note:** Currently each plugin defines its own Worker class with similar structure. When adding new plugins, consider whether a shared base Worker class can be created in `common/` to reduce duplication.

### Code Reuse Guidelines

**MANDATORY RULE: If identical or similar code appears 2+ times, you MUST abstract it into a shared class or method immediately.**

This is not a suggestion — it is a strict requirement to prevent maintenance debt. Every duplication:
- Requires bug fixes in multiple places
- Increases likelihood of inconsistent behavior
- Makes future refactoring more dangerous

#### Shared Components (in `toolbox.py` or `common/`)

| Component | Location | Purpose |
|-----------|----------|---------|
| `ToolPlugin` | `toolbox.py` | Base class for all plugins |
| `Theme` | `toolbox.py` | Dark/light color palettes + **ALL color constants** |
| `AnimatedButton` | `toolbox.py` | Reusable button with hover effects |
| `Card` | `toolbox.py` | Card container with title/content layout |
| `DragDropHandler` | `toolbox.py` | Drag-and-drop utility |
| `SidebarButton` | `toolbox.py` | Sidebar navigation button |
| `FileListPanel` | `common/file_list_panel.py` | Reusable file list table with buttons |
| `get_image_size`, `get_file_size` | `common/utils.py` | Image size and file size helper functions |
| `BaseWorker` | `common/base_worker.py` | Base QThread worker with standard signals |
| `MessageUtils` | `common/message_utils.py` | Themed message boxes and dialogs |

**Use these shared components whenever possible instead of reimplementing similar functionality.**

#### Patterns That MUST Be Abstracted (Duplicated 2+ Times)

| Pattern | Duplicated In | Action Required |
|---------|---------------|-----------------|
| Worker Classes | All plugins | Use `BaseWorker` from `common/` |
| Image Helper Functions | 4+ plugins | Use `get_image_size()` from `common/utils.py` |
| Button/Progress Bar Styles | All plugins | Define in `Theme` class, use `Theme.get_button_style()` |
| `apply_theme()` Method | All plugins | Implement in `ToolPlugin` base class |
| Import Fallback Pattern | All plugins | Document once, reference pattern |
| File size formatting | 3+ plugins | Add `format_file_size()` to `common/utils.py` |
| Status message updates | All plugins | Use shared helper method |

**Before adding a new plugin, check this table. If your plugin needs any of these patterns, use the shared component.**

#### When Adding New Plugins

1. **Check `FileListPanel` first** — If the plugin needs a file list with add/remove/clear buttons, use `FileListPanel` from `common/file_list_panel.py` instead of building custom UI.
2. **Use shared UI components** — Import `AnimatedButton`, `Card` from `toolbox` instead of creating custom buttons/cards.
3. **Reuse helper functions** — Check if needed utilities already exist in `common/` before writing new ones.
4. **Follow existing patterns** — If you must write plugin-specific code, follow the patterns established by existing plugins for consistency.
5. **Implement `update_theme()` properly** — MUST update ALL widgets that have custom styles. Use `Theme.get_button_style()` for gradient buttons.
6. **Test in both themes** — Verify all text is readable in both dark and light themes before marking work complete.

#### Creating New Shared Components

When you identify code that should be shared:

1. Create new shared code in `common/` directory (e.g., `common/utils.py`, `common/base_worker.py`)
2. Update `ToolPlugin` base class in `toolbox.py` if the shared code is fundamental to all plugins
3. Update this CLAUDE.md file to document the new shared component in the table above
4. Refactor existing plugins to use the new shared component (in a separate commit)

### Theme System

- Two themes: `Theme.DARK` (default) and `Theme.LIGHT`
- Theme switching via `SettingsPlugin` with persistent storage using `QSettings`
- All plugins MUST implement `update_theme(theme)` to respond to theme changes
- Global stylesheet applied to main window with theme-specific colors

#### Color Constants (Defined in `Theme` class)

| Constant | Dark Theme | Light Theme | Usage |
|----------|------------|-------------|-------|
| `BG_PRIMARY` | `#1e1e1e` | `#ffffff` | Main window background |
| `BG_SECONDARY` | `#2d2d2d` | `#f5f5f5` | Panels, content areas |
| `BG_TERTIARY` | `#3d3d3d` | `#e8e8e8` | Sidebar, toolbars |
| `TEXT_PRIMARY` | `#ffffff` | `#000000` | Primary text |
| `TEXT_SECONDARY` | `#aaaaaa` | `#666666` | Secondary text |
| `TEXT_DISABLED` | `#666666` | `#999999` | Disabled text |
| `ACCENT_PRIMARY` | `#4dabf7` | `#1c7ed6` | Links, highlights |
| `SUCCESS` | `#51cf66` | `#2f9e44` | Success messages |
| `WARNING` | `#ffd43b` | `#f08c00` | Warning messages |
| `ERROR` | `#ff6b6b` | `#e03131` | Error messages |

#### Theme Compliance Rules (MANDATORY)

1. **NEVER hardcode colors** — Always use `Theme.COLOR_NAME` or `theme["key"]`
2. **Text must contrast with background** — Use `TEXT_PRIMARY`/`TEXT_SECONDARY` for all text
3. **Test in BOTH themes** — Every style change must be verified in dark AND light mode
4. **QMessageBox styling** — Use `MessageUtils.show_info()`, `MessageUtils.show_error()` etc. from `common/message_utils.py` instead of raw `QMessageBox` to ensure theme compliance
5. **Gradient buttons** — Text color must be explicitly set for all states:
   ```python
   # GOOD: Explicit text color for each state
   button.setStyleSheet(f"""
       QPushButton {{ color: {Theme.TEXT_PRIMARY}; }}
       QPushButton:hover {{ color: {Theme.TEXT_PRIMARY}; }}
   """)
   
   # BAD: Depends on inheritance, may be unreadable
   button.setStyleSheet("background: qlineargradient(...);")
   ```
6. **Status labels** — Use appropriate color constants:
   - Success: `Theme.SUCCESS`
   - Error: `Theme.ERROR`
   - Warning: `Theme.WARNING`
   - Info: `Theme.ACCENT_PRIMARY`

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
