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
| 7 | 所有文本展示内容优先使用 `SelectableLabel`（交互控件除外）| [Text Copyability](#text-copyability-mandatory) |
| 8 | UI components MUST support responsive layout (Expanding策略, 动态高度) | [Responsive Layout](#responsive-layout-mandatory) |
| 9 | When writing/overwriting output files, check if the file is locked/occupied before processing | [File Operations](#file-operations-mandatory) |
| 10 | When deleting temporary files, check if the file exists first to avoid error spam | [File Operations](#file-operations-mandatory) |
| 11 | When processing files/images, use context managers and release resources properly | [Performance Optimization](#performance-optimization-mandatory) |
| 12 | When scanning/opening files, skip Windows reserved device names (CON, PRN, AUX, NUL, COMx, LPTx) | [File Operations](#file-operations-mandatory) |
| 13 | 只改动到代码才运行测试；纯文档改动（.md 等）不需要跑测试 | [Testing](#testing) |

---

## Project Structure

```text
toolbox/
├── main.py                     # Application entry point
├── toolbox.py                  # Main app (ToolboxWindow, ToolPlugin, Theme, UI components)
├── config.py                   # Global config (app info, UI, theme, welcome page)
├── menu_system.py              # Menu system (legacy demo, not imported by the app)
├── settings_page.py            # Legacy settings module (unused; real SettingsPlugin lives in toolbox.py)
├── requirements.txt            # Python dependencies
├── cliff.toml                  # git-cliff changelog 生成配置
├── toolbox.spec                # PyInstaller build spec
├── pytest.ini                  # pytest configuration
├── generate_version_info.py    # Version info generator (pre-build)
├── verify_packaging.py        # Packaging dependency verifier
├── build.py                   # Windows build script
├── build_macos.py             # macOS build script
├── favicon.ico                # Application icon
├── CHANGELOG.md               # Version changelog
├── .markdownlint.json         # Markdown lint configuration
│
├── common/                    # Shared components
│   ├── __init__.py
│   ├── base_worker.py         # BaseWorker — shared QThread worker base class
│   ├── file_list_panel.py     # FileListPanel — reusable file list table
│   ├── action_panel.py        # ActionPanel — button + progress bar + status label
│   ├── dialog_utils.py        # Dialog helpers (get_save_file_name, etc.)
│   ├── directory_drop_line_edit.py  # DirectoryDropLineEdit — folder drag-drop input
│   ├── message_utils.py       # Themed message boxes (show_info, show_error, etc.)
│   ├── app_settings.py        # AppSettings — config.ini read/write with atomic save
│   ├── nav_config.py          # Sidebar order/visibility config ([setting.nav] in config.ini)
│   ├── i18n.py                # t() translation lookup, bind_combo, retranslate helpers
│   └── utils.py              # Helpers: get_image_size, get_file_size, get_pdf_pages,
│                               get_create_time, get_modify_time, PDF_COLUMNS, IMAGE_COLUMNS,
│                               PIL_AVAILABLE, FITZ_AVAILABLE, IMG2PDF_AVAILABLE
│
├── plugins/                   # Plugin directory (auto-discovered via importlib)
│   ├── image_compressor.py        # Batch image compression (JPG/PNG/WebP)
│   ├── image_scaler.py            # Batch image scaling (resize by width/height/percentage)
│   ├── image_stitcher.py          # Image stitching (horizontal/vertical merge)
│   ├── image_to_pdf.py            # Convert multiple images to a single PDF
│   ├── image_format_converter.py  # Batch image format conversion
│   ├── pdf_merger.py             # Merge multiple PDFs into one
│   ├── pdf_splitter.py            # Split PDF into per-page PDFs or images
│   ├── file_deduplicator.py      # File deduplication (size→quick hash→full hash)
│   └── empty_folder_cleaner.py   # Recursive empty folder finder & deleter
│
├── i18n/                       # Translation dictionaries (zh_CN.json, en.json)
│
├── scripts/                   # Build and release scripts
│   ├── build_dmg.py           # macOS .dmg packaging
│   ├── check_i18n.py          # i18n dictionary validator (key coverage, dangling refs)
│   ├── generate_notes.py      # Release notes generator
│   └── get_version.py         # Version info extractor
│
└── test/                      # Test files (test_ prefix)
    ├── conftest.py            # Shared pytest fixtures
    ├── test_p3_*.py           # Per-plugin functional tests (image/pdf/dedup/empty-folder)
    ├── test_app_settings.py   # AppSettings INI read/write tests
    ├── test_i18n*.py          # i18n dictionary tests
    ├── test_nav_config.py    # Sidebar order/visibility config tests
    ├── test_base_worker.py   # BaseWorker tests
    ├── test_utils.py          # common/utils helper tests
    ├── test_button.py        # Button UI component tests
    ├── test_icon.py           # Icon and theme tests
    ├── test_plugin*.py        # Plugin system tests
    ├── test_sidebar.py        # Sidebar navigation tests
    ├── create_test_images.py  # Test image generator
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

# Clean build artifacts (only build/, NOT dist/)
rm -rf build/

# ⚠️ 不要删除 dist/ 目录 — 用户可能在其中存放自定义构建产物
```

### Changelog 生成（需安装 git-cliff，通过 `git cliff` 使用）

```bash
# 预览两个版本间的变更
git cliff v2.0.5..HEAD --unreleased

# 生成草稿并追加到 CHANGELOG.md
git cliff --unreleased --tag v2.0.6 --prepend CHANGELOG.md
```

## 发布流程

```bash
# 1. 更新版本号（编辑 config.py 中的 APP_VERSION）

# 2. 生成 changelog 草稿（自动分组 Added / Fixed / Dependencies / …）
git cliff --unreleased --tag v2.0.6 --prepend CHANGELOG.md

# 3. 人工润色 CHANGELOG.md（补充上下文细节、统一措辞）

# 4. 提交并打 tag
git add config.py CHANGELOG.md
git commit -m "chore: release v2.0.6"
git tag v2.0.6

# 5. 推送到远程
git push origin main --tags
```

---

## Architecture

`toolbox.py` is a PyQt6 desktop app (工具箱 "Toolbox") with a plugin-based architecture.

### Core Structure

- **`ToolboxWindow`** — main window; owns the sidebar (supports collapse/expand with animated width transition and child fade-in/out), a toggle button (chevron icon drawn via QPainter, `Ctrl+B` shortcut), and a `QStackedWidget` for tool pages
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
| `APP_UPDATE_URL`, `APP_ISSUE_URL` | Update check and issue report URLs |
| `PLUGIN_MODULES` | Plugin list with name, icon, description, order, module, class |
| `UI_CONFIG` | Window size, sidebar width, corner radius |
| `SPACING_SMALL`, `SPACING_MEDIUM` | Spacing constants for UI |
| `FONT_SIZE_*` (`12`–`24`) | Font size constants |
| `FONT_WEIGHT_*` (`600`–`800`) | Font weight constants |
| `TITLE_STYLES` | Title font size and weight |

### Threading

Long operations run in `QThread` workers that emit progress signals — never block the main thread.
Each plugin defines its own `*Worker` class (e.g., `CompressionWorker`, `PDFMergeWorker`). Consider using `BaseWorker` from `common/base_worker.py` to reduce duplication.

### PDF Conversion

`PDFWorker` (in `image_to_pdf.py`) tries libraries in order: `PyMuPDF` → `img2pdf` → `PIL`. All three are in `requirements.txt`. Supports compression with adjustable quality (1–100%) for all three backends.

---

## Development Standards

### Documentation Naming

问题分析、故障记录和修复建议文档统一放在 `docs/` 目录下，文件名使用 `YYYY-MM-DD-简短问题描述.md` 格式，例如 `2026-10-17-图片转PDF方向异常问题.md`。

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

# Syntax check all Python files in the project
find . -name "*.py" -not -path "./.git/*" -not -path "*/__pycache__/*" -exec python -m py_compile {} \;

# Static analysis — catches NameError / undefined names missed by py_compile
python -m pyflakes <file.py>
```

Common issues to catch:

- `NameError` / `ImportError` — missing imports (e.g., `Image` from `PIL`, `fitz`, `PDF_COLUMNS`, `pyqtSignal`)
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
| `load_setting`/`save_setting`/`set_combo_by_data` | `ToolPlugin` (`toolbox.py`) | 公共配置读写方法，插件设置项统一持久化到 `[plugin.<id>]` |
| `Theme` | `toolbox.py` | Dark/light color palettes + ALL color constants |
| `AnimatedButton` | `toolbox.py` | Reusable button with hover effects |
| `SelectableLabel` | `toolbox.py` | Text label supporting mouse selection and copying |
| `Card` | `toolbox.py` | Card container with title/content layout |
| `DragDropHandler` | `toolbox.py` | Drag-and-drop utility |
| `SidebarButton` | `toolbox.py` | Sidebar navigation button |
| `SidebarToggleIcon` | `toolbox.py` | Chevron icon rendered via `QPainter` for sidebar collapse button |
| `FileListPanel` | `common/file_list_panel.py` | Reusable file list table with buttons |
| `ActionPanel` | `common/action_panel.py` | Button + progress bar + status label |
| `BaseWorker` | `common/base_worker.py` | Base QThread worker with standard signals |
| `MessageUtils` | `common/message_utils.py` | Themed message boxes and dialogs |
| `AppSettings` | `common/app_settings.py` | config.ini read/write with backup + atomic save |
| `i18n` (`t()`, `bind_combo`) | `common/i18n.py` | Translation lookup and combo auto-retranslate |
| `DirectoryDropLineEdit` | `common/directory_drop_line_edit.py` | Folder input with drag-drop support |
| `get_image_size`, `get_file_size` | `common/utils.py` | Image/file size helper functions |
| `get_pdf_pages`, `get_create_time` | `common/utils.py` | PDF/file time helper functions |
| `IMAGE_COLUMNS`, `PDF_COLUMNS` | `common/utils.py` | Common table column definitions |
| `WINDOWS_RESERVED_NAMES` | `common/utils.py` | Windows reserved device names (CON, PRN, ...) |
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

**Rule: All文本展示内容，只要不是交互式控件（按钮、复选框等），尽量使用 `SelectableLabel` 替代 `QLabel`，确保用户可以选中复制。**

#### 必须使用 SelectableLabel 的场景

| 场景 | 示例 |
|------|------|
| 版本号、版权信息、官网链接 | `f"版本: v{APP_VERSION}"` |
| 文件路径、输出路径、状态消息 | `SelectableLabel("拖拽文件到此处...")` |
| 错误消息、扫描结果、统计数据 | `SelectableLabel("成功处理 5 张图片")` |
| 插件标题和描述 | `SelectableLabel(f"{self.icon} {self.name}")` |
| 卡片标题 | `Card(title="选择图片")` — Card 内部已用 SelectableLabel |
| 表单/设置字段标签 | `SelectableLabel("输出格式:")` 替代 `QLabel("输出格式:")` |
| 设置页面各项文字 | 外观、版本号、功能描述、版权等 |
| 水印/占位提示文字 | FileListPanel 水印文字（设置 `setTextInteractionFlags`） |
| QFormLayout 行标签 | 用显式 `SelectableLabel` 替代直接传字符串 |
| 百分比/数值标签 | `self.quality_label = SelectableLabel("75%")` |

#### 不需要改为 SelectableLabel 的场景

| 场景 | 原因 |
|------|------|
| 导航按钮（QPushButton） | 选中文本会干扰点击导航，保持不可复制 |
| AnimatedButton 等按钮文字 | 按钮是交互控件，不适用 |
| 复选框/单选按钮文字 | 交互式控件，不可复制是正常行为 |

#### 使用方式

**方式一：直接使用 SelectableLabel（推荐）**
{% raw %}```python
from toolbox import SelectableLabel

self.version_label = SelectableLabel(f"版本: v{APP_VERSION}")
self.format_label = SelectableLabel("输出格式:")
```{% endraw %}

**方式二：QFormLayout 行标签（不要直接传字符串）**
{% raw %}```python
# BAD — QFormLayout 内部生成不可选的 QLabel
settings_layout.addRow("输出格式:", format_layout)

# GOOD — 使用显式 SelectableLabel
self.format_label = SelectableLabel("输出格式:")
settings_layout.addRow(self.format_label, format_layout)
```{% endraw %}

**方式三：FileListPanel 等通用组件（无法导入 SelectableLabel 时）**
{% raw %}```python
self.watermark_label = QLabel("拖拽文件到此处...")
self.watermark_label.setTextInteractionFlags(
    Qt.TextInteractionFlag.TextSelectableByMouse
    | Qt.TextInteractionFlag.LinksAccessibleByMouse
)
self.watermark_label.setCursor(Qt.CursorShape.IBeamCursor)
```{% endraw %}

#### SelectableLabel 特性

- 支持鼠标选中文本（`TextSelectableByMouse`）
- 支持点击链接（`LinksAccessibleByMouse`）
- 悬停时显示 I-Beam 光标
- 兼容所有 QLabel 样式设置

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

## Configuration Persistence (config.ini)

所有用户配置统一存放在单个 `config.ini`（由 `common/app_settings.py` 的 `AppSettings` 管理），分两个命名空间：

### INI 节结构

| 节 | 键 | 内容 |
|----|-----|------|
| `[setting]` | `language`, `theme` | 界面语言、主题 |
| `[setting.window]` | `geometry`, `state` | 窗口几何/状态（base64） |
| `[setting.nav]` | `order`, `hidden` | 侧边栏顺序与隐藏项 |
| `[setting.meta]` | `config_version` | 配置文件版本（当前 2） |
| `[plugin.<id>]` | 各插件自定义 | 插件设置项（如 `quality`、`format`、`output_dir`） |

规则：**全局项一律放 `setting.*` 命名空间，插件项一律放 `plugin.<id>`**——节名即前缀，天然区分归属。

### 读写时机（重要）

| 配置项 | 读取时机 | 写入时机 |
|--------|----------|----------|
| `[setting]` language | `main.py` 启动时（`QApplication` 创建后、窗口构造前） | 语言下拉变化时（`_persist_language` 立即 `save()`） |
| `[setting]` theme | `ToolboxWindow.__init__`（初始主题） | 主题按钮点击时（`save_theme_setting` 立即 `save()`） |
| `[setting.window]` geometry/state | 窗口构造时 `load_geometry()` | `closeEvent` → `save_geometry()` |
| `[setting.nav]` order/hidden | `rebuild_navigation()`（注册后与每次导航变动） | 导航管理操作时（`save_nav_state` 立即 `save()`） |
| `[plugin.<id>]` 全部 | `register_plugin` → `plugin.load_settings()`（页面构建后立即应用） | `closeEvent` → `save_plugins_settings()`（仅 `set` 进内存，随 `save_geometry` 的 `save()` 一次性落盘） |

要点：

- 插件设置**不在改控件时写盘**，只在窗口正常关闭时统一落盘——`save_setting()` 只写内存，必须由 `ToolboxWindow.closeEvent` 链路调用 `app_settings.save()` 才持久化。崩溃/强杀会丢失上次关闭后的插件设置改动（与窗口几何同风险等级，属有意设计）。
- 设置页「恢复默认设置」→ `AppSettings.reset()` 重建空配置（清掉 `setting.*` 与全部 `plugin.*`），随后遍历各插件 `load_settings()` 让控件回到硬编码默认。
- 旧版本兼容：启动 `load()` 时 `_migrate_legacy_sections()` 自动把 v1 平铺节（`[general]`/`[window]`/`[nav]`/`[meta]`）迁入 `setting.*`，目标已存在时不覆盖，迁移后旧节移除、`config_version` 升级。

### 公共读写方法（新增配置项必须使用）

插件级配置一律走 `ToolPlugin` 基类方法（`toolbox.py`），不要直接操作 parser：

| 方法 | 用途 |
|------|------|
| `load_setting(key, default, type)` | 读本插件 `[plugin.<id>]` 键；缺键/空值/类型失败回退 default（`type` 支持 `int`/`str`/`bool`） |
| `save_setting(key, value)` | 写本插件键（仅内存，不落盘） |
| `set_combo_by_data(combo, value)` | 按 data 匹配下拉框选项（int/str data 均可） |
| `load_settings()` / `save_settings()` | 钩子：子类覆写，完成控件 ↔ 键的映射（框架在注册后/关闭时调用） |

`AppSettings` 级公共方法：`get`/`set`/`save`/`load`/`reset`/`remove_section`/`is_explicit`。

### 新增配置项操作清单

新增**插件设置项**时：

1. 在该插件的 `load_settings()`/`save_settings()` 中加一行 `load_setting`/`save_setting` 映射（键名用 snake_case）。
2. `create_ui()` 中的控件默认值保持硬编码——它就是缺键时的回退默认，不要重复定义默认值常量。
3. 在 `test/test_plugin_settings.py` 或对应插件测试中补往返断言。
4. 更新 `docs/2026-10-19-插件设置项持久化方案.md` 第 7 节清单与 README 的保存内容说明（如影响用户可见行为）。

新增**全局配置项**时：

1. 确定归属：全局项放 `setting.*`（如需新子节，如 `[setting.editor]`，同时加入 `_DEFAULTS`）。
2. 读取方在启动/使用处用 `settings.get(section, key, default)`；写入方确定时机（即时 `save()` vs 关闭时统一 `save()`），参考上表同类项。
3. 若该项需纳入「恢复默认」范围，确认 `reset()` 语义已覆盖（`_DEFAULTS` 有默认值即自动覆盖）。
4. 跨版本兼容时提升 `CONFIG_VERSION` 并在 `_migrate_legacy_sections()` 补迁移。

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
- ✅ `empty_folder_cleaner.py` — deletes via `os.rmdir` only; output-path lock check N/A
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
| `file_deduplicator.py` | ✅ OK | Streams files; no large image buffers held |
| `empty_folder_cleaner.py` | ✅ OK | Directory traversal only; no file/image buffers |

## Theme System

- Two themes: `Theme.DARK` (default) and `Theme.LIGHT`
- Theme switching via `SettingsPlugin` with persistent storage in `config.ini` (`[setting]` theme)
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

All test files are in `test/` with a `test_` prefix (pytest via `pytest.ini`, or `python -m unittest discover`).

- `test_p3_*.py` — per-plugin functional tests (compressor, converter, stitcher, image_to_pdf, scaler, pdf_merger, pdf_splitter, file_deduplicator, empty_folder_cleaner)
- `test_app_settings.py` — config.ini read/write/migration tests
- `test_i18n*.py`, `test_check_i18n.py` — translation dictionary tests
- `test_nav_config.py` — sidebar order/visibility config tests
- `test_base_worker.py`, `test_utils.py` — shared component tests
- `test_button.py`, `test_icon.py`, `test_sidebar.py` — UI component tests
- `test_plugin*.py` — plugin system tests

Note: some legacy script-style test files launch a GUI event loop on import and hang a full pytest collection run — run a targeted subset when testing (see memory notes).

When adding features, create corresponding test files in `test/`.

**测试纪律：** 只有改动了对应的代码文件才运行测试；纯文档改动（`.md`、`docs/`、`CHANGELOG.md` 等）不需要运行测试。改某个插件时只需跑该插件相关的测试，不必跑全量套件。

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

### macOS Packaging

macOS 打包通过 `build_macos.py` 和 `scripts/build_dmg.py` 实现，支持 `.dmg` 和 `.tar.gz` 格式。

**流程：** `build_macos.py` → PyInstaller `.app` → `scripts/build_dmg.py` → `.dmg`

CI 自动构建通过 `release.yml` 触发（Windows + macOS Matrix 策略）。

### Key Dependencies

| Package | Role |
|---------|------|
| PyQt6 | GUI framework |
| Pillow (PIL) | Image processing |
| img2pdf | Primary PDF conversion |
| PyMuPDF (fitz) | Fallback PDF conversion |
| PyInstaller | Build executables |
