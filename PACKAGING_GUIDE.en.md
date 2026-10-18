# Packaging Problem Analysis and Solution

English | [简体中文](PACKAGING_GUIDE.md)

## Problem Description

The packaged app is missing these feature modules:

1. **Batch Image Scaling** (`plugins/image_scaler.py`)
2. **Settings** (`SettingsPlugin` in `toolbox.py`)

## Root Cause

### Dynamic Import Issue

When analyzing code dependencies, PyInstaller only detects **static imports** (such as `import xxx` or `from xxx import yyy`) and cannot automatically detect **dynamically imported** modules.

The `load_plugins()` method in `toolbox.py` (lines 2200-2230) loads plugins dynamically via `importlib`:

```python
def load_plugins(self):
    # ...
    for file in plugins_dir.glob("*.py"):
        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # dynamically loaded
```

This dynamic loading prevents PyInstaller from automatically discovering the `plugins/image_scaler.py` module.

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
    'plugins.image_scaler',  # new

    # PIL/Pillow core modules
    'PIL',
    'PIL.Image',
    'PIL.ImageFilter',
    'PIL.ImageEnhance',
    'PIL.ImageDraw',  # new
    'PIL.ImageFont',  # new

    # PyQt6 core modules
    'PyQt6.sip',

    # PDF conversion libraries
    'img2pdf',
    'fitz',
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

```bash
# Windows
rmdir /s /q build dist

# Linux/macOS
rm -rf build dist
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
- ✓ The sidebar shows "Image Scaler"
- ✓ The sidebar shows "Settings"
- ✓ "Image Scaler" opens normally
- ✓ "Settings" opens and can switch themes

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
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "批量处理工具，支持图片压缩、PDF转换、格式转换和拼接"
APP_COPYRIGHT = "© 2026 yansheng836"
```

Then run `python generate_version_info.py` to regenerate the version info file.

### Windows File Properties

Right-click the packaged `.exe` → Properties → Details shows:

- File description: Batch processing tool with image compression, PDF conversion, format conversion and stitching
- Product name: ToolBox
- Product version: 1.0.0.0
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
- [ ] The sidebar shows all tools (including "Image Scaler" and "Settings")
- [ ] Image compression works
- [ ] Image to PDF works
- [ ] Image format conversion works
- [ ] Image stitching works
- [ ] **Batch image scaling works**
- [ ] **The settings page opens**
- [ ] **Theme switching works**

## References

- [PyInstaller Docs - Hidden Imports](https://pyinstaller.org/en/stable/when-things-go-wrong.html#listing-hidden-imports)
- [PyInstaller Docs - Runtime Information](https://pyinstaller.org/en/stable/runtime-information.html)
