[TOC]

---

# ToolBox

工具箱应用。

用Python写一个Windows桌面应用-工具箱，需要有漂亮的UI，可以扩展。支持图片压缩，一组图片转PDF等功能。

https://www.kimi.com/chat/19db0c86-0b22-8d2f-8000-09135f9f8673?chat_enter_method=history

## 打包

使用pyinstaller.bat，能正常打包，但是程序有问题，运行不了。

```shell
# ========== Windows ==========
# 单文件 EXE
pyinstaller --onefile --windowed toolbox.py

# 完整配置（推荐）
pyinstaller toolbox.spec

# 使用 UPX 压缩（减小体积）
pyinstaller --upx-dir=/path/to/upx toolbox.spec


# ========== macOS ==========
# 生成 .app Bundle
pyinstaller --windowed --onefile --osx-bundle-identifier com.company.toolbox toolbox.py

# 签名（可选，避免安全警告）
codesign --deep --force --verify --verbose --sign "Developer ID" dist/Toolbox.app


# ========== Linux ==========
# 生成可执行文件
pyinstaller --onefile --windowed toolbox.py

# 创建 .deb/.rpm 需要使用其他工具（如 fpm）
```

