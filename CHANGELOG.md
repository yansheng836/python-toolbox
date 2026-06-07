# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/).

[v2.0.4]: https://github.com/yansheng836/python-toolbox/compare/v2.0.3...v2.0.4
[v2.0.3]: https://github.com/yansheng836/python-toolbox/compare/v2.0.2...v2.0.3
[v2.0.2]: https://github.com/yansheng836/python-toolbox/compare/v2.0.1...v2.0.2
[v2.0.1]: https://github.com/yansheng836/python-toolbox/compare/v2.0.0...v2.0.1
[v2.0.0]: https://github.com/yansheng836/python-toolbox/compare/v1.0.11...v2.0.0
[v1.0.11]: https://github.com/yansheng836/python-toolbox/compare/v1.0.10...v1.0.11
[v1.0.10]: https://github.com/yansheng836/python-toolbox/compare/v1.0.9...v1.0.10
[v1.0.9]: https://github.com/yansheng836/python-toolbox/compare/v1.0.8...v1.0.9
[v1.0.8]: https://github.com/yansheng836/python-toolbox/compare/v1.0.7...v1.0.8
[v1.0.7]: https://github.com/yansheng836/python-toolbox/compare/v1.0.6...v1.0.7
[v1.0.6]: https://github.com/yansheng836/python-toolbox/compare/v1.0.5...v1.0.6
[v1.0.5]: https://github.com/yansheng836/python-toolbox/compare/v1.0.4...v1.0.5
[v1.0.4]: https://github.com/yansheng836/python-toolbox/compare/v1.0.3...v1.0.4
[v1.0.3]: https://github.com/yansheng836/python-toolbox/compare/v1.0.2...v1.0.3
[v1.0.2]: https://github.com/yansheng836/python-toolbox/compare/v1.0.1...v1.0.2
[v1.0.1]: https://github.com/yansheng836/python-toolbox/compare/v1.0.0...v1.0.1
[v1.0.0]: https://github.com/yansheng836/python-toolbox/compare/v0.0.1...v1.0.0
[v0.0.1]: https://github.com/yansheng836/python-toolbox/releases/tag/v0.0.1

## [v2.0.4] - 2026-05-30

### Added

- 文件去重功能增强
  - 选择文件夹后自动开始扫描
  - 文件删除后增加自动扫描开关
- 添加 tag 触发自动打包并创建 GitHub Release
- 添加 macOS 打包支持（.app → .dmg → tar.gz）
- 重构 CI/CD 为 Matrix 构建策略（Windows + macOS）
- 添加 .codacy.yml 配置文件

### Changed

- 统一 Release 打包规范，优化打包文件名和构建流程
- 统一进度条样式并去除边框细线

### Fixed

- 修复 Windows runner 打包问题（pandoc 安装、bash 语法兼容性、中文编码）
- 修复 release.yml YAML 语法错误（Windows 打包改用 7z）
- 修复 macOS 打包图标文件不存在问题
- 修复 CLAUDE.md 中 Liquid 模板冲突
- 优化 Release Notes 生成逻辑
- 更新 CI Action 组件版本

## [v2.0.3] - 2026-05-07

### Added

- 图片拼接支持无限张数，超尺寸自动分批处理
- 在设置页关于中添加检查更新和问题反馈链接（配置化管理）
- 新增 LICENSE.txt 许可证文件

### Changed

- 替换 README 截图预览为实际功能截图
- 在用户手册各功能标题后添加对应截图
- README 导航栏添加用户手册链接和许可证说明
- 精简 TODO 列表，移除必要性较低的待办项

### Fixed

- 统一所有插件描述文字颜色，修复主题切换时颜色不一致
- 弹窗按钮文字颜色改为白色，提升浅色主题下可读性
- 图片拼接进度条改为按每张图片更新，支持百分比显示

## [v2.0.2] - 2026-05-06

### Added

- GitHub Actions 添加打包验证和构建产物上传
- CI 流程添加 Python 语法检查和 Windows 环境支持

### Fixed

- 修复 CI 配置中 YAML 语法错误（jobs 拼写、always() 表达式）
- 修复 CRLF 换行符导致的 YAML 解析错误
- 修复 build.py 编码问题并优化打包验证流程

## [v2.0.1] - 2026-05-06

### Added

- 实现响应式布局，支持窗口大小自适应
  - 统一插件布局，移除 `addStretch()` 让内容自然填充
  - `FileListPanel` 组件使用 `Expanding` 策略自适应
  - 欢迎页卡片支持自动轮播效果
- 新增 `SelectableLabel` 组件，支持文本选择和复制
  - 所有信息文本（版本号、文件路径、状态消息等）使用该组件
  - 用户可自由选择和复制文本内容
- 新增性能优化强制性标准（Rule #11）
  - 插件处理图片/文件时必须正确管理内存
  - 使用上下文管理器、显式关闭、批量处理等模式

### Changed

- 更新 `CLAUDE.md` 新增多项强制性标准
  - 文本可复制性标准（Rule #7）
  - 响应式布局标准（Rule #8）
  - 文件操作标准（Rule #9、#10）
