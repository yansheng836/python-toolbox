# Build Tooling Guide

English | [简体中文](BUILD_README.md)

This project ships several scripts to simplify the packaging workflow.

## Quick Start

### One-Command Build (Recommended)

```bash
python build.py
```

The script runs these steps automatically:

1. Generate the version info file
2. Verify all dependencies
3. Clean old build artifacts
4. Run PyInstaller packaging
5. Verify the build result

### Manual Build

If you need more control, run each step yourself:

```bash
# 1. Generate version info (read from config.py)
python generate_version_info.py

# 2. Verify dependencies
python verify_packaging.py

# 3. Clean old artifacts (only build/; keep dist/ historical outputs)
rmdir /s /q build       # Windows
# rm -rf build          # Linux/macOS

# 4. Build
pyinstaller toolbox.spec
```

## Script Reference

### `build.py`

Automated build script that runs the complete packaging pipeline.

**When to use**: everyday builds — one command does it all

### `generate_version_info.py`

Generates the `version_info.txt` version info file from `config.py`.

**When to use**:

- After changing the version number or app info in `config.py`
- When updating the Windows executable's property info

### `verify_packaging.py`

Verifies that every required module imports correctly.

**When to use**:

- Pre-build dependency check
- After adding a new plugin, verify it can be imported
- Troubleshooting missing modules after packaging

## Modifying App Info

All app info is centralized in `config.py`:

```python
APP_NAME = "工具箱"
APP_VERSION = "2.0.6"
APP_DESCRIPTION = "批量处理工具，支持图片压缩、PDF转换、格式转换、拼接和PDF合并"
APP_COPYRIGHT = "© 2026 yansheng836"
APP_WEBSITE_URL = "https://github.com/yansheng836/python-toolbox"
```

After editing:

1. Run `python generate_version_info.py` to refresh the version info
2. Run `python build.py` to rebuild

## Adding a New Plugin

1. Create the plugin file in `plugins/` (e.g. `my_plugin.py`)
2. Add `'plugins.my_plugin'` to `hiddenimports` in `toolbox.spec`
3. Run `python verify_packaging.py` to verify
4. Run `python build.py` to rebuild

## Troubleshooting

See `PACKAGING_GUIDE.en.md` for the detailed troubleshooting guide.

Common issues:

- **Missing modules after packaging**: check `hiddenimports` in `toolbox.spec`
- **Version info not showing**: make sure `version_info.txt` exists and is well-formed
- **Oversized binary**: check `excludes` in `toolbox.spec` and drop unneeded modules
