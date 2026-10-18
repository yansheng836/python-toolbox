# Packaging Checklist

English | [简体中文](BUILD_CHECKLIST.md)

## Pre-Build Checks

### 1. Required Files

- [x] main.py - Application entry point
- [x] toolbox.py - Main application class
- [x] config.py - Configuration file
- [x] menu_system.py - Menu system
- [x] settings_page.py - Settings page
- [x] favicon.ico - Application icon
- [x] plugins/ - Plugin directory
  - [x] image_scaler.py - Image scaling plugin

### 2. Dependencies

```bash
pip list | grep -E "PyQt6|Pillow|img2pdf|PyMuPDF|pyinstaller"
```

You should see:

- PyQt6 >= 6.4.0
- Pillow >= 9.0.0
- img2pdf >= 0.4.4
- PyMuPDF >= 1.21.0
- pyinstaller >= 5.7.0

### 3. Code Checks

- [x] settings_page.py imports QGraphicsDropShadowEffect and QColor
- [x] menu_system.py imports QApplication
- [x] Every plugin can import the toolbox module

### 4. toolbox.spec Configuration

- [x] Entry point set to main.py
- [x] datas includes all required files:
  - config.py
  - toolbox.py
  - menu_system.py
  - settings_page.py
  - plugins/
  - favicon.ico
- [x] hiddenimports includes all project modules
- [x] excludes removes unneeded modules

## Build Commands

```bash
# Clean old build artifacts
rm -rf build/ dist/

# Build from the spec file
pyinstaller toolbox.spec

# Inspect the generated files
ls -lh dist/
```

## Post-Build Testing

### 1. Basic Functionality

- [ ] The app starts normally
- [ ] The welcome page displays correctly
- [ ] Sidebar navigation works

### 2. Tool Features

- [ ] Image compression works
- [ ] Image format conversion works
- [ ] Image to PDF works
- [ ] Image stitching works
- [ ] Batch image scaling works

### 3. Settings

- [ ] The settings page opens
- [ ] Theme switching works
- [ ] About info displays correctly

### 4. Plugin System

- [ ] Plugins load normally
- [ ] Plugin features work

## Common Issues

### Issue 1: Missing Module Error

**Symptom:** "No module named 'xxx'" at runtime
**Cause:**

- The module was mistakenly added to the excludes list
- The module was not auto-detected by PyInstaller

**Solution:**

1. For standard library modules (e.g. zipfile, inspect), remove them from excludes
2. For project modules, add them to hiddenimports
3. See PYINSTALLER_EXCLUDES.en.md for modules that must not be excluded

### Issue 2: Icon Not Showing

**Symptom:** The window icon or tray icon does not appear
**Solution:** Confirm favicon.ico is listed in datas with the correct path

### Issue 3: Plugin Loading Fails

**Symptom:** Plugin features are missing
**Solution:** Confirm the plugins/ directory is listed in datas

### Issue 4: Wrong App Info

**Symptom:** App name, version, etc. show default values
**Solution:** Confirm config.py is listed in datas

## File Size Optimization

Current expected size: 60-80MB

To optimize further:

1. Check whether unneeded DLLs are being bundled
2. Use UPX compression (already enabled in the spec)
3. Consider compressing the final exe with 7-Zip

## Release

1. Update the version number in config.py
2. Update CHANGELOG.md
3. Run the full test suite
4. Build
5. Test the packaged program
6. Create a GitHub Release
7. Upload the executables
