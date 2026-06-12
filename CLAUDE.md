# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Quick Reference — Mandatory Rules

These rules MUST be followed. Violations will cause bugs or maintenance debt.

| # | Rule | Section |
|---|------|---------|
| 1 | After modifying any Python file, run syntax & import checks before marking complete | [Syntax Check](#syntax-check-after-modification-mandatory) |
| 2 | If identical/similar code appears 2+ times, abstract it into a shared class/method | [Code Reuse](#code-reuse-mandatory) |
| 3 | NEVER hardcode colors; use `Theme.*` constants; verify text readable in both themes | [Theme Compliance](#theme-system) |
| 4 | All Python files MUST use UTF-8 encoding and LF (`\n`) line endings | [File Encoding](#file-encoding-and-line-endings) |
| 5 | Only catch meaningful exceptions; always report errors; no try-catch for project-internal imports | [Exception Handling](#exception-handling-mandatory) |
| 6 | Module availability flags (`PIL_AVAILABLE`, etc.) must be imported from `common/utils.py`, never re-declared | [Exception Handling](#exception-handling-mandatory) |
| 7 | Informational text MUST use `SelectableLabel` to support copying | [Text Copyability](#text-copyability-mandatory) |
| 8 | UI components MUST support responsive layout (Expanding策略, 动态高度) | [Responsive Layout](#responsive-layout-mandatory) |
| 9 | When writing/overwriting output files, check if the file is locked/occupied before processing | [File Operations](#file-operations-mandatory) |
| 10 | When deleting temporary files, check if the file exists first to avoid error spam | [File Operations](#file-operations-mandatory) |
| 11 | When processing files/images, use context managers and release resources properly | [Performance Optimization](#performance-optimization-mandatory) |
| 12 | When scanning/opening files, skip Windows reserved device names (CON, PRN, AUX, NUL, COMx, LPTx) | [File Operations](#file-operations-mandatory) |

---

## Project Structure

```text
toolbox/
├── main.py                     # Application entry point
├── toolbox.py                  # Main app (ToolboxWindow, ToolPlugin, Theme, UI components)
├── config.py                   # Global config (app info, UI, theme, welcome page)
├── requirements.txt            # Python dependencies
├── toolbox.spec                # PyInstaller build spec
├── generate_version_info.py    # Version info generator (pre-build)
├── verify_packaging.py        # Packaging dependency verifier
├── favicon.ico                # Application icon
│
├── common/                    # Shared components
│   ├── __init__.py
│   ├── base_worker.py         # BaseWorker — shared QThread worker base class
│   ├── file_list_panel.py     # FileListPanel — reusable file list table
│   ├── action_panel.py        # ActionPanel — button + progress bar + status label
│   ├── dialog_utils.py        # Dialog helpers (get_save_file_name, etc.)
│   ├── message_utils.py       # Themed message boxes (show_info, show_error, etc.)
│   └── utils.py              # Helpers: get_image_size, get_file_size, get_pdf_pages,
│                               get_create_time, get_modify_time, PDF_COLUMNS, IMAGE_COLUMNS,
│                               PIL_AVAILABLE, FITZ_AVAILABLE, IMG2PDF_AVAILABLE
│
├── plugins/                   # Plugin directory (auto-discovered via importlib)
│   ├── image_compressor.py    # Batch image compression (JPG/PNG/WebP)
│   ├── image_scaler.py        # Batch image scaling (resize by width/height/percentage)
│   ├── image_stitcher.py      # Image stitching (horizontal/vertical merge)
│   ├── image_to_pdf.py        # Convert multiple images to a single PDF
│   ├── image_format_converter.py  # Batch image format conversion
│   ├── pdf_merger.py         # Merge multiple PDFs into one
│   ├── pdf_splitter.py        # Split PDF into per-page PDFs or images
│   └── file_deduplicator.py  # File deduplication (size→quick hash→full hash)
│
└── test/                      # Test files
    ├── test_button.py          # Button UI component tests
    ├── test_icon.py           # Icon and theme tests
    ├── test_plugin.py         # Plugin system tests
    ├── test_scaling.py        # Image scaling functionality tests
    ├── test_scaling_complete.py
    ├── test_scaling_function.py
    ├── test_sidebar.py        # Sidebar navigation tests
    ├── test_adaptive_ui.py
    ├── test_plugins.py
    ├── test_pdf_merger.py
    ├── create_test_images.py  # Test image generator
    ├── check_plugins.py
    ├── debug_plugins.py
    ├── final_test.py
    ├── simple_check.py
    ├── simple_test.py
    └── toolbox2.py            # Backup/alternative implementation (test only)
```

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py

# Run tests
cd test/ && python -m unittest discover -v

# Pre-build steps
python generate_version_info.py
python verify_packaging.py

# Build executable (Windows, recommended)
pyinstaller toolbox.spec

# Build with UPX compression
pyinstaller --upx-dir=/path/to/upx toolbox.spec
```

---

## Architecture

`toolbox.py` is a PyQt6 desktop app (工具箱 "Toolbox") with a plugin-based architecture.

### Core Structure

- **`ToolboxWindow`** — main window; owns the sidebar (`QVBoxLayout`) and a `QStackedWidget` for tool pages
- **`Theme`** — dark/light color palette constants; applied via Qt stylesheets
- **`ToolPlugin`** (abstract base) — all tools inherit this; must implement `create_ui() -> QWidget` and `update_theme(theme)`
- **Built-in tools**: `ImageCompressor`, `ImageToPDF`, `FormatConverter`, `ImageStitcher`, `PDFMerger`, `PDFSplitter`
- **Plugins**: auto-discovered from `plugins/` via `importlib`; added dynamically to sidebar and stack
- **`SettingsPlugin`** — settings page with theme switching (dark/light) and about info
- **`WelcomePage`** — landing page showing feature cards

### Configuration System (`config.py`)

| Constant | Purpose |
|----------|---------|
| `APP_NAME`, `APP_VERSION`, `APP_DESCRIPTION`, `APP_COPYRIGHT` | Basic app info |
| `APP_WEBSITE_URL`, `APP_WEBSITE_LINK_TEXT` | Website link in settings |
| `FEATURE_MODULES` | Feature cards shown on welcome page |
| `UI_CONFIG` | Window size, sidebar width, corner radius |
| `THEME_CONFIG` | Default theme and color settings |
| `WELCOME_CONFIG` | Welcome page text content |
| `SPACING_SMALL`, `SPACING_MEDIUM` | Spacing constants for UI |
| `FONT_SIZE_*`, `FONT_WEIGHT_*` | Font constants for UI |

### Threading

Long operations run in `QThread` workers that emit progress signals — never block the main thread.
Each plugin defines its own `*Worker` class (e.g., `CompressionWorker`, `PDFMergeWorker`). Consider using `BaseWorker` from `common/base_worker.py` to reduce duplication.

### PDF Conversion

`PDFWorker` (in `image_to_pdf.py`) tries libraries in order: `img2pdf` → `PyMuPDF` → `PIL`. All three are in `requirements.txt`. Supports compression with adjustable quality (1–100%) for all three backends.

---

## Development Standards

### Syntax Check After Modification (MANDATORY)

**Rule: After modifying any Python file, you MUST run syntax checking before marking the task as complete.**

Required checks:

- **Syntax validation**: `python -m py_compile <file.py>`
- **Indentation check**: Consistent indentation (4 spaces per level, no tabs)
- **Import verification**: All used names (`Image`, `fitz`, `img2pdf`, `FONT_WEIGHT_*`, etc.) must be properly imported
- **Line ending check**: LF (`\n`) only, not CRLF (`\r\n`)

Check command:

```bash
# Syntax check a single file
python -m py_compile <file.py>

# Check all Python files in the project
find . -name "*.py" -not -path "./.git/*" -not -path "*/__pycache__/*" -exec python -m py_compile {} \;
```

Common issues to catch:

- `NameError` / `ImportError` — missing imports (e.g., `Image` from `PIL`, `fitz`, `PDF_COLUMNS`)
- `IndentationError` — mixed tabs/spaces or incorrect indent
- `SyntaxError` — malformed Python code (missing colons, unclosed brackets)
- Method definitions missing `:` (e.g., `def update_theme(self, theme)` — colon required)

### Code Reuse (MANDATORY)

**Rule: If identical or similar code appears 2+ times, you MUST abstract it into a shared class or method.**

- Before writing new code, check `common/`, `toolbox.py`, or existing plugins for similar logic
- Shared components go in `common/` or the base class (`ToolPlugin`, `Theme`)
- When refactoring, update ALL occurrences, not just new code

#### Shared Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ToolPlugin` | `toolbox.py` | Base class for all plugins |
| `Theme` | `toolbox.py` | Dark/light color palettes + ALL color constants |
| `AnimatedButton` | `toolbox.py` | Reusable button with hover effects |
| `SelectableLabel` | `toolbox.py` | Text label supporting mouse selection and copying |
| `Card` | `toolbox.py` | Card container with title/content layout |
| `DragDropHandler` | `toolbox.py` | Drag-and-drop utility |
| `SidebarButton` | `toolbox.py` | Sidebar navigation button |
| `FileListPanel` | `common/file_list_panel.py` | Reusable file list table with buttons |
| `ActionPanel` | `common/action_panel.py` | Button + progress bar + status label |
| `BaseWorker` | `common/base_worker.py` | Base QThread worker with standard signals |
| `MessageUtils` | `common/message_utils.py` | Themed message boxes and dialogs |
| `get_image_size`, `get_file_size` | `common/utils.py` | Image/file size helper functions |
| `get_pdf_pages`, `get_create_time` | `common/utils.py` | PDF/file time helper functions |
| `IMAGE_COLUMNS`, `PDF_COLUMNS` | `common/utils.py` | Common table column definitions |
| `PIL_AVAILABLE`, `FITZ_AVAILABLE`, `IMG2PDF_AVAILABLE` | `common/utils.py` | Module availability flags |

#### Patterns That MUST Use Shared Components

| Pattern | Use Instead |
|---------|---------------|
| Worker class in each plugin | `BaseWorker` from `common/base_worker.py` |
| Image size/format helpers | `get_image_size()` from `common/utils.py` |
| Button/progress bar styles | `Theme` class constants |
| `update_theme()` per plugin | Implement in `ToolPlugin` base class |
| File size formatting | `get_file_size()` from `common/utils.py` |
| Status message updates | Shared helper or `ActionPanel` |

#### When Adding a New Plugin

1. **Check `FileListPanel`** — if the plugin needs a file list, use `FileListPanel` from `common/file_list_panel.py`
2. **Use shared UI components** — import `AnimatedButton`, `Card`, `SelectableLabel` from `toolbox`
3. **Reuse helper functions** — check `common/utils.py` before writing new ones
4. **Use `ActionPanel`** — for button + progress + status, use `ActionPanel` from `common/action_panel.py`
5. **Use `SelectableLabel`** — for titles, descriptions, status messages (any text users might copy)
6. **Responsive layout** — no `addStretch()` at end; let FileListPanel expand naturally
7. **Follow existing patterns** — follow established plugin code for consistency
8. **Implement `update_theme()`** — update ALL custom-styled widgets; use `Theme` constants
9. **Test in both themes** — verify text readability in dark AND light mode
10. **Test responsive behavior** — verify layout adapts in normal, maximized, and fullscreen modes

### File Encoding and Line Endings

- **Encoding**: All Python files MUST use UTF-8 (first line: `# -*- encoding: utf-8 -*-`)
- **Line Endings**: All Python files MUST use LF (`\n`), not CRLF (`\r\n`)
- **Module docstring**: Every file MUST have a brief module docstring after the encoding line

```python
# -*- encoding: utf-8 -*-
"""
Brief description of this module
"""
```

### Exception Handling (MANDATORY)

**Rule: Only catch exceptions that are meaningful and necessary. Always provide error information.**

- **No meaningless try-catch** — don't wrap code that cannot reasonably raise
- **Catch and report** — always print or log the error when catching
- **No try-catch for project-internal imports** — `config.py`, `toolbox.py`, etc. should fail loudly
- **No duplicate import checks** — import `PIL_AVAILABLE`, `FITZ_AVAILABLE`, `IMG2PDF_AVAILABLE` from `common.utils`, never re-declare

```python
# GOOD: Catching a reasonable exception with error info
try:
    plugin_module = importlib.import_module(module_name)
except ImportError as e:
    print(f"Failed to import {module_name}: {e}")
    return None

# BAD: Meaningless try-catch
try:
    x = 1 + 2
except Exception as e:
    print(e)  # Addition never raises

# BAD: Catching but not reporting
try:
    data = json.load(file)
except json.JSONDecodeError:
    return None  # No error info — hard to debug
```

### Text Copyability (MANDATORY)

**Rule: All informational text that users might want to copy MUST use `SelectableLabel` instead of `QLabel`.**

Users should be able to select and copy:

- Version numbers, copyright info, website links
- File paths, output paths, status messages
- Error messages, scan results, statistics
- Plugin titles and descriptions
- Welcome page content

#### Using SelectableLabel

{% raw %}```python
from toolbox import SelectableLabel

# GOOD: Informational text uses SelectableLabel

self.version_label = SelectableLabel(f"版本: v{APP_VERSION}")
self.status_label = SelectableLabel("正在处理...")
self.desc_label = SelectableLabel(self.description)

# BAD: Informational text uses QLabel (not copyable)

self.version_label = QLabel(f"版本: v{APP_VERSION}")

```{% endraw %}

#### When to Use SelectableLabel

| Use SelectableLabel | Use QLabel |
|---------------------|------------|
| Version numbers, copyright | Button text |
| File paths, output paths | Form field labels ("输出格式:") |
| Status messages, error messages | Decorative icons |
| Statistics, scan results | Section titles (unless user needs to copy) |
| Plugin titles/descriptions | - |

#### SelectableLabel Features

- Supports text selection with mouse (`TextSelectableByMouse`)
- Supports clickable links (`LinksAccessibleByMouse`)
- Shows I-beam cursor on hover
- Works with all existing QLabel styling

### Responsive Layout (MANDATORY)

**Rule: UI components MUST adapt to window size changes. Avoid fixed heights; use Expanding策略 and dynamic sizing.**

#### Core Principles

1. **Tables and lists**: Use `setSizePolicy(Expanding, Expanding)` to fill available space
2. **No `addStretch()` at layout end**: Let content naturally fill space instead of pushing to bottom
3. **Dynamic heights**: Use `resizeEvent` for components that need proportional sizing
4. **Minimum heights only**: Use `setMinimumHeight()` instead of `setFixedHeight()`

#### FileListPanel (Already Responsive)

`FileListPanel` in `common/file_list_panel.py` already implements responsive layout:

```python
self.table.setMinimumHeight(self.table_min_height)  # Minimum, not fixed
self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
```

When using `FileListPanel`, the table automatically expands when the window grows.

#### Plugin Layout Pattern

```python
# GOOD: Responsive layout
layout = QVBoxLayout(widget)
layout.addWidget(self.title_label)
layout.addWidget(self.desc_label)
layout.addWidget(file_card)      # Contains FileListPanel
layout.addWidget(settings_card)
layout.addWidget(self.action_panel)
# NO addStretch() — let FileListPanel expand naturally

# BAD: Fixed layout with wasted space
layout.addWidget(self.action_panel)
layout.addStretch()  # Pushes empty space to bottom instead of expanding content
```

#### Dynamic Height Components

For components that need proportional sizing (like welcome page carousel):

```python
def resizeEvent(self, event):
    """Adjust component height based on window size"""
    super().resizeEvent(event)
    if self.scroll_area:
        available_height = self.height()
        # Calculate target height: min 250px, max 500px, default 35% of window
        target_height = max(250, min(500, int(available_height * 0.35)))
        self.scroll_area.setMaximumHeight(target_height)
```

#### Responsive Layout Checklist

When adding new UI components:

- [ ] Tables/lists use `setSizePolicy(Expanding, Expanding)`
- [ ] Use `setMinimumHeight()` instead of `setFixedHeight()` where possible
- [ ] No `layout.addStretch()` at the end of plugin layouts
- [ ] Components that need proportional sizing implement `resizeEvent()`
- [ ] Test in normal, maximized, and fullscreen modes
- [ ] Verify no excessive whitespace at bottom when window is large

---

## File Operations

### File Operations (MANDATORY)

Two critical rules for file handling:

#### Rule 9: Pre-check Output Files

**When writing/overwriting output files, check if the file is locked/occupied before processing.**

This prevents wasting user time by catching the error early, rather than after all processing is complete.

```python
# GOOD: Pre-check if output file is locked (image_to_pdf.py pattern)
try:
    with open(self.output, 'ab') as f:
        pass  # Test if file can be opened for writing
except PermissionError as e:
    # Windows file lock (WinError 32) - file opened in WPS, Adobe Reader, etc.
    self.finished.emit(
        False,
        f"目标文件被占用，无法写入：\n{self.output}\n\n"
        f"请先关闭该文件（如在 WPS、Adobe Reader 等软件中打开），然后重试。"
    )
    return
except Exception as e:
    self.finished.emit(False, f"无法访问目标文件：{str(e)}")
    return
```

**Why this matters:**

- Processing many files takes time — don't discover the file is locked AFTER processing
- User sees "conversion failed" after waiting, then must restart everything
- Clear error message helps user understand what to do (close the file)

**Check other plugins:**

- ✅ `image_to_pdf.py` — has this check (since commit 79b9b69)
- ✅ Other plugins — `file_deduplicator.py` only reads files (no output file check needed)
- ✅ `pdf_merger.py`, `pdf_splitter.py`, etc. — use `QFileDialog` which handles file access natively

#### Rule 10: Check File Existence Before Deletion

**When deleting temporary files, check if the file exists first to avoid error spam.**

This is especially important when files may have been moved, already deleted, or when using relative paths that resolve differently.

```python
# GOOD: Check existence before deleting
import os
for tf in temp_files:
    try:
        tf_full = os.path.abspath(tf)  # Always use absolute path
        if os.path.exists(tf_full):
            os.remove(tf_full)
    except OSError as e:
        print(f"Error removing temp file {tf}: {e}")

# BAD: Direct deletion without checks
for tf in temp_files:
    os.remove(tf)  # May raise FileNotFoundError or WinError 2
```

**Why this matters:**

- After `shutil.move()` or other operations, the temp file may no longer exist at the expected path
- Relative paths can resolve incorrectly when working directory changes
- Batch operations may create duplicate filenames, causing some to be already deleted

**Best practices:**

1. **Use `os.path.abspath()`** — convert all paths to absolute before operations
2. **Use `os.path.exists()`** — check before delete to avoid errors
3. **Use `set()` instead of `list`** — for temp_files storage to avoid duplicates
4. **Use `set.discard()`** — instead of `list.remove()` to avoid ValueError on missing items

**Check other plugins:**

- ✅ `image_to_pdf.py` — fixed in commit 58ec96e (uses `abspath`, `exists`, `set`)
- ✅ `file_deduplicator.py` — uses `os.path.exists()` before delete, skips reserved device names

#### Rule 12: Skip Windows Reserved Device Names

**When scanning or opening files by path, skip files whose basename (without extension) is a Windows reserved device name.**

On Windows, names like `CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9` are device names. Opening `con.log` causes `open()` to block indefinitely (interpreted as console device input). This applies regardless of file extension or directory depth.

```python
# GOOD: Skip reserved device names before opening
WINDOWS_RESERVED_NAMES = frozenset({
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
})

name_without_ext = os.path.splitext(filename)[0].upper()
if name_without_ext in WINDOWS_RESERVED_NAMES:
    continue  # Skip this file

# BAD: Opening without checking
with open(file_path, 'rb') as f:  # Blocks forever if file is named con.log
    data = f.read()
```

---

## Performance Optimization

### Performance Optimization (MANDATORY)

**Rule: Plugins processing images or files MUST manage memory properly to avoid leaks and excessive memory usage.**

Based on commit `f28dfae` - fixes for memory leaks and file handle issues.

#### Core Principles

1. **Use context managers** — Always use `with Image.open(f) as img:` to ensure file handles are released
2. **Explicit close** — Call `img.close()` after processing to free memory immediately
3. **Avoid loading all data at once** — For batch processing, process files one-by-one or in batches
4. **Use BATCH_SIZE** — For large batch operations, control memory with `BATCH_SIZE = N`
5. **Release intermediate objects** — When creating new images (resized, converted), close the old one

#### Context Manager Pattern

```python
# GOOD: Context manager ensures file handle release
with Image.open(file_path) as src_img:
    img = src_img.copy()  # Work on a copy
# src_img is automatically closed here

# BAD: File handle leak
img = Image.open(file_path)  # Never closed, handle leaks
```

#### Process Files One-by-One (Not All at Once)

```python
# GOOD: Process one-by-one (image_stitcher.py pattern)
for f in self.files:
    with Image.open(f) as img:
        # Process this image
        img.save(output_path)
    # File closed, memory freed

# BAD: Load ALL images into memory
images = []
for f in self.files:
    img = Image.open(f)
    images.append(img)  # Memory grows unbounded!
```

#### Release Memory After Processing

```python
# GOOD: Close after save
img.save(output_path, "JPEG", quality=85)
img.close()  # Free memory immediately

# GOOD: Close old image when creating new one
new_img = img.resize((w, h), Image.Resampling.LANCZOS)
img.close()  # Release original
img = new_img

# BAD: Never closing
scaled_img = img.resize((w, h))
scaled_img.save(output_file)
# Memory not freed until garbage collection
```

#### Batch Processing Pattern

```python
# GOOD: Batch with BATCH_SIZE (image_to_pdf.py pattern)
BATCH_SIZE = 50

for batch_start in range(0, total, self.BATCH_SIZE):
    batch_files = files[batch_start:batch_start + self.BATCH_SIZE]
    batch_imgs = []
    for f in batch_files:
        with Image.open(f) as img:
            batch_imgs.append(img.copy())
    # Process this batch...
    batch_imgs.clear()  # Release batch memory
```

#### Check Plugins for Performance Issues

| Plugin | Status | Issue |
|--------|--------|-------|
| `image_stitcher.py` | ✅ Fixed (f28dfae) | Was loading ALL images into memory |
| `image_compressor.py` | ✅ Fixed (f28dfae) | Now uses context manager + explicit close |
| `image_scaler.py` | ✅ Fixed (f28dfae) | Now closes `scaled_img` after save |
| `image_format_converter.py` | ✅ Fixed (f28dfae) | Now uses context manager + close |
| `image_to_pdf.py` | ✅ Fixed (f28dfae) | Now uses context manager in scan + batch processing |
| `pdf_merger.py` | ✅ OK | Uses `doc.close()` correctly |
| `pdf_splitter.py` | ✅ OK | Uses `doc.close()` correctly |

## Theme System

- Two themes: `Theme.DARK` (default) and `Theme.LIGHT`
- Theme switching via `SettingsPlugin` with persistent storage using `QSettings`
- All plugins MUST implement `update_theme(theme)` to respond to theme changes
- Global stylesheet applied to main window with theme-specific colors

### Color Constants (Defined in `Theme` class)

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

### Theme Compliance Rules (MANDATORY)

1. **NEVER hardcode colors** — Always use `Theme.COLOR_NAME` or `theme["key"]`
2. **Text must contrast with background** — Use `TEXT_PRIMARY`/`TEXT_SECONDARY` for all text
3. **Test in BOTH themes** — Every style change must be verified in dark AND light mode
4. **Message boxes** — Use `MessageUtils.show_info()`, etc. from `common/message_utils.py` instead of raw `QMessageBox`
5. **Gradient buttons** — Text color must be explicitly set for all states:
   {% raw %}```python

   # GOOD

   button.setStyleSheet(f"""
       QPushButton {{ color: {Theme.TEXT_PRIMARY}; }}
       QPushButton:hover {{ color: {Theme.TEXT_PRIMARY}; }}
   """)

   # BAD — depends on inheritance

   button.setStyleSheet("background: qlineargradient(...);")

   ```{% endraw %}
6. **Status labels** — Use appropriate color constants: Success=`Theme.SUCCESS`, Error=`Theme.ERROR`, Warning=`Theme.WARNING`, Info=`Theme.ACCENT_PRIMARY`

---

## Adding a Plugin

Inherit `ToolPlugin`, implement `create_ui()` and `update_theme()`, then drop the file in `plugins/`.

```python
from toolbox import ToolPlugin, Card, AnimatedButton, SelectableLabel, Theme
from PyQt6.QtWidgets import QWidget, QVBoxLayout

class MyTool(ToolPlugin):
    name = "我的工具"
    description = "工具描述"
    icon = "🔧"

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Use SelectableLabel for informational text
        self.title_label = SelectableLabel(f"{self.icon} {self.name}")
        layout.addWidget(self.title_label)
        
        self.desc_label = SelectableLabel(self.description)
        layout.addWidget(self.desc_label)
        
        # Add your content here
        # ...
        
        # NO layout.addStretch() at the end for responsive layout
        return widget

    def update_theme(self, theme):
        """Update UI when theme changes — MUST update all custom-styled widgets."""
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"color: {theme['text']};")
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"color: {theme['text_secondary']};")
```

### Plugin Checklist

- [ ] Inherits `ToolPlugin` and implements `create_ui()` + `update_theme()`
- [ ] Uses `FileListPanel` if file list needed
- [ ] Uses `ActionPanel` for action button + progress + status
- [ ] Uses `SelectableLabel` for informational text (titles, descriptions, status)
- [ ] Responsive layout: no `addStretch()` at end, tables use Expanding策略
- [ ] Imports shared helpers from `common/utils.py` (not re-declared)
- [ ] Imports `Image`/`fitz`/`img2pdf` conditionally based on availability flags
- [ ] All used names are imported (run pyflakes to verify)
- [ ] Tested in both dark and light themes
- [ ] Tested in normal, maximized, and fullscreen window modes
- [ ] Added to `hiddenimports` in `toolbox.spec`
- [ ] Syntax-checked with `python -m py_compile`
- [ ] When writing/overwriting output files, check if the file is locked (Rule #9)
- [ ] When deleting files, check if the file exists first (Rule #10)

---

## Testing

All test files are in `test/` with a `test_` prefix.

- `test_button.py` — Button UI component tests
- `test_icon.py` — Icon and theme tests
- `test_plugin.py` — Plugin system tests
- `test_scaling.py` — Image scaling functionality tests
- `test_sidebar.py` — Sidebar navigation tests

When adding features, create corresponding test files in `test/`.

---

## Packaging

### Dynamic Import Issue

PyInstaller cannot auto-detect modules loaded via `importlib`. All plugins in `plugins/` must be explicitly listed in `toolbox.spec`'s `hiddenimports`.

**When adding a new plugin:**

1. Create the plugin file in `plugins/` (e.g., `plugins/my_plugin.py`)
2. Add `'plugins.my_plugin'` to `hiddenimports` in `toolbox.spec`
3. Run `python verify_packaging.py` to verify
4. Rebuild with `pyinstaller toolbox.spec`

See `PACKAGING_GUIDE.md` for detailed troubleshooting.

### Key Dependencies

| Package | Role |
|---------|------|
| PyQt6 | GUI framework |
| Pillow (PIL) | Image processing |
| img2pdf | Primary PDF conversion |
| PyMuPDF (fitz) | Fallback PDF conversion |
| PyInstaller | Build executables |
