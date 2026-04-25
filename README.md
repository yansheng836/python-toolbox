[TOC]

---

![ToolBox](README.assets/ToolBox.png)

# 工具箱 (ToolBox)

基于 PyQt6 的 Windows 桌面工具集，深色 UI，支持插件扩展。

初始模板来源：https://www.kimi.com/chat/19db0c86-0b22-8d2f-8000-09135f9f8673?chat_enter_method=history



## 功能

- **图片压缩** — 批量压缩 JPG/PNG/WebP，可调质量（1-100%），支持自定义输出目录和格式转换
- **图片格式转换** — 批量转换图片格式，纯转格式不压缩，支持 JPEG/PNG/WebP/BMP/TIFF/GIF 互转，自动处理透明通道
- **图片转PDF** — 多张图片合并为单个 PDF，支持调整顺序，页面大小可选（自动/A4/A3/原图），支持压缩选项：
  - **启用压缩** — 可选择是否压缩图片
  - **JPEG质量** — 1-100% 可调节，数值越小文件越小但质量越低
  - **多库支持** — 支持三种 PDF 转换库（img2pdf、PyMuPDF、PIL），自动选择可用库
  - **批量处理** — 支持大量图片转换为单个 PDF
- **图片拼接** — 多图横向/纵向合并为一张，支持顶部/居中/底部对齐及自定义背景色（RGB）
- **图片批量缩放** — 批量缩放图片，支持三种缩放模式：
  - **百分比缩放** — 按百分比（1-200%）等比缩放
  - **指定宽度** — 指定目标宽度，可选保持宽高比
  - **指定高度** — 指定目标高度，可选保持宽高比
  - **质量设置** — 支持高质量(95)/标准(85)/较小文件(75)/最小文件(50)四档
- **主题切换** — 支持深色/浅色主题切换，设置持久化保存
- **插件扩展** — 将自定义工具放入 `plugins/` 目录即可自动加载

## 安装依赖

```shell
pip install -r requirements.txt
```

依赖包：

| 包 | 用途 |
|----|------|
| PyQt6 | GUI 框架 |
| Pillow | 图片处理 |
| img2pdf | PDF 转换（首选，平衡速度和质量） |
| PyMuPDF | PDF 转换（备选，支持更多格式） |
| Pillow | 图片处理和 PDF 转换（备选） |
| pyinstaller | 打包为可执行文件 |

## 运行

```shell
python main.py
```

## 打包

```shell
# 推荐：使用 spec 文件打包（已优化，包含所有必要模块）
pyinstaller toolbox.spec

# 不推荐：快速单文件打包（可能缺少模块）
# pyinstaller --onefile --windowed main.py

# 使用 UPX 压缩（减小体积）
pyinstaller --upx-dir=/path/to/upx toolbox.spec
```

**重要提示：** 必须使用 `toolbox.spec` 进行打包，直接使用 pyinstaller 命令可能会缺少必要的模块（config.py、menu_system.py、settings_page.py 等）。

### 移除非必要的包以减少体积

在toolbox.spec中，使用excludes参数移除非必要的包。

直接执行

```shell
pyinstaller toolbox.spec
```

效果

```shell
$ ll dist/ -h
total 314M
-rwxr-xr-x 1 荷塘月色 197121  62M  4月 23 09:45  Toolbox.exe*
-rwxr-xr-x 1 荷塘月色 197121 252M  4月 23 09:26 '工具箱 - 副本.exe'*

```

## 插件开发

在 `plugins/` 目录下新建 `.py` 文件，继承 `ToolPlugin` 并实现 `create_ui()`：

```python
from toolbox import ToolPlugin, Card, AnimatedButton
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MyTool(ToolPlugin):
    name = "我的工具"
    description = "工具描述"
    icon = "🔧"

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Hello, World!"))
        return widget
    
    def update_theme(self, theme):
        """可选：响应主题切换"""
        pass
```

启动时会自动发现并加载，无需修改主程序。

### 现有插件

- `plugins/image_scaler.py` — 图片批量缩放工具，支持百分比/指定尺寸缩放

## 配置系统

应用配置集中在 `config.py` 文件中，包括：

- **应用信息**：`APP_NAME`, `APP_VERSION`, `APP_DESCRIPTION`, `APP_COPYRIGHT`
- **网站链接**：`APP_WEBSITE_URL`, `APP_WEBSITE_LINK_TEXT`
- **功能模块**：`FEATURE_MODULES` — 欢迎页显示的功能卡片
- **UI配置**：`UI_CONFIG` — 窗口大小、侧边栏宽度、圆角半径等
- **主题配置**：`THEME_CONFIG` — 默认主题、主色调等
- **欢迎页配置**：`WELCOME_CONFIG` — 欢迎页文本内容

修改 `config.py` 即可自定义应用外观和信息，无需修改主程序代码。

## 详细功能说明

### 图片转PDF - 压缩功能详解

#### 压缩选项
- **启用压缩复选框**：控制是否对图片进行压缩
- **JPEG质量滑块**：1-100% 可调节
  - 1-30%：极小文件，适合网页分享
  - 30-70%：平衡质量和大小（推荐）
  - 70-100%：高质量，最小压缩
- **压缩库自动选择**：
  - **img2pdf**：速度最快，压缩效果好，支持 JPEG 和 PNG（优先使用）
  - **PyMuPDF**：功能最全，支持更多格式，压缩适中（备选）
  - **PIL**：兼容性最好，压缩比可调范围大（备选）

#### 使用建议
1. **网页分享**：启用压缩，使用 50-70% 质量
2. **打印用途**：启用压缩，使用 85-95% 质量
3. **存档保存**：不启用压缩，保持原始质量

#### 性能优化
- 所有转换都在内存中进行，无需临时文件
- 支持实时进度显示
- 自动选择最优可用库

### 图片批量缩放 - 功能详解

#### 缩放模式
- **百分比缩放**：按原图尺寸的百分比缩放（1-200%），自动保持宽高比
- **指定宽度**：设置目标宽度，可选择是否保持宽高比
- **指定高度**：设置目标高度，可选择是否保持宽高比

#### 质量设置
- **高质量 (95)**：最佳质量，文件较大
- **标准 (85)**：平衡质量和大小（推荐）
- **较小文件 (75)**：适度压缩
- **最小文件 (50)**：最大压缩

#### 使用建议
- 缩略图生成：使用百分比缩放 25-50%，质量 75
- 网页优化：指定宽度 800-1200px，质量 85
- 打印准备：指定尺寸，质量 95

## TODO

### 图片处理
- [x] 图片格式批量转换（纯转格式，不压缩）
- [x] 图片批量缩放（指定宽高或百分比）
- [ ] 图片批量水印（文字或图片水印）
- [x] 图片拼接（多图横向/纵向合并为一张）
- [ ] 图片批量旋转/翻转
- [ ] 图片批量裁剪

### 文件处理
- [ ] PDF 拆分（拆成多张图片或单页 PDF）
- [ ] PDF 合并（多个 PDF 合并为一个）
- [ ] 文件批量重命名（支持正则、序号、日期规则）
- [ ] 文件去重（按内容 hash 查找重复文件）

### 实用工具
- [ ] 颜色取色器（屏幕取色，显示 HEX/RGB/HSL）
- [ ] 二维码生成与解析
- [ ] JSON / YAML 格式化与校验
- [ ] Base64 编解码

### UI/UX 改进
- [x] 深色/浅色主题切换
- [ ] 拖拽文件支持
- [ ] 批量操作历史记录
- [ ] 快捷键支持
