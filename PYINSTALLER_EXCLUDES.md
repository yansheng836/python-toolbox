# PyInstaller Excludes 参考指南

## ⚠️ 重要提示

排除模块时要非常谨慎！某些看似不需要的模块实际上是 PyInstaller 或其他库的依赖。

## ✅ 安全排除的模块

### GUI 框架
```python
'tkinter',
'_tkinter',
```
**说明：** 项目使用 PyQt6，不需要 tkinter

### 测试框架
```python
'unittest',
'test',
'tests',
'doctest',
'pytest',
```
**说明：** 生产环境不需要测试框架

### 开发工具
```python
'pydoc',
'lib2to3',
'distutils',
'setuptools',
'pip',
'wheel',
'pkg_resources',
```
**说明：** 打包后不需要这些开发工具

### 网络协议（不使用的）
```python
'ftplib',
'telnetlib',
'poplib',
'imaplib',
'smtplib',
'xmlrpc',
```
**说明：** 项目不需要这些网络协议

### 数据库
```python
'sqlite3',
```
**说明：** 项目不使用数据库

### 科学计算库
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
**说明：** 项目不需要科学计算

### PyQt6 不需要的模块
```python
'PyQt6.QtWebEngine',
'PyQt6.QtWebEngineCore',
'PyQt6.QtWebEngineWidgets',
'PyQt6.QtNetwork',
'PyQt6.QtSql',
'PyQt6.QtTest',
# ... 等等
```
**说明：** 只使用 QtCore、QtGui、QtWidgets

## ❌ 不能排除的模块

### PyInstaller 核心依赖
```python
# 不要排除这些！
'zipfile',      # PyInstaller 需要
'inspect',      # PyInstaller 需要
'io',           # 基础 I/O
'os',           # 操作系统接口
'sys',          # 系统相关
'pathlib',      # 路径操作
'importlib',    # 动态导入
```

### 常用标准库
```python
# 谨慎排除这些
'json',         # JSON 处理（config.py 可能需要）
'base64',       # Base64 编码（toolbox.py 导入了）
'dataclasses',  # 数据类（toolbox.py 使用了）
'enum',         # 枚举类型（toolbox.py 使用了）
'typing',       # 类型提示
```

### 压缩和归档
```python
# 不要排除
'gzip',         # 某些库可能需要
'bz2',          # 某些库可能需要
'lzma',         # 某些库可能需要
'zipfile',      # PyInstaller 需要！
'tarfile',      # 某些库可能需要
```

### 网络基础
```python
# 谨慎排除
'socket',       # 基础网络（某些库可能需要）
'ssl',          # SSL/TLS（HTTPS 需要）
'http',         # HTTP 客户端（某些库可能需要）
'urllib',       # URL 处理
```

### 序列化
```python
# 谨慎排除
'pickle',       # Python 对象序列化（QSettings 可能需要）
'shelve',       # 持久化存储
```

### 其他
```python
# 谨慎排除
'email',        # 邮件处理（某些库可能需要）
'csv',          # CSV 处理
'xml',          # XML 处理
```

## 🔍 如何判断是否可以排除

### 方法 1：检查导入
```bash
# 搜索项目中是否使用了该模块
grep -r "import module_name" .
grep -r "from module_name" .
```

### 方法 2：测试打包
1. 添加到 excludes
2. 打包测试
3. 运行所有功能
4. 如果出错，从 excludes 中移除

### 方法 3：查看依赖
```bash
# 使用 pipdeptree 查看依赖树
pip install pipdeptree
pipdeptree
```

## 📊 排除效果对比

| 策略 | 文件大小 | 风险 | 推荐 |
|------|---------|------|------|
| 不排除任何模块 | ~250MB | 低 | ❌ |
| 保守排除（当前） | ~80-100MB | 低 | ✅ |
| 激进排除 | ~60-80MB | 高 | ❌ |

## 🐛 常见错误

### 错误 1：ModuleNotFoundError: No module named 'zipfile'
**原因：** 错误地排除了 zipfile
**解决：** 从 excludes 中移除 zipfile

### 错误 2：ModuleNotFoundError: No module named 'inspect'
**原因：** 错误地排除了 inspect
**解决：** 从 excludes 中移除 inspect

### 错误 3：应用启动后功能异常
**原因：** 排除了应用或其依赖需要的模块
**解决：** 逐个测试，找出需要的模块

## 💡 最佳实践

1. **从保守开始**：先排除明确不需要的模块
2. **逐步优化**：每次只添加少量排除项
3. **充分测试**：每次修改后都要完整测试所有功能
4. **记录原因**：在 spec 文件中注释为什么排除某个模块
5. **版本控制**：使用 git 跟踪 spec 文件的变化

## 🔧 调试技巧

### 查看打包包含的模块
```bash
# 打包后查看包含的模块
pyi-archive_viewer dist/Toolbox.exe
```

### 启用详细日志
```bash
# 打包时启用详细日志
pyinstaller --log-level=DEBUG toolbox.spec
```

### 测试特定模块
```python
# 在打包后的程序中测试
import sys
print(sys.modules.keys())
```

## 📚 参考资料

- [PyInstaller 官方文档](https://pyinstaller.org/)
- [PyInstaller 排除模块指南](https://pyinstaller.org/en/stable/usage.html#excluding-modules)
- [Python 标准库文档](https://docs.python.org/3/library/)
