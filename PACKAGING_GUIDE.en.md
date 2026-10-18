# Packaging Problem Analysis and Solution

English | [简体中文](PACKAGING_GUIDE.md)

## Problem Description

The packaged app is missing these feature modules:

1. **Batch Image Scaling** (`plugins/image_scaler.py`)
2. **Settings** (`SettingsPlugin` in `toolbox.py`)

## Root Cause

### Dynamic Import Issue

When analyzing code dependencies, PyInstaller only detects **static imports** (such as `import xxx` or `from xxx import yyy`) and cannot automatically detect **dynamically imported** modules.

The `load_plugins()` method in `toolbox.py` dynamically loads the plugin modules configured in `config.PLUGIN_MODULES` via `importlib`:

```python
def load_plugins(self):
    """Load plugins from the PLUGIN_MODULES config, register after sorting by order."""
    plugin_classes = []
    for plugin_config in PLUGIN_MODULES:
        try:
            module = importlib.import_module(plugin_config["module"])
            plugin_class = getattr(module, plugin_config["class"])
            plugin_class.id = plugin_config["id"]
            plugin_class.name = plugin_config["name"]
            plugin_class.icon = plugin_config["icon"]
            plugin_class.order = plugin_config["order"]
            ...
            plugin_classes.append(plugin_class)
        except Exception as e:
            print(f"Failed to load plugin {plugin_config.get('name', 'unknown')}: {e}")
```

This dynamic loading prevents PyInstaller from automatically discovering the modules under `plugins/`, so every plugin must be declared explicitly in `hiddenimports`.

### Solution

**Explicitly list** all dynamically loaded modules in the `hiddenimports` list of `toolbox.spec`:

```python
hiddenimports=[
    # Project modules
    'toolbox',
    'config',
    'menu_system',
    'settings_page',

    # ⭐ Plugin modules (dynamically loaded plugins must be listed explicitly)
    'plugins.image_compressor',
    'plugins.image_format_converter',
    'plugins.image_stitcher',
    'plugins.image_to_pdf',
    'plugins.image_scaler',
    'plugins.pdf_merger',
    'plugins.pdf_splitter',
    'plugins.file_deduplicator',
    'plugins.empty_folder_cleaner',

    # PIL/Pillow core modules
    'PIL',
    'PIL.Image',
    'PIL.ImageFilter',
    'PIL.ImageEnhance',
    'PIL.ImageDraw',
    'PIL.ImageFont',

    # PyQt6 core modules
    'PyQt6.sip',

    # PDF conversion libraries
    'img2pdf',
    'pymupdf',  # PyMuPDF
],
```

## Build Steps

### 1. Generate the Version Info File (Optional)

```bash
python generate_version_info.py
```

This generates `version_info.txt` from `config.py`, containing the app version, description, copyright, and other metadata.

### 2. Verify Dependencies (Pre-Build)

```bash
python verify_packaging.py
```

Make sure every required module imports correctly.

### 3. Clean Old Build Artifacts

> ⚠️ Only clean `build/`; do not delete `dist/` — users may keep historical build artifacts there.

```bash
# Windows
rmdir /s /q build

# Linux/macOS
rm -rf build
```

### 4. Build with the Spec File

```bash
pyinstaller toolbox.spec
```

### 5. Test the Packaged App

```bash
# Windows
dist\工具箱.exe

# Linux/macOS
./dist/工具箱
```

Check that the following work:

- ✓ The app starts normally
- ✓ Right-click → Properties shows the correct version info
- ✓ The sidebar shows all tools (Image Compressor, Image Format Converter, Image Stitcher, Image to PDF, Image Scaler, PDF Merger, PDF Splitter, File Deduplicator, Empty Folder Cleaner)
- ✓ The sidebar shows "Settings"
- ✓ Every tool opens normally
- ✓ "Settings" opens and can switch themes, switch language, and manage the navigation bar

## Version Info Configuration

### Auto-Generated Version Info

`toolbox.spec` is configured to read app info from `config.py`:

```python
# Import app info from config.py
from config import APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_COPYRIGHT

# Used in the EXE configuration
exe = EXE(
    # ...
    name=APP_NAME,           # the configured app name
    version='version_info.txt',  # version info file
    # ...
)
```

### Modifying App Info

Just edit the variables in `config.py`:

```python
APP_NAME = "工具箱"
APP_VERSION = "2.0.6"
APP_DESCRIPTION = "批量处理工具，支持图片压缩、PDF转换、格式转换、拼接和PDF合并"
APP_COPYRIGHT = "© 2026 yansheng836"
```

Then run `python generate_version_info.py` to regenerate the version info file.

### Windows File Properties

Right-click the packaged `.exe` → Properties → Details shows:

- File description: 批量处理工具，支持图片压缩、PDF转换、格式转换、拼接和PDF合并
- Product name: 工具箱
- Product version: 2.0.6.0
- Copyright: © 2026 yansheng836
- Company: yansheng836

## FAQ

### Q1: Why specify `hiddenimports` when `datas` already includes `('plugins', 'plugins')`?

**A:**

- `datas` merely copies files into the package as **data files**
- `hiddenimports` tells PyInstaller to bundle modules as **importable Python modules**
- Dynamically loaded modules must be specified in both places

### Q2: How do I add a new plugin?

**A:**

1. Create the plugin file in `plugins/` (e.g. `my_plugin.py`)
2. Add `'plugins.my_plugin'` to `hiddenimports` in `toolbox.spec`
3. Rebuild

### Q3: Why might the Settings plugin go missing?

**A:**
`SettingsPlugin` is defined in `toolbox.py`, so in theory it is included automatically. If it is still missing:

1. Make sure `toolbox.py` is in `hiddenimports`
2. Check that `toolbox.py` is copied correctly in `datas`

## Verification Checklist

After packaging, verify the following:

- [ ] The app starts normally
- [ ] The sidebar shows all tools (Image Compressor, Image Format Converter, Image Stitcher, Image to PDF, Image Scaler, PDF Merger, PDF Splitter, File Deduplicator, Empty Folder Cleaner) and Settings
- [ ] Image compression works
- [ ] Image to PDF works
- [ ] Image format conversion works
- [ ] Image stitching works
- [ ] Image scaling works
- [ ] PDF merging works
- [ ] PDF splitting works
- [ ] File deduplication works
- [ ] Empty folder cleanup works
- [ ] The settings page opens
- [ ] Theme switching works
- [ ] Language switching works
- [ ] Navigation management works

## References

- [PyInstaller Docs - Hidden Imports](https://pyinstaller.org/en/stable/when-things-go-wrong.html#listing-hidden-imports)
- [PyInstaller Docs - Runtime Information](https://pyinstaller.org/en/stable/runtime-information.html)
