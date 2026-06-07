# UI 自适应缩放指南

## 问题

原来的代码使用固定像素大小 (`font-size: 32px;`)，导致：

- 窗口较小时图标显得过小
- 窗口较大时图标不会自动放大
- 缺乏响应式设计

## 解决方案

### 1. 使用 QSizePolicy

```python
icon_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
```

### 2. 使用 QFont 而不是样式表

```python
font = icon_label.font()
font.setPointSize(24)  # 使用点大小而非像素
font.setBold(True)
icon_label.setFont(font)
```

### 3. 设置最小尺寸

```python
icon_label.setMinimumSize(48, 48)  # 确保图标不会过小
```

### 4. 使用布局拉伸因子

```python
card_layout.setStretch(0, 2)  # 图标占据更多权重
card_layout.setStretch(1, 1)  # 文字占据较少权重
```

### 5. 保持宽高比

```python
icon_label.setScaledContents(False)  # 防止图标拉伸失真
```

## 测试方法

运行以下测试文件验证自适应效果：

```bash
python test_icon_scaling.py
```

该测试工具会创建不同大小的容器，展示图标如何自适应缩放。

## 最佳实践

1. **优先使用 QFont**：比样式表更可控，特别是在缩放时
2. **设置合理的最小尺寸**：确保在小屏幕上仍然可见
3. **使用布局拉伸因子**：控制元素在容器中的占比
4. **避免固定像素值**：使用相对单位或字体大小
5. **测试不同屏幕尺寸**：确保在各种分辨率下都显示良好

## 注意事项

- Qt 的字体缩放是基于屏幕 DPI 的
- 过大的字体在某些小容器中可能仍然受限
- 复杂布局可能需要额外的布局策略调整
