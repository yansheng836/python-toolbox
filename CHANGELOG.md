# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/).

## [Unreleased]

### Added
- 完善打包配置，添加版本信息和自动化脚本
  - 创建 `generate_version_info.py` 自动从 config.py 生成版本信息文件
  - 创建 `verify_packaging.py` 验证所有依赖模块是否可正确导入
  - 创建 `build.py` 一键自动化打包脚本
  - 添加 `PACKAGING_GUIDE.md` 详细的打包问题分析和解决方案文档
  - 添加 `BUILD_README.md` 打包工具使用说明
  - 添加 `version_info.txt` 为 Windows 可执行文件提供版本元数据

### Changed
- 修改 `toolbox.spec` 从 config.py 读取应用信息（名称、版本、描述、版权）
- 在 hiddenimports 中添加 `plugins.image_scaler` 解决动态加载插件打包缺失问题
- 更新 `CLAUDE.md` 添加打包相关命令和注意事项

### Fixed
- 修复打包后缺少"图片批量缩放"和"设置"模块的问题（动态导入问题）
- 修复打包后的可执行文件缺少版本信息和元数据的问题

### Removed
- 删除 `pyinstaller.bat` 替换为跨平台的 `pyinstaller.sh`

## [v1.0.0] - 2026-04-25

### Added
- 添加入口点和菜单系统
- 添加测试文件并组织结构

### Changed
- 更新文档并修复打包配置
- 优化 UI 边框样式，提升视觉效果
- 将设置按钮移动到侧边栏最后位置
- 格式化代码

### Fixed
- 修复所有剩余硬编码颜色问题
- 修复 SettingsPlugin 中 copyright_label 未定义的错误
- 修复浅色主题文字可见性问题
- 修复主页文本空白问题，解决循环导入
- 修复 APP_VERSION 未定义的错误
- 修复主题按钮闪退问题，实现正确的焦点状态
- 实现主题切换功能，支持深色/浅色主题
- 修复设置页面插件注册和卡片构造错误

### Maintenance
- 更新 settings.local.json 并删除测试文件

## [v0.0.1] - 2026-04-24

### Added
- 初始化项目
- 添加图片压缩功能
- 添加图片转 PDF 功能
  - 支持压缩选项
  - 添加压缩 UI 控件
  - 添加 compress_image 辅助方法
  - 支持三种 PDF 转换库（img2pdf、PyMuPDF、PIL）
- 添加图片格式批量转换功能
- 添加图片拼接功能
- 添加图片批量缩放功能
- 添加自定义图标支持，修复窗口和任务栏图标显示问题
- 添加 PyInstaller 打包配置（toolbox.spec）
- 添加 Claude Code 配置文件
- 添加 CLAUDE.md 文档，包含构建命令和架构概述
- 添加 TODO 列表到 README

### Changed
- 优化图片批量缩放 UI 并统一插件样式
- 优化图片批量缩放设置布局
- 改进欢迎页面 UI 并添加响应式图标缩放
- 重组项目结构并整合测试文件
- 优化 PyInstaller spec 以减小 exe 大小
- 更新 README 和 CLAUDE.md 以反映当前状态
- 更新 README.md 说明图片转 PDF 的压缩功能
- 更换 ico 图标

### Fixed
- 修复图片批量缩放开始按钮报错问题
- 修复图片批量缩放功能显示问题
- 修复插件加载逻辑和图片缩放翻译
- 修复功能按钮颜色
- 修复关闭按钮直接退出程序，修改图片拼接图标
- 修复 ImageToPDF 中 remove_selected 行为
- 修复压缩完成后清除状态标签
- 修复卡片内容布局冲突导致按钮无响应
- 修复 register_plugin 中 lambda 闭包捕获错误的插件名称
- 修复点击侧边栏按钮崩溃和设置布局父级问题

[Unreleased]: https://github.com/yansheng836/python-toolbox/compare/v1.0.0...HEAD
[v1.0.0]: https://github.com/yansheng836/python-toolbox/compare/v0.0.1...v1.0.0
[v0.0.1]: https://github.com/yansheng836/python-toolbox/releases/tag/v0.0.1
