# PyInstaller Excludes Reference

English | [简体中文](PYINSTALLER_EXCLUDES.md)

## ⚠️ Important

Be very careful when excluding modules! Some modules that look unnecessary are actually dependencies of PyInstaller or other libraries.

## ✅ Safe to Exclude

### GUI Frameworks

```python
'tkinter',
'_tkinter',
```

**Note:** The project uses PyQt6; tkinter is not needed

### Test Frameworks

```python
'unittest',
'test',
'tests',
'doctest',
'pytest',
```

**Note:** Test frameworks are not needed in production

### Development Tools

```python
'pydoc',
'lib2to3',
'distutils',
'setuptools',
'pip',
'wheel',
'pkg_resources',
```

**Note:** These development tools are not needed after packaging

### Network Protocols (Unused)

```python
'ftplib',
'telnetlib',
'poplib',
'imaplib',
'smtplib',
'xmlrpc',
```

**Note:** The project does not use these network protocols

### Databases

```python
'sqlite3',
```

**Note:** The project does not use a database

### Scientific Computing Libraries

```python
'matplotlib',
'pandas',
'numpy',
'scipy',
'sklearn',
'tensorflow',
'torch',
'keras',
```

**Note:** No scientific computing is needed

### Unneeded PyQt6 Modules

```python
'PyQt6.QtWebEngine',
'PyQt6.QtWebEngineCore',
'PyQt6.QtWebEngineWidgets',
'PyQt6.QtNetwork',
'PyQt6.QtSql',
'PyQt6.QtTest',
# ... and so on
```

**Note:** Only QtCore, QtGui, and QtWidgets are used

## ❌ Must Not Be Excluded

### PyInstaller Core Dependencies

```python
# Do not exclude these!
'zipfile',      # Required by PyInstaller
'inspect',      # Required by PyInstaller
'io',           # Basic I/O
'os',           # Operating system interface
'sys',          # System-specific
'pathlib',      # Path operations
'importlib',    # Dynamic imports
```

### Common Standard Library

```python
# Exclude with caution
'json',         # JSON handling (may be needed by config.py)
'base64',       # Base64 encoding (imported by toolbox.py)
'dataclasses',  # Data classes (used by toolbox.py)
'enum',         # Enum types (used by toolbox.py)
'typing',       # Type hints
```

### Compression and Archives

```python
# Do not exclude
'gzip',         # Some libraries may need it
'bz2',          # Some libraries may need it
'lzma',         # Some libraries may need it
'zipfile',      # Required by PyInstaller!
'tarfile',      # Some libraries may need it
```

### Networking Basics

```python
# Exclude with caution
'socket',       # Basic networking (some libraries may need it)
'ssl',          # SSL/TLS (needed for HTTPS)
'http',         # HTTP client (some libraries may need it)
'urllib',       # URL handling
```

### Serialization

```python
# Exclude with caution
'pickle',       # Python object serialization (QSettings may need it)
'shelve',       # Persistent storage
```

### Others

```python
# Exclude with caution
'email',        # Email handling (some libraries may need it)
'csv',          # CSV handling
'xml',          # XML handling
```

## 🔍 How to Tell Whether a Module Can Be Excluded

### Method 1: Check Imports

```bash
# Search the project for usages of the module
grep -r "import module_name" .
grep -r "from module_name" .
```

### Method 2: Test the Build

1. Add it to excludes
2. Build and test
3. Exercise every feature
4. If something breaks, remove it from excludes

### Method 3: Inspect Dependencies

```bash
# Inspect the dependency tree with pipdeptree
pip install pipdeptree
pipdeptree
```

## 📊 Exclusion Strategies Compared

| Strategy | Size | Risk | Recommended |
|----------|------|------|------|
| Exclude nothing | ~250MB | Low | ❌ |
| Conservative (current) | ~80-100MB | Low | ✅ |
| Aggressive | ~60-80MB | High | ❌ |

## 🐛 Common Errors

### Error 1: ModuleNotFoundError: No module named 'zipfile'

**Cause:** zipfile was excluded by mistake
**Fix:** Remove zipfile from excludes

### Error 2: ModuleNotFoundError: No module named 'inspect'

**Cause:** inspect was excluded by mistake
**Fix:** Remove inspect from excludes

### Error 3: App Misbehaves After Launch

**Cause:** A module needed by the app or its dependencies was excluded
**Fix:** Test one by one to find the required modules

## 💡 Best Practices

1. **Start conservative**: exclude only clearly unneeded modules first
2. **Iterate gradually**: add only a few exclusions at a time
3. **Test thoroughly**: run the full feature set after every change
4. **Record the reason**: comment in the spec file why each module is excluded
5. **Use version control**: track spec file changes with git

## 🔧 Debugging Tips

### Inspect Bundled Modules

```bash
# Inspect the modules included in the package
pyi-archive_viewer dist/Toolbox.exe
```

### Enable Verbose Logging

```bash
# Enable verbose logging while building
pyinstaller --log-level=DEBUG toolbox.spec
```

### Test a Specific Module

```python
# Test inside the packaged program
import sys
print(sys.modules.keys())
```

## 📚 References

- [PyInstaller official documentation](https://pyinstaller.org/)
- [PyInstaller guide to excluding modules](https://pyinstaller.org/en/stable/usage.html#excluding-modules)
- [Python standard library documentation](https://docs.python.org/3/library/)
