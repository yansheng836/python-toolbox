# 打包检查清单

## 打包前检查

### 1. 必要文件检查

- [x] main.py - 应用入口点
- [x] toolbox.py - 主应用类
- [x] config.py - 配置文件
- [x] menu_system.py - 菜单系统
- [x] settings_page.py - 设置页面
- [x] favicon.ico - 应用图标
- [x] plugins/ - 插件目录
  - [x] image_scaler.py - 图片缩放插件

### 2. 依赖检查

```bash
pip list | grep -E "PyQt6|Pillow|img2pdf|PyMuPDF|pyinstaller"
```

应该看到：

- PyQt6 >= 6.4.0
- Pillow >= 9.0.0
- img2pdf >= 0.4.4
- PyMuPDF >= 1.21.0
- pyinstaller >= 5.7.0

### 3. 代码检查

- [x] settings_page.py 导入了 QGraphicsDropShadowEffect 和 QColor
- [x] menu_system.py 导入了 QApplication
- [x] 所有插件都能正常导入 toolbox 模块

### 4. toolbox.spec 配置检查

- [x] 入口点设置为 main.py
- [x] datas 包含所有必要文件：
  - config.py
  - toolbox.py
  - menu_system.py
  - settings_page.py
  - plugins/
  - favicon.ico
- [x] hiddenimports 包含所有项目模块
- [x] excludes 排除了不需要的模块

## 打包命令

```bash
# 清理旧的构建文件
rm -rf build/ dist/

# 使用 spec 文件打包
pyinstaller toolbox.spec

# 检查生成的文件
ls -lh dist/
```

## 打包后测试

### 1. 基本功能测试

- [ ] 应用能正常启动
- [ ] 欢迎页面显示正常
- [ ] 侧边栏导航正常

### 2. 工具功能测试

- [ ] 图片压缩功能正常
- [ ] 图片格式转换功能正常
- [ ] 图片转PDF功能正常
- [ ] 图片拼接功能正常
- [ ] 图片批量缩放功能正常

### 3. 设置功能测试

- [ ] 设置页面能打开
- [ ] 主题切换功能正常
- [ ] 关于信息显示正常

### 4. 插件系统测试

- [ ] 插件能正常加载
- [ ] 插件功能正常工作

## 常见问题

### 问题1：缺少模块错误

**症状：** 运行时提示 "No module named 'xxx'"
**原因：**

- 模块被错误地添加到 excludes 列表
- 模块没有被 PyInstaller 自动检测到
**解决：**

1. 如果是标准库模块（如 zipfile、inspect），从 excludes 中移除
2. 如果是项目模块，添加到 hiddenimports
3. 参考 PYINSTALLER_EXCLUDES.md 了解哪些模块不能排除

### 问题2：图标不显示

**症状：** 窗口图标或系统托盘图标不显示
**解决：** 确认 favicon.ico 在 datas 中，且路径正确

### 问题3：插件加载失败

**症状：** 插件功能缺失
**解决：** 确认 plugins/ 目录在 datas 中

### 问题4：配置信息错误

**症状：** 应用名称、版本等信息显示为默认值
**解决：** 确认 config.py 在 datas 中

## 文件大小优化

当前配置预期文件大小：60-80MB

如果需要进一步优化：

1. 检查是否有不需要的 DLL 被打包
2. 使用 UPX 压缩（已在 spec 中启用）
3. 考虑使用 7-Zip 压缩最终的 exe 文件

## 版本发布

1. 更新 config.py 中的版本号
2. 更新 CHANGELOG.md
3. 运行完整测试
4. 打包
5. 测试打包后的程序
6. 创建 GitHub Release
7. 上传可执行文件
