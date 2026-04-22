[TOC]

---

# 工具箱 (ToolBox)

基于 PyQt6 的 Windows 桌面工具集，深色 UI，支持插件扩展。

初始模板来源：https://www.kimi.com/chat/19db0c86-0b22-8d2f-8000-09135f9f8673?chat_enter_method=history

## 功能

- **图片压缩** — 批量压缩 JPG/PNG/WebP，可调质量（1-100%），支持自定义输出目录和格式转换
- **图片转PDF** — 多张图片合并为单个 PDF，支持调整顺序，页面大小可选（自动/A4/A3/原图）
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
| img2pdf | PDF 转换（首选） |
| PyMuPDF | PDF 转换（备选） |
| pyinstaller | 打包为可执行文件 |

## 运行

```shell
python toolbox.py
```

## 打包

```shell
# 推荐：使用 spec 文件打包
pyinstaller toolbox.spec

# 快速单文件打包
pyinstaller --onefile --windowed toolbox.py

# 使用 UPX 压缩（减小体积）
pyinstaller --upx-dir=/path/to/upx toolbox.spec
```

## 插件开发

在 `plugins/` 目录下新建 `.py` 文件，继承 `ToolPlugin` 并实现 `create_ui()`：

```python
from toolbox import ToolPlugin
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
```

启动时会自动发现并加载，无需修改主程序。

## TODO

### 图片处理
- [ ] 图片格式批量转换（纯转格式，不压缩）
- [ ] 图片批量缩放（指定宽高或百分比）
- [ ] 图片批量水印（文字或图片水印）
- [ ] 图片拼接（多图横向/纵向合并为一张）

### 文件处理
- [ ] PDF 拆分（拆成多张图片或单页 PDF）
- [ ] 文件批量重命名（支持正则、序号、日期规则）
- [ ] 文件去重（按内容 hash 查找重复文件）

### 实用工具
- [ ] 颜色取色器（屏幕取色，显示 HEX/RGB/HSL）
- [ ] 二维码生成与解析
- [ ] JSON / YAML 格式化与校验
- [ ] Base64 编解码