- 优化 `toolbox.spec` 使用 `os.path.abspath('.')` 替代 `__file__` 避免未定义错误

### Fixed

- 修复插件内存泄漏和文件句柄未释放问题
  - 所有图片处理插件改用上下文管理器 `with Image.open() as img:`
  - 显式调用 `img.close()` 释放内存
  - 图片拼接改为逐张处理，避免一次性加载所有图片到内存
- 为图片压缩、缩放、格式转换添加输出目录可写检查
- 为图片拼接、PDF合并、PDF拆分添加文件占用预检查
  - 在写入前检测目标文件是否被占用（如 WPS、Adobe Reader 等）
  - 提供清晰的错误提示，指导用户关闭占用程序
- 修复图片转 PDF 临时文件问题
  - 修复临时文件名冲突
  - 修复清理时的路径问题（使用 `os.path.abspath()` + `os.path.exists()` 检查）
  - 目标文件被占用时提前检测并提示

## [v2.0.0] - 2026-05-05

### Added

- 新增面向非技术用户的 Markdown 格式使用手册（`用户手册.md`）
  - 涵盖全部 8 个功能的详细使用步骤和适用场景
  - 包含界面介绍、通用操作元素、主题切换、常见问题等章节
  - 纯用户视角编写，无技术术语
- 全面更新 `README.md`
  - 重写功能特色表格，涵盖全部工具和通用特性
  - 新增截图预览区域（ASCII 占位符）
  - 新增简明使用指南，每个工具列出操作步骤
  - 更新插件开发章节，添加配置示例和现有插件列表
  - 新增打包发布章节（环境要求、打包步骤）
  - 优化排版和可读性
- 新增 `CLAUDE.md` 语法检查强制规则
  - 修改 Python 文件后必须进行语法检查
  - 包括语法验证、缩进检查、导入验证、行尾检查
- 恢复 `README.md` 中的程序介绍图 `ToolBox.png`
- 更新 `CHANGELOG.md`，采用 Keep a Changelog 标准格式

### Changed

- 更新所有版本号至 v2.0.0
  - `config.py`: APP_VERSION = "2.0.0"
  - `toolbox.py`: ToolPlugin.version = "2.0.0"
  - `settings_page.py`: version = "2.0.0"
  - `test/test_app.py`: 两处版本号
  - `test/toolbox2.py`: 版本号
- 重新整理 `CLAUDE.md`
  - 新增 Quick Reference 速查表，集中展示 6 条强制规则
  - 合并重复的 Code Reuse 章节，统一到 Development Standards
  - 更新 Project Structure 与实际文件结构一致（含 common/、plugins/、8个插件）
  - 新增 Plugin Checklist 和 Adding a Plugin 完整示例
  - 精简冗余描述，优化章节层级结构
- 统一模块可用性检查到 `common/utils.py`
  - 移除不必要的 try-catch
  - 集中管理 `PIL_AVAILABLE`、`FITZ_AVAILABLE`、`IMG2PDF_AVAILABLE`
- 优化插件代码结构
  - 新增 `PDF_COLUMNS` 定义到 `common/utils.py`
  - 添加缺失的 `PDFMergeWorker` 和 `PDFSplitWorker` 类
  - 统一管理 `ActionPanel` 导入

### Fixed

- 修复多个插件未定义名称问题
  - `image_compressor.py`: 添加 `Image` 条件导入
  - `image_format_converter.py`: 添加 `Image` 条件导入
  - `image_scaler.py`: 添加 `Image` 条件导入
  - `image_stitcher.py`: 添加 `Image` 条件导入
  - `image_to_pdf.py`: 添加 `Image`、`fitz`、`img2pdf` 条件导入
  - `pdf_merger.py`: 添加 `ActionPanel`、`PDF_COLUMNS` 导入和 Worker 类
  - `pdf_splitter.py`: 添加 `QLineEdit`、`get_create_time` 导入和 Worker 类
  - `common/utils.py`: 修复重复导入 `fitz` 问题
  - `test/test_icon.py`: 添加 `Qt` 导入
- 修复 `file_deduplicator.py` 主题切换报错
  - 重命名 `FileDeduplicatorWidget.update_theme` 为 `apply_theme`
  - 修复插件注册时调用 `self.widget.apply_theme(theme)` 失败的问题
- 清理各文件未使用的导入
  - 移除 `toolbox.py` 未使用的配置和组件导入
  - 移除 `common/action_panel.py` 未使用的 `show_error` 导入
  - 移除 `common/utils.py` 未使用的 `img2pdf` 导入
  - 清理各插件未使用的导入（`sys`、`time`、`QBrush`、`QSizePolicy` 等）
  - 修复过度清理导致的 `Qt`、`List`、`QFileDialog` 缺失问题
- 修复 `common/utils.py` 中 `get_pdf_pages` 方法
  - 添加 `FITZ_AVAILABLE` 检查，防止未定义错误

### Removed

