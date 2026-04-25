# 打包问题分析与解决方案

## 问题描述

打包后的应用缺少以下功能模块：
1. **图片批量缩放** (`plugins/image_scaler.py`)
2. **设置** (`SettingsPlugin` in `toolbox.py`)

## 根本原因

### 动态导入问题

PyInstaller 在分析代码依赖时，只能检测**静态导入**（如 `import xxx` 或 `from xxx import yyy`），无法自动检测**动态导入**的模块。

在 `toolbox.py` 的 `load_plugins()` 方法中（第2200-2230行），使用了 `importlib` 动态加载插件：

```python
def load_plugins(self):
    # ...
    for file in plugins_dir.glob("*.py"):
        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # 动态加载
```

这种动态加载方式导致 PyInstaller 无法自动发现 `plugins/image_scaler.py` 模块。

### 解决方法

在 `toolbox.spec` 的 `hiddenimports` 列表中**明确指定**所有动态加载的模块：

```python
hiddenimports=[
    # 项目模块
    'toolbox',
    'config',
    'menu_system',
    'settings_page',

    # ⭐ 插件模块（动态加载的插件必须明确指定）
    'plugins.image_scaler',  # 新增

    # PIL/Pillow 核心模块
    'PIL',
    'PIL.Image',
    'PIL.ImageFilter',
    'PIL.ImageEnhance',
    'PIL.ImageDraw',  # 新增
    'PIL.ImageFont',  # 新增

    # PyQt6 核心模块
    'PyQt6.sip',

    # PDF 转换库
    'img2pdf',
    'fitz',
],
```

## 打包步骤

### 1. 生成版本信息文件（可选）

```bash
python generate_version_info.py
```

这会从 `config.py` 自动生成 `version_info.txt`，包含应用的版本信息、描述、版权等元数据。

### 2. 验证依赖（打包前）

```bash
python verify_packaging.py
```

确保所有必需模块都能正确导入。

### 3. 清理旧的打包文件

```bash
# Windows
rmdir /s /q build dist

# Linux/macOS
rm -rf build dist
```

### 4. 使用 spec 文件打包

```bash
pyinstaller toolbox.spec
```

### 5. 测试打包后的应用

```bash
# Windows
dist\工具箱.exe

# Linux/macOS
./dist/工具箱
```

检查以下功能是否正常：
- ✓ 应用能正常启动
- ✓ 右键查看文件属性，版本信息是否正确显示
- ✓ 侧边栏是否显示"图片批量缩放"
- ✓ 侧边栏是否显示"设置"
- ✓ 点击"图片批量缩放"是否能正常打开
- ✓ 点击"设置"是否能正常打开并切换主题

## 版本信息配置

### 自动生成版本信息

`toolbox.spec` 已配置为从 `config.py` 读取应用信息：

```python
# 从 config.py 导入应用信息
from config import APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_COPYRIGHT

# 在 EXE 配置中使用
exe = EXE(
    # ...
    name=APP_NAME,           # 使用配置的应用名称
    version='version_info.txt',  # 版本信息文件
    # ...
)
```

### 修改应用信息

只需修改 `config.py` 中的变量：

```python
APP_NAME = "工具箱"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "批量处理工具，支持图片压缩、PDF转换、格式转换和拼接"
APP_COPYRIGHT = "© 2026 yansheng836"
```

然后运行 `python generate_version_info.py` 重新生成版本信息文件。

### Windows 文件属性显示

打包后的 `.exe` 文件右键 → 属性 → 详细信息，会显示：
- 文件描述：批量处理工具，支持图片压缩、PDF转换、格式转换和拼接
- 产品名称：工具箱
- 产品版本：1.0.0.0
- 版权：© 2026 yansheng836
- 公司：yansheng836

## 常见问题

### Q1: 为什么 `datas` 中已经包含了 `('plugins', 'plugins')`，还需要在 `hiddenimports` 中指定？

**A:** 
- `datas` 只是将文件作为**数据文件**复制到打包目录
- `hiddenimports` 是告诉 PyInstaller 将模块作为**Python 可导入模块**打包
- 动态加载的模块需要同时在两个地方指定

### Q2: 如何添加新的插件？

**A:** 
1. 在 `plugins/` 目录创建新的插件文件（如 `my_plugin.py`）
2. 在 `toolbox.spec` 的 `hiddenimports` 中添加 `'plugins.my_plugin'`
3. 重新打包

### Q3: 设置插件为什么会缺失？

**A:** 
`SettingsPlugin` 定义在 `toolbox.py` 中，理论上应该被自动包含。但如果仍然缺失，可以：
1. 确保 `toolbox.py` 在 `hiddenimports` 中
2. 检查 `toolbox.py` 是否在 `datas` 中被正确复制

## 验证清单

打包完成后，请验证以下内容：

- [ ] 应用能正常启动
- [ ] 侧边栏显示所有工具（包括"图片批量缩放"和"设置"）
- [ ] 图片压缩功能正常
- [ ] 图片转PDF功能正常
- [ ] 图片格式转换功能正常
- [ ] 图片拼接功能正常
- [ ] **图片批量缩放功能正常**
- [ ] **设置页面能打开**
- [ ] **主题切换功能正常**

## 参考资料

- [PyInstaller 文档 - Hidden Imports](https://pyinstaller.org/en/stable/when-things-go-wrong.html#listing-hidden-imports)
- [PyInstaller 文档 - Runtime Information](https://pyinstaller.org/en/stable/runtime-information.html)
