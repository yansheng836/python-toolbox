# 打包工具说明

本项目提供了多个脚本来简化打包流程。

## 快速开始

### 一键打包（推荐）

```bash
python build.py
```

这个脚本会自动执行以下步骤：

1. 生成版本信息文件
2. 验证所有依赖
3. 清理旧的打包文件
4. 执行 PyInstaller 打包
5. 验证打包结果

### 手动打包

如果需要更多控制，可以手动执行各个步骤：

```bash
# 1. 生成版本信息（从 config.py 读取）
python generate_version_info.py

# 2. 验证依赖
python verify_packaging.py

# 3. 清理旧文件
rmdir /s /q build dist  # Windows
# rm -rf build dist     # Linux/macOS

# 4. 打包
pyinstaller toolbox.spec
```

## 脚本说明

### `build.py`

自动化打包脚本，执行完整的打包流程。

**使用场景**: 日常打包，一键完成所有步骤

### `generate_version_info.py`

从 `config.py` 自动生成 `version_info.txt` 版本信息文件。

**使用场景**:

- 修改了 `config.py` 中的版本号或应用信息后
- 需要更新 Windows 可执行文件的属性信息

### `verify_packaging.py`

验证所有必需的模块是否可以正确导入。

**使用场景**:

- 打包前检查依赖是否完整
- 添加新插件后验证是否能被正确导入
- 排查打包后模块缺失的问题

## 修改应用信息

所有应用信息集中在 `config.py` 中：

```python
APP_NAME = "工具箱"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "批量处理工具，支持图片压缩、PDF转换、格式转换和拼接"
APP_COPYRIGHT = "© 2026 yansheng836"
APP_WEBSITE_URL = "https://github.com/yansheng836/python-toolbox"
```

修改后：

1. 运行 `python generate_version_info.py` 更新版本信息
2. 运行 `python build.py` 重新打包

## 添加新插件

1. 在 `plugins/` 目录创建新插件文件（如 `my_plugin.py`）
2. 在 `toolbox.spec` 的 `hiddenimports` 中添加 `'plugins.my_plugin'`
3. 运行 `python verify_packaging.py` 验证
4. 运行 `python build.py` 重新打包

## 故障排除

详细的故障排除指南请参考 `PACKAGING_GUIDE.md`。

常见问题：

- **打包后缺少模块**: 检查 `toolbox.spec` 的 `hiddenimports` 配置
- **版本信息不显示**: 确保 `version_info.txt` 存在且格式正确
- **文件过大**: 检查 `toolbox.spec` 的 `excludes` 配置，排除不需要的模块