- 移除各插件中重复的导入检查模式
  - 统一使用 `common/utils.py` 中的可用性标志

## [v1.0.11] - 2026-05-04

### Changed

- 调整文件去重删除规则下拉框顺序
- 新增文件名降序规则

## [v1.0.10] - 2026-05-03

### Added

- 统一操作按钮样式为 `ActionPanel` 标准
- 优化 PDF 拆分 PNG 输出质量

## [v1.0.9] - 2026-05-02

### Performance

- 优化 PDF 合并及文件列表性能

### Fixed

- 修复主题合规问题（文本颜色对比度）

## [v1.0.8] - 2026-05-01

### Added

- 统一图片压缩、格式转换、拼接功能布局为 `ActionPanel` 标准
  - 统一操作面板交互体验
  - 按钮 + 进度条 + 状态标签一体化

## [v1.0.7] - 2026-04-30

### Fixed

- 添加临时 PDF 和输出 PDF 的空文件验证
- 防止空文件导致处理失败

## [v1.0.6] - 2026-04-29

### Added

- 图片拼接新增"智能缩放"对齐方式（默认）
  - 自动按比例缩放图片以适应拼接画布

## [v1.0.5] - 2026-04-28

### Fixed

- 区分 JPG/JPEG 扩展名，保持原格式时保留原始扩展名
- 修复图片压缩输出文件扩展名不一致问题

## [v1.0.4] - 2026-04-27

### Fixed

- 修复图片压缩/缩放/拼接的上移下移功能
  - 改为选中行上下移动，操作更直观

## [v1.0.3] - 2026-04-26

### Added

- 将左侧和欢迎页的 emoji logo 替换为 `favicon.ico` 图标
- 为右侧内容区域添加滚动支持，适配小屏场景
- 支持手动调整窗口大小，添加窗口最大尺寸配置
- 新增插件排序功能，支持通过 `order` 属性控制侧边栏顺序
- 添加 push/PR 时运行 main.py 检查（CI/CD）

### Changed

- 重构 `config.py` 配置顺序，新增 `FONT_SIZE_24` 常量
- 统一字体大小为全局变量（`FONT_SIZE_12/14/16/20/24`）
- 将内置图片处理功能提取为独立插件
- 精简欢迎页布局，缩小 logo/标题/卡片尺寸，改为容器居中布局

### Fixed

- 修复窗口图标和控制栏图标不显示的问题
- 修复插件 `get_widget` 缺失和导入失败问题
- 修复插件实例化失败问题
- 去掉全局 QFrame 边框，卡片内添加分隔线，统一样式管理
- 调整欢迎页卡片布局，修复滚动条问题
- 修复图片拼接图标显示问题
- 修复插件 f-string QSS 转义错误

### Refactored

- 移除所有 Python 文件中未使用的 import
- 优化 main.py 检查步骤，避免复杂 shell 脚本

## [v1.0.2] - 2026-04-26

### Added

- 新增文件去重工具插件 (`plugins/file_deduplicator.py`)
  - 选择文件夹递归扫描所有文件
  - 使用 SHA-256 计算文件内容哈希
  - 按内容哈希找出重复文件并分组显示
  - 支持三种删除规则：按文件名排序、按修改时间升序/降序排序
  - 删除前显示确认对话框，列出待删除文件
  - 使用后台线程避免界面卡顿
  - 支持深色/浅色主题切换
- 新增 PDF 合并工具插件 (`plugins/pdf_merger.py`)
  - 将多个 PDF 文件合并为一个
  - 支持拖拽调整文件顺序
- 新增 PDF 拆分工具插件 (`plugins/pdf_splitter.py`)
  - 将 PDF 拆分为图片或单页 PDF
  - 支持设置拆分页数
  - 支持多种图片格式输出（PNG/JPEG/WebP）
- 新增 PDF 合并测试文件 (`test/test_pdf_merger.py`)
- 将标题字体样式全局化，统一管理字体大小和字重 (`config.py` 中 `TITLE_STYLES`)
- 更新 `README.md` 添加新功能描述
- 更新 `FEATURE_MODULES` 添加新的功能卡片

### Changed

- 更新 `toolbox.spec` 添加新插件到 hiddenimports
- 更新 `CLAUDE.md` 插件目录结构
- 更新 `verify_packaging.py` 添加新插件验证项
- 优化图片批量缩放插件 UI (`plugins/image_scaler.py`)
- 更新 `config.py` 中 APP_VERSION 至 1.0.2
- 更新 `version_info.txt` 版本信息

### Fixed

- 修复图片压缩功能中拖拽图片无法识别的问题
- 修复拖拽功能初始化顺序问题
- 修复图片批量缩放功能的拖拽支持
- 修复图片拼接工具的拖拽支持

### Refactored

- 提取拖拽功能为共用工具类，统一处理所有图片输入框 (`toolbox.py`)
- 统一标题样式使用 `TITLE_STYLES` 配置

## [v1.0.1] - 2026-04-26

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
- 根据 git tags 更新 CHANGELOG.md，采用 Keep a Changelog 标准格式

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
