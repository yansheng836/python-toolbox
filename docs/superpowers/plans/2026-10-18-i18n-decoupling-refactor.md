# i18n 解耦重构（P0.5）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把插件名/下拉项/列名/去重文件路径从"显示文本"解耦为"稳定值"，为后续 i18n 翻译显示文本扫除障碍——翻译后业务逻辑不受影响。

**Architecture:** 在 `config.PLUGIN_MODULES` 为每个插件增加稳定 `id`；`ToolboxWindow` 改用 `id` 作为插件字典键和导航匹配依据；下拉框改用 `addItem(显示文本, 稳定值)` + `currentData()`，worker 接收稳定值而非显示文本；表格列引入 `Column(id, label, func)` 命名元组，列宽按 `id` 配置；去重子节点文件路径存入 `Qt.ItemDataRole.UserRole`，不再从显示文本反解析。本计划只做"解耦"，不引入 i18n 翻译文件（那是后续 P1+ 计划）。

**Tech Stack:** PyQt6, Python 3.12, pytest + pytest-qt（`qapp` / `loaded_plugins` fixture 见 `test/conftest.py`）。

## Global Constraints

- 所有 Python 文件 UTF-8 + LF，首行 `# -*- encoding: utf-8 -*-`，次行起模块 docstring（见 CLAUDE.md）。
- 改动任意 Python 文件后必须 `python -m py_compile <file>` + `python -m pyflakes <file>` 通过（CLAUDE.md Rule 1）。
- 颜色一律用 `Theme.*`，不得硬编码（Rule 3）——本计划不涉及颜色，保持现状即可。
- 仅捕获有意义的异常并报告，不要为项目内部 import 加 try-catch（Rule 5）。
- 模块可用性标志 `PIL_AVAILABLE` 等从 `common.utils` 导入，不重复声明（Rule 6）。
- 提交信息末尾追加 `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`。
- 测试统一在项目根目录运行：`cd test && python -m pytest <test_file> -v`。
- 现有测试 `test/test_plugins.py` 迭代 `loaded_plugins.values()` 取 `p.name`，不依赖字典键为中文，故把字典键改为 `id` 后该测试仍通过；不要修改这些既有断言。

## 文件结构

| 文件 | 角色 | 本计划改动 |
|---|---|---|
| `config.py` | 全局配置单一数据源 | 为 9 个 `PLUGIN_MODULES` 项加 `id` |
| `toolbox.py` | 主窗口/`ToolPlugin`/`SidebarButton` | `load_plugins` 设 `id`；`register_plugin`/`switch_plugin`/`show_settings` 改用 `id`；`SidebarButton` 存 `id` |
| `common/utils.py` | 共享工具函数/列定义 | 新增 `Column` 命名元组；`IMAGE_COLUMNS`/`PDF_COLUMNS` 改用 `Column` |
| `common/file_list_panel.py` | 通用文件列表 | 列宽按 `id` 配置；接受 `Column` 与兼容旧 `(label, func)` 元组 |
| `plugins/image_compressor.py` | 图片压缩 | `format_combo` 用 `addItem(display, data)`；worker 接收稳定 `format_code` |
| `plugins/image_scaler.py` | 图片缩放 | `scale_type_combo`/`quality_combo` 用 `currentData()`；worker 接收稳定 `scale_type` |
| `plugins/image_to_pdf.py` | 图片转 PDF | `size_combo` 用 `addItem(display, data)`；`start_conversion` 传 `currentData()` |
| `plugins/image_format_converter.py` | 格式转换 | `fmt_combo` 用 `addItem(display, data)`；`start_convert` 传 `currentData()` |
| `plugins/image_stitcher.py` | 图片拼接 | `columns=` 用 `Column` 代替裸元组 |
| `plugins/file_deduplicator.py` | 文件去重 | 子节点文件路径存 `UserRole`，`_sort_by_rule` 用 `UserRole` 建 `child_map` |
| `test/test_plugin_ids.py` | 新增 | 断言 `id` 唯一/含 settings |
| `test/test_decouple_combos.py` | 新增 | 断言各下拉 `currentData()` 返回稳定值 |
| `test/test_columns.py` | 新增 | 断言列 `id` 唯一且匹配默认列宽键 |
| `test/test_dedup_userrole.py` | 新增 | 断言去重子节点存 `UserRole` 路径 |

---

### Task 1: 为 PLUGIN_MODULES 增加稳定 id

**Files:**
- Modify: `config.py:20-102`
- Test: `test/test_plugin_ids.py`（新建）

**Interfaces:**
- Produces: `PLUGIN_MODULES` 每项新增 `"id"` 字段（字符串，snake_case，唯一）；设置项 `id == "settings"`。

- [ ] **Step 1: 写失败测试**

`test/test_plugin_ids.py`:

```python
# -*- encoding: utf-8 -*-
"""PLUGIN_MODULES 稳定 id 校验"""

import re
from config import PLUGIN_MODULES


def test_each_plugin_has_id():
    for p in PLUGIN_MODULES:
        assert "id" in p, f"插件 {p.get('name')} 缺少 id 字段"


def test_ids_unique():
    ids = [p["id"] for p in PLUGIN_MODULES]
    assert len(ids) == len(set(ids)), f"id 重复: {ids}"


def test_ids_snake_case():
    pat = re.compile(r"^[a-z][a-z0-9_]*$")
    for p in PLUGIN_MODULES:
        assert pat.match(p["id"]), f"id 不符合 snake_case: {p['id']}"


def test_settings_id_present():
    settings = [p for p in PLUGIN_MODULES if p["class"] == "SettingsPlugin"]
    assert settings and settings[0]["id"] == "settings"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd test && python -m pytest test_plugin_ids.py -v`
Expected: 4 个测试 FAIL（`KeyError: 'id'` / 断言失败）。

- [ ] **Step 3: 实现——为 9 项加 id**

编辑 `config.py`，给 `PLUGIN_MODULES` 每项加 `"id"` 字段（放在 `"name"` 之后）。完整新结构示例（只列首尾两项，其余同样加 `id`）：

```python
    {
        "id": "image_compressor",
        "name": "图片压缩",
        "icon": "🗜️",
        "description": "批量压缩JPG/PNG/WebP图片，可调整质量以减小文件体积",
        "order": 5,
        "module": "plugins.image_compressor",
        "class": "ImageCompressor",
    },
```

9 个 id 依次为：`image_compressor`、`image_format_converter`、`image_stitcher`、`image_to_pdf`、`image_scaler`、`pdf_merger`、`pdf_splitter`、`file_deduplicator`、`empty_folder_cleaner`、`settings`（注意共 10 项：8 插件 + 空文件夹清理 + 设置；按文件实际项数补齐，每项一个唯一 id）。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd test && python -m pytest test_plugin_ids.py -v`
Expected: 4 PASS。

- [ ] **Step 5: 语法/导入检查**

Run: `python -m py_compile config.py && python -m pyflakes config.py`
Expected: 无输出。

- [ ] **Step 6: 提交**

```bash
git add config.py test/test_plugin_ids.py
git commit -m "$(cat <<'EOF'
refactor: 为 PLUGIN_MODULES 增加稳定 id

解耦插件显示名与业务标识，为 i18n 翻译插件名扫除障碍。
设置项 id 固定为 "settings"，其余插件用 snake_case id。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: ToolboxWindow 改用 id 作为插件字典键与导航匹配

**Files:**
- Modify: `toolbox.py:201-206`（`SidebarButton.__init__`）、`toolbox.py:1004-1036`（`register_plugin`）、`toolbox.py:1038-1063`（`load_plugins`）、`toolbox.py:1088-1103`（`switch_plugin`）、`toolbox.py:1491-1492`（`show_settings`）
- Test: `test/test_plugin_nav_by_id.py`（新建）

**Interfaces:**
- Consumes: `PLUGIN_MODULES[*]["id"]`（Task 1 产出）。
- Produces: `ToolPlugin.id` 类属性；`self.plugins` 字典键改为 `id`；`switch_plugin(plugin_id)`；`SidebarButton.plugin_id()`；`show_settings()` 调 `switch_plugin("settings")`。

- [ ] **Step 1: 写失败测试**

`test/test_plugin_nav_by_id.py`:

```python
# -*- encoding: utf-8 -*-
"""插件字典键与导航按 id 匹配"""

from toolbox import ToolboxWindow, SidebarButton


def test_plugins_dict_keyed_by_id(loaded_plugins):
    # 设置项可通过 id 取到
    assert "settings" in loaded_plugins
    assert loaded_plugins["settings"].name == "设置"


def test_all_plugins_have_id(loaded_plugins):
    for pid, plugin in loaded_plugins.items():
        assert hasattr(plugin, "id")
        assert plugin.id == pid


def test_switch_plugin_by_id(qapp):
    win = ToolboxWindow()
    win.load_plugins()
    win.switch_plugin("settings")
    assert win.current_plugin == "settings"


def test_sidebar_button_stores_plugin_id(qapp):
    btn = SidebarButton("image_compressor", "图片压缩", "🗜️")
    assert btn.plugin_id() == "image_compressor"
    # 显示文本仍包含中文名（翻译在后续计划处理）
    assert "图片压缩" in btn.text()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd test && python -m pytest test_plugin_nav_by_id.py -v`
Expected: FAIL（`KeyError: 'settings'` / `SidebarButton` 参数不匹配 / `current_plugin` 不等于 `"settings"`）。

- [ ] **Step 3: 实现——SidebarButton 存 id**

`toolbox.py:201` 区域，把 `SidebarButton.__init__` 改为接收 `plugin_id`：

```python
class SidebarButton(QPushButton):
    """侧边栏导航按钮"""

    def __init__(self, plugin_id, text, icon_text, parent=None):
        super().__init__(parent)
        self._plugin_id = plugin_id
        self.setText(f"  {icon_text}  {text}")
        self.setMinimumHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        # ……以下原有 stylesheet 不变
```

在 `setText` 下方、`setStyleSheet` 之前补一个方法：

```python
    def plugin_id(self):
        """返回该按钮绑定的插件稳定 id"""
        return self._plugin_id
```

- [ ] **Step 4: 实现——register_plugin / load_plugins / switch_plugin / show_settings**

`toolbox.py:1004` 区域 `register_plugin`：

```python
    def register_plugin(self, plugin_class):
        try:
            plugin = plugin_class(self)
            self.plugins[plugin.id] = plugin

            btn = SidebarButton(plugin.id, plugin.name, plugin.icon)
            from functools import partial
            btn.clicked.connect(partial(self.switch_plugin, plugin.id))
            self.nav_layout.addWidget(btn)
            # ……（widget / scroll_area 部分保持不变）
        except Exception as e:
            print(f"注册插件失败 {getattr(plugin_class, 'id', '?')}: {e}")
```

`toolbox.py:1038` 区域 `load_plugins`，在设置 `name/icon/order/description` 后加一行：

```python
                plugin_class.id = plugin_config["id"]
                plugin_class.name = plugin_config["name"]
                plugin_class.icon = plugin_config["icon"]
                plugin_class.order = plugin_config["order"]
                if "description" in plugin_config:
                    plugin_class.description = plugin_config["description"]
```

`toolbox.py:1088` 区域 `switch_plugin`，参数改名为 `plugin_id`，匹配逻辑改用 `plugin_id()`：

```python
    def switch_plugin(self, plugin_id):
        for i in range(self.nav_layout.count()):
            widget = self.nav_layout.itemAt(i).widget()
            if isinstance(widget, SidebarButton):
                widget.setChecked(widget.plugin_id() == plugin_id)

        self.home_btn.setChecked(False)

        if plugin_id in self.plugins:
            plugin = self.plugins[plugin_id]
            if hasattr(plugin, 'scroll_area'):
                index = self.content.indexOf(plugin.scroll_area)
                if index >= 0:
                    self.content.setCurrentIndex(index)
                    self.current_plugin = plugin_id
```

`toolbox.py:1491` 区域 `show_settings`：

```python
    def show_settings(self):
        self.switch_plugin("settings")
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd test && python -m pytest test_plugin_nav_by_id.py -v`
Expected: 4 PASS。

- [ ] **Step 6: 回归既有插件测试**

Run: `cd test && python -m pytest test_plugins.py -v`
Expected: 全 PASS（这些测试迭代 `.values()` 取 `p.name`，不依赖字典键）。

- [ ] **Step 7: 语法/导入检查**

Run: `python -m py_compile toolbox.py && python -m pyflakes toolbox.py`
Expected: 无输出。

- [ ] **Step 8: 提交**

```bash
git add toolbox.py test/test_plugin_nav_by_id.py
git commit -m "$(cat <<'EOF'
refactor: 插件字典键与导航改用稳定 id

ToolboxWindow.plugins 以 id 为键，switch_plugin/show_settings 按 id
匹配，SidebarButton 保存 plugin_id。翻译插件显示名后导航不再失效。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: 图片压缩——下拉项用 currentData() 传稳定 format_code

**Files:**
- Modify: `plugins/image_compressor.py:202-204`（combo 构造）、`plugins/image_compressor.py:266-271`（传参）、`plugins/image_compressor.py:60-84`（worker `format_map`/分支）
- Test: `test/test_decouple_combos.py`（新建，本任务起追加用例）

**Interfaces:**
- Produces: `CompressionWorker.__init__(files, output_dir, format_code, quality)`，`format_code` 取值 `"keep"|"JPG"|"JPEG"|"PNG"|"WebP"`；UI 用 `addItem(显示文本, format_code)` + `currentData()`。

- [ ] **Step 1: 写失败测试**

追加到 `test/test_decouple_combos.py`（首次创建该文件）：

```python
# -*- encoding: utf-8 -*-
"""下拉项解耦：currentData() 返回稳定值"""

import pytest

from plugins.image_compressor import ImageCompressor, CompressionWorker


@pytest.fixture
def compressor_widget(qapp):
    from toolbox import Theme
    plugin = ImageCompressor.__new__(ImageCompressor)
    plugin.icon = "🗜️"
    plugin.name = "图片压缩"
    plugin.description = ""
    from PyQt6.QtWidgets import QWidget
    plugin.widget = None
    plugin.theme = Theme.DARK
    w = plugin.create_ui()
    return plugin, w


def test_compressor_format_combo_has_stable_data(compressor_widget):
    plugin, _ = compressor_widget
    combo = plugin.format_combo
    # 每项都有 data
    for i in range(combo.count()):
        assert combo.itemData(i) is not None
    # "保持原格式" 对应稳定值 "keep"
    idx = combo.findData("keep")
    assert idx >= 0
    assert combo.itemText(idx) == "保持原格式"


def test_compressor_worker_receives_keep_code(compressor_widget):
    plugin, _ = compressor_widget
    plugin.format_combo.setCurrentIndex(plugin.format_combo.findData("keep"))
    # 直接断言传给 worker 的 format_code（不启动线程）
    code = plugin.format_combo.currentData()
    assert code == "keep"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd test && python -m pytest test_decouple_combos.py -v`
Expected: FAIL（`itemData is None` / `findData` 返回 -1）。

- [ ] **Step 3: 实现——combo 用 addItem(display, data)**

`plugins/image_compressor.py:202` 区域：

```python
        self.format_combo = QComboBox()
        self.format_combo.addItem("保持原格式", "keep")
        self.format_combo.addItem("JPG", "JPG")
        self.format_combo.addItem("JPEG", "JPEG")
        self.format_combo.addItem("PNG", "PNG")
        self.format_combo.addItem("WebP", "WebP")
        self.format_combo.setStyleSheet(get_combo_style(self.theme))
```

- [ ] **Step 4: 实现——start_compression 传 currentData()**

`plugins/image_compressor.py:266` 区域，把 `self.format_combo.currentText()` 改为 `self.format_combo.currentData()`：

```python
        self.worker = CompressionWorker(
            files,
            self.output_path.text() or None,
            self.format_combo.currentData(),
            self.quality_slider.value()
        )
```

- [ ] **Step 5: 实现——worker 用稳定 format_code**

`plugins/image_compressor.py:60` 区域，把 `if self.format_str == "保持原格式":` 改为比较 `"keep"`，并修正日志/变量名为 `format_code`：

```python
                # 确定输出格式及扩展名
                # Pillow 格式映射（JPG/JPEG 底层都是 JPEG）
                format_map = {'JPG': 'JPEG', 'JPEG': 'JPEG', 'PNG': 'PNG', 'WebP': 'WEBP'}
                out_ext_map = {'JPG': 'jpg', 'JPEG': 'jpeg', 'PNG': 'png',
                               'WebP': 'webp'}

                if self.format_code == "keep":
                    # 保留原扩展名（区分 jpg/jpeg）
                    orig_ext = os.path.splitext(file_path)[1].lstrip('.')
                    if orig_ext.lower() in ('jpg', 'jpeg'):
                        fmt = 'JPEG'
                        output_ext = orig_ext
                    elif orig_ext.lower() == 'png':
                        fmt = 'PNG'
                        output_ext = orig_ext
                    elif orig_ext.lower() == 'webp':
                        fmt = 'WEBP'
                        output_ext = orig_ext
                    else:
                        fmt = img.format if img.format else 'JPEG'
                        output_ext = fmt.lower()
                else:
                    fmt = format_map[self.format_code]
                    output_ext = out_ext_map[self.format_code]
```

同时把 `CompressionWorker.__init__` 的参数名从 `format_str` 改为 `format_code`，并赋值 `self.format_code = format_code`（`plugins/image_compressor.py:36-41`）。

- [ ] **Step 6: 运行测试确认通过**

Run: `cd test && python -m pytest test_decouple_combos.py -v`
Expected: 2 PASS。

- [ ] **Step 7: 语法/导入检查**

Run: `python -m py_compile plugins/image_compressor.py && python -m pyflakes plugins/image_compressor.py`
Expected: 无输出。

- [ ] **Step 8: 提交**

```bash
git add plugins/image_compressor.py test/test_decouple_combos.py
git commit -m "$(cat <<'EOF'
refactor: 图片压缩下拉项用稳定 format_code

combo 改为 addItem(显示, data)，worker 接收 keep/JPG/JPEG/PNG/WebP
稳定值，翻译下拉显示文本后压缩逻辑不受影响。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: 图片缩放——scale_type 与 quality 用 currentData()

**Files:**
- Modify: `plugins/image_scaler.py:185-189`（`scale_type_combo`）、`plugins/image_scaler.py:261-265`（`quality_combo`）、`plugins/image_scaler.py:300-337`（`on_scale_type_changed`）、`plugins/image_scaler.py:346-364`（`start_scaling`）、`plugins/image_scaler.py:73-89`（worker `run` 分支）
- Test: `test/test_decouple_combos.py`（追加用例）

**Interfaces:**
- Produces: `scale_type_combo` data = `"percent"|"width"|"height"`；`quality_combo` data = `int`（95/85/75/50）；`ScalingWorker.scale_type` 接收稳定值；`start_scaling` 传 `currentData()`。

- [ ] **Step 1: 写失败测试**

追加到 `test/test_decouple_combos.py`：

```python
from plugins.image_scaler import ImageScaler


@pytest.fixture
def scaler_widget(qapp):
    from toolbox import Theme
    plugin = ImageScaler.__new__(ImageScaler)
    plugin.icon = "🔍"
    plugin.name = "图片缩放"
    plugin.description = ""
    plugin.theme = Theme.DARK
    w = plugin.create_ui()
    # create_ui 返回 ImageScalerWidget，其控件引用已复制到 plugin
    return plugin, w


def test_scaler_scale_type_combo_data(scaler_widget):
    plugin, _ = scaler_widget
    combo = plugin.scale_type_combo
    assert combo.findData("percent") >= 0
    assert combo.findData("width") >= 0
    assert combo.findData("height") >= 0


def test_scaler_quality_combo_data_is_int(scaler_widget):
    plugin, _ = scaler_widget
    combo = plugin.quality_combo
    for i in range(combo.count()):
        assert isinstance(combo.itemData(i), int)
    assert combo.findData(85) >= 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd test && python -m pytest test_decouple_combos.py::test_scaler_scale_type_combo_data test_decouple_combos.py::test_scaler_quality_combo_data_is_int -v`
Expected: FAIL（`findData` 返回 -1）。

- [ ] **Step 3: 实现——combo 构造**

`plugins/image_scaler.py:185` 区域：

```python
        self.scale_type_combo = QComboBox()
        self.scale_type_combo.addItem("百分比缩放", "percent")
        self.scale_type_combo.addItem("指定宽度", "width")
        self.scale_type_combo.addItem("指定高度", "height")
        self.scale_type_combo.setStyleSheet(combo_style)
        self.scale_type_combo.currentIndexChanged.connect(self.on_scale_type_changed)
```

注意把信号从 `currentTextChanged` 改为 `currentIndexChanged`（因为 text 会被翻译，index/data 稳定）。

`plugins/image_scaler.py:261` 区域 `quality_combo`：

```python
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("高质量 (95)", 95)
        self.quality_combo.addItem("标准 (85)", 85)
        self.quality_combo.addItem("较小文件 (75)", 75)
        self.quality_combo.addItem("最小文件 (50)", 50)
        self.quality_combo.setCurrentIndex(1)
        self.quality_combo.setStyleSheet(combo_style)
```

- [ ] **Step 4: 实现——on_scale_type_changed 用 currentData()**

`plugins/image_scaler.py:300` 区域：

```python
    def on_scale_type_changed(self):
        scale_type = self.scale_type_combo.currentData()

        if scale_type == "percent":
            self.zoom_row_widget.setVisible(True)
            self.width_row_widget.setVisible(False)
            self.height_row_widget.setVisible(False)
            self.aspect_row_widget.setVisible(False)
        elif scale_type == "width":
            self.zoom_row_widget.setVisible(False)
            self.width_row_widget.setVisible(True)
            self.height_row_widget.setVisible(True)
            self.aspect_row_widget.setVisible(True)
            self.width_input.setEnabled(True)
            self.width_input.setSuffix(" px")
            if self.maintain_aspect.isChecked():
                self.height_input.setEnabled(False)
                self.height_input.setSuffix(" (自动)")
            else:
                self.height_input.setEnabled(True)
                self.height_input.setSuffix(" px")
        elif scale_type == "height":
            self.zoom_row_widget.setVisible(False)
            self.width_row_widget.setVisible(True)
            self.height_row_widget.setVisible(True)
            self.aspect_row_widget.setVisible(True)
            self.height_input.setEnabled(True)
            self.height_input.setSuffix(" px")
            if self.maintain_aspect.isChecked():
                self.width_input.setEnabled(False)
                self.width_input.setSuffix(" (自动)")
            else:
                self.width_input.setEnabled(True)
                self.width_input.setSuffix(" px")
```

- [ ] **Step 5: 实现——start_scaling 传 currentData()**

`plugins/image_scaler.py:346` 区域：

```python
    def start_scaling(self):
        files = self.file_panel.get_files()
        if not files:
            show_warning(self, "警告", "请先添加图片！")
            return

        scale_type = self.scale_type_combo.currentData()
        quality = self.quality_combo.currentData()

        self.worker = ScalingWorker(
            input_files=files,
            output_dir=self.output_path.text(),
            scale_type=scale_type,
            scale_value=self.scale_value_input.value() if scale_type == "percent" else 100,
            quality=quality,
            maintain_aspect=self.maintain_aspect.isChecked(),
            width=self.width_input.value() if scale_type in ("width", "height") else None,
            height=self.height_input.value() if scale_type in ("width", "height") else None
        )
```

- [ ] **Step 6: 实现——worker run 分支用稳定值**

`plugins/image_scaler.py:73` 区域：

```python
                        if self.scale_type == "percent":
                            new_width = int(img.width * self.scale_value / 100)
                            new_height = int(img.height * self.scale_value / 100)
                        elif self.scale_type == "width":
                            new_width = self.width
                            if self.maintain_aspect:
                                new_height = int(img.height * new_width / img.width)
                            else:
                                new_height = self.height
                        elif self.scale_type == "height":
                            new_height = self.height
                            if self.maintain_aspect:
                                new_width = int(img.width * new_height / img.height)
                            else:
                                new_width = self.width
                        else:
                            raise ValueError(f"未知缩放类型: {self.scale_type}")
```

- [ ] **Step 7: 运行测试确认通过**

Run: `cd test && python -m pytest test_decouple_combos.py -v`
Expected: 全 PASS。

- [ ] **Step 8: 语法/导入检查**

Run: `python -m py_compile plugins/image_scaler.py && python -m pyflakes plugins/image_scaler.py`
Expected: 无输出。

- [ ] **Step 9: 提交**

```bash
git add plugins/image_scaler.py test/test_decouple_combos.py
git commit -m "$(cat <<'EOF'
refactor: 图片缩放下拉项用稳定 scale_type 与 quality

scale_type_combo data 为 percent/width/height，quality_combo data 为
整数质量值，worker 按稳定值分支，不再解析中文显示文本。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: 图片转 PDF——size_combo 用 currentData()

**Files:**
- Modify: `plugins/image_to_pdf.py:381-384`（`size_combo` 构造）、`plugins/image_to_pdf.py:469-475`（`start_conversion` 传参）、`plugins/image_to_pdf.py:88-96`（`_prepare_image` 比较）、`plugins/image_to_pdf.py:122-123`（`run` 中 `智能缩放` 比较）
- Test: `test/test_decouple_combos.py`（追加用例）

**Interfaces:**
- Produces: `size_combo` data = `"auto"|"A4"|"A3"|"original"|"smart"`；`PDFWorker.page_size` 接收稳定值；`PAGE_SIZES` 字典键 `A4/A3` 已是稳定值，无需改。

- [ ] **Step 1: 写失败测试**

追加到 `test/test_decouple_combos.py`：

```python
from plugins.image_to_pdf import ImageToPDF


@pytest.fixture
def pdf_widget(qapp):
    from toolbox import Theme
    plugin = ImageToPDF.__new__(ImageToPDF)
    plugin.icon = "🖨️"
    plugin.name = "图片转PDF"
    plugin.description = ""
    plugin.widget = None
    plugin.theme = Theme.DARK
    w = plugin.create_ui()
    return plugin, w


def test_pdf_size_combo_data(pdf_widget):
    plugin, _ = pdf_widget
    combo = plugin.size_combo
    assert combo.findData("smart") >= 0
    assert combo.findData("auto") >= 0
    assert combo.findData("A4") >= 0
    assert combo.findData("A3") >= 0
    assert combo.findData("original") >= 0


def test_pdf_default_smart(pdf_widget):
    plugin, _ = pdf_widget
    assert plugin.size_combo.currentData() == "smart"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd test && python -m pytest test_decouple_combos.py::test_pdf_size_combo_data test_decouple_combos.py::test_pdf_default_smart -v`
Expected: FAIL。

- [ ] **Step 3: 实现——size_combo 构造**

`plugins/image_to_pdf.py:381` 区域：

```python
        self.size_combo = QComboBox()
        self.size_combo.addItem("自动适应", "auto")
        self.size_combo.addItem("A4", "A4")
        self.size_combo.addItem("A3", "A3")
        self.size_combo.addItem("原图尺寸", "original")
        self.size_combo.addItem("智能缩放", "smart")
        # 默认 smart 在索引 4
        self.size_combo.setCurrentIndex(self.size_combo.findData("smart"))
        self.size_combo.setStyleSheet(get_combo_style(self.theme))
```

- [ ] **Step 4: 实现——start_conversion 传 currentData()**

`plugins/image_to_pdf.py:469` 区域：

```python
        self.worker = PDFWorker(
            files,
            output,
            self.size_combo.currentData(),
            self.compress_check.isChecked(),
            self.quality_slider.value()
        )
```

- [ ] **Step 5: 实现——worker 用稳定值比较**

`plugins/image_to_pdf.py:88` `_prepare_image`：

```python
        if self.page_size == "smart" and max_width is not None and img.width != max_width:
```

`plugins/image_to_pdf.py:122` `run`：

```python
            if self.page_size == "smart":
                self.status.emit("正在扫描图片尺寸...")
```

`PAGE_SIZES` 字典键 `A4/A3` 与稳定值一致，`self.page_size in self.PAGE_SIZES` 判断无需改。

- [ ] **Step 6: 运行测试确认通过**

Run: `cd test && python -m pytest test_decouple_combos.py -v`
Expected: 全 PASS。

- [ ] **Step 7: 语法/导入检查**

Run: `python -m py_compile plugins/image_to_pdf.py && python -m pyflakes plugins/image_to_pdf.py`
Expected: 无输出。

- [ ] **Step 8: 回归 image_to_pdf 既有测试**

Run: `cd test && python -m pytest test_image_to_pdf.py -v`
Expected: 全 PASS（页面尺寸逻辑用稳定值后行为一致）。

- [ ] **Step 9: 提交**

```bash
git add plugins/image_to_pdf.py test/test_decouple_combos.py
git commit -m "$(cat <<'EOF'
refactor: 图片转 PDF 页面大小下拉用稳定 data

size_combo data 为 auto/A4/A3/original/smart，worker 按稳定值判断
智能缩放与固定页面，翻译下拉显示文本后转换逻辑不受影响。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: 图片格式转换——fmt_combo 用 currentData()

**Files:**
- Modify: `plugins/image_format_converter.py:122`（`FORMATS`）、`plugins/image_format_converter.py:188-190`（`fmt_combo` 构造）、`plugins/image_format_converter.py:232-236`（`start_convert` 传参）
- Test: `test/test_decouple_combos.py`（追加用例）

**Interfaces:**
- Produces: `fmt_combo` 每项 `data == 显示文本`（格式名 JPEG/PNG/WebP/BMP/TIFF/GIF 为通用专有名词，data 与显示一致；本任务保证 `start_convert` 传 `currentData()` 而非 `currentText()`，未来若翻译显示文本也不破坏）。

- [ ] **Step 1: 写失败测试**

追加到 `test/test_decouple_combos.py`：

```python
from plugins.image_format_converter import FormatConverter


@pytest.fixture
def converter_widget(qapp):
    from toolbox import Theme
    plugin = FormatConverter.__new__(FormatConverter)
    plugin.icon = "🔁"
    plugin.name = "图片格式转换"
    plugin.description = ""
    plugin.widget = None
    plugin.theme = Theme.DARK
    w = plugin.create_ui()
    return plugin, w


def test_converter_fmt_combo_data(converter_widget):
    plugin, _ = converter_widget
    combo = plugin.fmt_combo
    for fmt in ["JPEG", "PNG", "WebP", "BMP", "TIFF", "GIF"]:
        assert combo.findData(fmt) >= 0, f"缺少 data: {fmt}"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd test && python -m pytest test_decouple_combos.py::test_converter_fmt_combo_data -v`
Expected: FAIL。

- [ ] **Step 3: 实现——fmt_combo 构造**

`plugins/image_format_converter.py:188` 区域：

```python
        self.fmt_combo = QComboBox()
        for fmt in self.FORMATS:
            self.fmt_combo.addItem(fmt, fmt)
        self.fmt_combo.setStyleSheet(get_combo_style(self.theme))
```

- [ ] **Step 4: 实现——start_convert 传 currentData()**

`plugins/image_format_converter.py:232` 区域：

```python
        self.worker = FormatConvertWorker(
            files,
            self.output_path.text() or None,
            self.fmt_combo.currentData()
        )
```

`FORMAT_MAP` 键已是格式名，worker 无需改动。

- [ ] **Step 5: 运行测试确认通过**

Run: `cd test && python -m pytest test_decouple_combos.py -v`
Expected: 全 PASS。

- [ ] **Step 6: 语法/导入检查**

Run: `python -m py_compile plugins/image_format_converter.py && python -m pyflakes plugins/image_format_converter.py`
Expected: 无输出。

- [ ] **Step 7: 提交**

```bash
git add plugins/image_format_converter.py test/test_decouple_combos.py
git commit -m "$(cat <<'EOF'
refactor: 图片格式转换下拉用 currentData()

fmt_combo 每项 data 等于格式名，start_convert 传 currentData()，
与其它插件下拉解耦方式保持一致。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: 表格列引入 Column(id,label,func)，列宽按 id 配置

**Files:**
- Modify: `common/utils.py:109-121`（`IMAGE_COLUMNS`/`PDF_COLUMNS`）、`common/file_list_panel.py:27-35`（`DEFAULT_COLUMN_WIDTHS`）、`common/file_list_panel.py:37-68`（构造/列定义）、`common/file_list_panel.py:109-110`（表头）、`common/file_list_panel.py:156-198`（`_apply_column_widths`）、`plugins/image_stitcher.py:404`、`plugins/image_to_pdf.py:367`（裸元组改 `Column`）
- Test: `test/test_columns.py`（新建）

**Interfaces:**
- Produces: `common/utils.Column`（`namedtuple("Column", "id label func")`）；`IMAGE_COLUMNS`/`PDF_COLUMNS` 元素为 `Column`；`FileListPanel` 列宽按 `col.id` 配置，兼容 `Column` 与旧 `(label, func)` 元组（自动转换）。

- [ ] **Step 1: 写失败测试**

`test/test_columns.py`:

```python
# -*- encoding: utf-8 -*-
"""列定义稳定 id 与列宽键一致性"""

from common.utils import IMAGE_COLUMNS, PDF_COLUMNS, Column
from common.file_list_panel import FileListPanel


def test_columns_are_column_namedtuple():
    for col in IMAGE_COLUMNS + PDF_COLUMNS:
        assert isinstance(col, Column), f"{col} 不是 Column"
        assert col.id
        assert callable(col.func)


def test_column_ids_unique():
    ids = [c.id for c in IMAGE_COLUMNS + PDF_COLUMNS]
    assert len(ids) == len(set(ids)), f"列 id 重复: {ids}"


def test_default_widths_keyed_by_id():
    for cid, _ in FileListPanel.DEFAULT_COLUMN_WIDTHS.items():
        assert isinstance(cid, str)
        # 每个默认列宽键都能在某列定义中找到
        all_ids = [c.id for c in IMAGE_COLUMNS + PDF_COLUMNS] + [
            "filename", "size", "pages", "dimensions", "created", "modified"
        ]
        assert cid in all_ids, f"默认列宽键未对应任何列: {cid}"


def test_file_panel_accepts_legacy_tuple(qapp):
    # 旧式 (label, func) 元组仍能工作（向后兼容）
    import os
    panel = FileListPanel(columns=[("文件名", lambda f: os.path.basename(f))])
    assert panel.table.columnCount() == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd test && python -m pytest test_columns.py -v`
Expected: FAIL（`Column` 未定义 / `DEFAULT_COLUMN_WIDTHS` 键是中文）。

- [ ] **Step 3: 实现——Column 命名元组与列定义**

`common/utils.py` 在 `IMAGE_COLUMNS` 之前加：

```python
from collections import namedtuple

# 列定义：id 为稳定标识（列宽/排序按 id 匹配），label 为显示文本（i18n 时翻译），func 为取值函数
Column = namedtuple("Column", "id label func")
```

把 `IMAGE_COLUMNS`/`PDF_COLUMNS` 改为：

```python
# 图片类插件通用的表格列定义
IMAGE_COLUMNS = [
    Column("filename", "文件名", lambda f: os.path.basename(f)),
    Column("dimensions", "尺寸", get_image_size),
    Column("size", "大小", get_file_size),
]

# PDF类插件通用的表格列定义
PDF_COLUMNS = [
    Column("filename", "文件名", lambda f: os.path.basename(f)),
    Column("pages", "页数", get_pdf_pages),
    Column("size", "大小", get_file_size),
]
```

- [ ] **Step 4: 实现——FileListPanel 列宽按 id 配置**

`common/file_list_panel.py:27` 区域 `DEFAULT_COLUMN_WIDTHS`：

```python
    # 默认列宽映射：列 id -> 宽度（px），None 表示使用 Stretch
    DEFAULT_COLUMN_WIDTHS = {
        "filename": None,   # Stretch
        "size": 80,
        "pages": 50,
        "dimensions": 100,
        "created": 150,
        "modified": 150,
    }
```

`common/file_list_panel.py:60` 区域，构造时规范化列定义（兼容 Column 与旧元组）：

```python
        # 规范化列定义：接受 Column 或旧式 (label, func) / (id, label, func) 元组
        raw_cols = columns or [("filename", lambda f: os.path.basename(f))]
        self.columns = []
        for col in raw_cols:
            if isinstance(col, Column):
                self.columns.append(col)
            elif len(col) == 3:
                self.columns.append(Column(col[0], col[1], col[2]))
            else:  # (label, func) -> 推导 id
                self.columns.append(Column(col[0], col[0], col[1]))
```

`common/file_list_panel.py:109-110` 表头用 `col.label`：

```python
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels([col.label for col in self.columns])
```

`common/file_list_panel.py:156` `_apply_column_widths`，把列名映射改为按 id：

```python
    def _apply_column_widths(self, header):
        """应用列宽设置

        优先级：用户指定 > DEFAULT_COLUMN_WIDTHS > 默认（第0列Stretch，其余Interactive）
        """
        col_id_to_idx = {col.id: idx for idx, col in enumerate(self.columns)}
        col_settings = [None] * len(self.columns)

        # 1. 先应用默认值
        for col_id, default_width in self.DEFAULT_COLUMN_WIDTHS.items():
            if col_id in col_id_to_idx:
                col_settings[col_id_to_idx[col_id]] = default_width

        # 2. 再应用用户指定的设置（覆盖默认值）
        if self.column_widths is not None:
            if isinstance(self.column_widths, dict):
                # 格式: {"列 id": 宽度, ...}
                for col_id, width in self.column_widths.items():
                    if col_id in col_id_to_idx:
                        col_settings[col_id_to_idx[col_id]] = width
            else:
                # 格式: [(列索引, 宽度), ...] 或 [宽度1, 宽度2, ...]
                for item in self.column_widths:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        col_idx, width = item
                    else:
                        col_idx, width = item, item
                    if 0 <= col_idx < len(col_settings):
                        col_settings[col_idx] = width

        # 3. 应用设置到 header
        for col_idx, width in enumerate(col_settings):
            if width is None:
                header.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Fixed)
                header.resizeSection(col_idx, width)
```

`common/file_list_panel.py:316` `update_list` 中遍历列用属性访问：

```python
        for row, file_path in enumerate(self.files):
            for col_idx, col in enumerate(self.columns):
                try:
                    text = str(col.func(file_path))
                except Exception as e:
                    print(f"Error in file_list_panel: {e}")
                    text = "错误"
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col_idx, item)
```

（即把 `for col_idx, (col_name, col_func) in enumerate(self.columns):` 改为 `for col_idx, col in enumerate(self.columns):`，`col_func(file_path)` 改为 `col.func(file_path)`。）

- [ ] **Step 5: 实现——更新裸元组调用方**

`plugins/image_stitcher.py:404`：

```python
            columns=IMAGE_COLUMNS + [Column("created", "创建时间", get_create_time)],
```

`plugins/image_to_pdf.py:367`：

```python
            columns=IMAGE_COLUMNS + [Column("created", "创建时间", get_create_time)],
```

两个文件都需在顶部 import 增加 `Column`：

`plugins/image_stitcher.py` 与 `plugins/image_to_pdf.py` 的 `from common.utils import ...` 行追加 `Column`。

- [ ] **Step 6: 运行测试确认通过**

Run: `cd test && python -m pytest test_columns.py -v`
Expected: 4 PASS。

- [ ] **Step 7: 回归插件测试**

Run: `cd test && python -m pytest test_plugins.py test_decouple_combos.py -v`
Expected: 全 PASS。

- [ ] **Step 8: 语法/导入检查**

Run: `python -m py_compile common/utils.py common/file_list_panel.py plugins/image_stitcher.py plugins/image_to_pdf.py && python -m pyflakes common/utils.py common/file_list_panel.py plugins/image_stitcher.py plugins/image_to_pdf.py`
Expected: 无输出。

- [ ] **Step 9: 提交**

```bash
git add common/utils.py common/file_list_panel.py plugins/image_stitcher.py plugins/image_to_pdf.py test/test_columns.py
git commit -m "$(cat <<'EOF'
refactor: 表格列引入 Column(id,label,func)，列宽按 id 配置

列定义改为 namedtuple，列宽与排序按稳定 id 匹配，表头显示文本独立
可翻译。FileListPanel 兼容旧式 (label, func) 元组，调用方逐步迁移。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: 文件去重——子节点文件路径存 UserRole

**Files:**
- Modify: `plugins/file_deduplicator.py:521-523`（创建 `file_item` 时存 `UserRole`）、`plugins/file_deduplicator.py:645-665`（`_sort_by_rule` 用 `UserRole` 建 `child_map`）
- Test: `test/test_dedup_userrole.py`（新建）

**Interfaces:**
- Produces: 去重结果子节点 `QTreeWidgetItem` 在 `setData(0, Qt.ItemDataRole.UserRole, file_path)` 存文件路径；`_sort_by_rule` 的 `child_map` 用 `child.data(0, UserRole)` 作键，不再从 `"✅ 保留: "` / `"❌ 删除: "` 前缀反解析。显示文本仍可带前缀（前缀的翻译在后续 P3 计划处理）。

- [ ] **Step 1: 写失败测试**

`test/test_dedup_userrole.py`:

```python
# -*- encoding: utf-8 -*-
"""去重子节点文件路径存 UserRole，不依赖显示文本"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem


def test_sort_by_rule_uses_userrole(qapp, monkeypatch):
    from plugins.file_deduplicator import FileDeduplicator
    from toolbox import Theme

    plugin = FileDeduplicator.__new__(FileDeduplicator)
    plugin.icon = "🧹"
    plugin.name = "文件去重"
    plugin.description = ""
    plugin.theme = Theme.DARK
    plugin.current_theme = Theme.DARK
    plugin.create_ui()

    # 构造一个重复组：父节点带 hash，两个子节点带 UserRole 路径
    from PyQt6.QtWidgets import QTreeWidget
    plugin.duplicates = {"hash123": ["/a/x.jpg", "/a/y.jpg"]}
    tree = plugin.results_tree
    tree.clear()
    parent = QTreeWidgetItem(tree)
    parent.setData(0, Qt.ItemDataRole.UserRole, "hash123")
    c1 = QTreeWidgetItem(parent)
    c1.setText(0, "/a/x.jpg")
    c1.setData(0, Qt.ItemDataRole.UserRole, "/a/x.jpg")
    c2 = QTreeWidgetItem(parent)
    c2.setText(0, "/a/y.jpg")
    c2.setData(0, Qt.ItemDataRole.UserRole, "/a/y.jpg")

    # 默认规则 index 0：按文件名升序，保留首个
    plugin.rule_combo.setCurrentIndex(0)
    plugin._sort_by_rule()

    # 重建后子节点仍可通过 UserRole 拿到路径（不依赖显示文本前缀）
    paths = [parent.child(i).data(0, Qt.ItemDataRole.UserRole)
             for i in range(parent.childCount())]
    assert "/a/x.jpg" in paths
    assert "/a/y.jpg" in paths
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd test && python -m pytest test_dedup_userrole.py -v`
Expected: FAIL（当前 `_sort_by_rule` 用 `removeprefix` 解析显示文本，若子节点无 `UserRole` 则 `child_map` 键为 `None`，重建后路径断言失败）。

- [ ] **Step 3: 实现——创建子节点时存 UserRole**

`plugins/file_deduplicator.py:521` 区域，在 `file_item.setText(0, file_path)` 后加一行：

```python
            for file_path in file_list:
                file_item = QTreeWidgetItem(group_item)
                file_item.setText(0, file_path)
                file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
                file_item.setForeground(0, QBrush(QColor(text_color)))
```

- [ ] **Step 4: 实现——_sort_by_rule 用 UserRole 建 child_map**

`plugins/file_deduplicator.py:645` 区域：

```python
            # 收集现有子项（按 UserRole 中存的文件路径索引，不依赖显示前缀）
            child_map = {}
            for j in range(parent.childCount()):
                child = parent.child(j)
                child_map[child.data(0, Qt.ItemDataRole.UserRole)] = child
```

`649` 行原来的 `child_map[child.text(0).removeprefix(...)...] = child` 整行删除。下方 `child.setText(0, f"✅ 保留: {file_path}")` / `child.setText(0, f"❌ 删除: {file_path}")` 保持不变（显示前缀留待后续翻译）。

- [ ] **Step 5: 运行测试确认通过**

Run: `cd test && python -m pytest test_dedup_userrole.py -v`
Expected: PASS。

- [ ] **Step 6: 语法/导入检查**

Run: `python -m py_compile plugins/file_deduplicator.py && python -m pyflakes plugins/file_deduplicator.py`
Expected: 无输出。

- [ ] **Step 7: 提交**

```bash
git add plugins/file_deduplicator.py test/test_dedup_userrole.py
git commit -m "$(cat <<'EOF'
refactor: 去重子节点文件路径存 UserRole

child_map 改用 Qt.ItemDataRole.UserRole 中的文件路径作键，不再从
"✅ 保留: "/"❌ 删除: " 显示前缀反解析，翻译前缀后排序逻辑不破坏。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## 全量回归（所有任务完成后）

- [ ] **Run full test suite**

```bash
cd test && python -m pytest -v
```
Expected: 全 PASS（既有用例 + 本计划新增 4 个测试文件）。

- [ ] **Run全量语法/导入检查**

```bash
python -m py_compile config.py toolbox.py common/utils.py common/file_list_panel.py plugins/image_compressor.py plugins/image_scaler.py plugins/image_to_pdf.py plugins/image_format_converter.py plugins/image_stitcher.py plugins/file_deduplicator.py
python -m pyflakes config.py toolbox.py common/utils.py common/file_list_panel.py plugins/image_compressor.py plugins/image_scaler.py plugins/image_to_pdf.py plugins/image_format_converter.py plugins/image_stitcher.py plugins/file_deduplicator.py
```
Expected: 无输出。

- [ ] **手动冒烟（可选但建议）**

```bash
python main.py
```
验证：侧边栏点击各插件可切换；图片压缩/缩放/转PDF/格式转换下拉切换后实际转换行为不变；去重扫描后切换删除规则，"保留/删除"标记顺序仍按规则变化；设置入口（菜单 `工具→设置` 或 `Ctrl+S`）仍能跳转设置页。

## Self-Review

**1. Spec coverage**（对照 `docs/2026-10-17-多语言国际化方案分析.md` §6.4 必须先完成的重构表）：
- ✅ 插件 `id` + `self.plugins[id]` + `switch_plugin(id)` + `show_settings()` 用 `"settings"` → Task 1 + Task 2。
- ✅ 下拉框 `addItem(显示, 稳定值)` + `currentData()` → Task 3/4/5/6（覆盖设计文档列出的 image_compressor/image_scaler/image_to_pdf/image_format_converter 四处）。
- ✅ `FileListPanel` 稳定列 ID + 显示文本分离 + 列宽按 ID → Task 7。
- ✅ 去重文件路径存 `UserRole` → Task 8。
- 未覆盖（属后续计划，非本 P0.5 范围）：模块级 `APP_NAME`/`WELCOME_CONFIG`/`FEATURE_MODULES` 改运行时函数、控件保留引用、worker 消息改 key、`settings_page.py` 删除——这些是 P1+ 的内容，本计划范围明确不含。

**2. Placeholder scan**：无 TBD/TODO；每个代码步骤均给出完整代码与命令。

**3. Type consistency**：`plugin.id`（Task 2）在 Task 1 配置中定义为字符串；`Column.id`（Task 7）字符串；`scale_type` 稳定值 `percent/width/height` 在 Task 4 的 combo、`on_scale_type_changed`、`start_scaling`、worker `run` 四处一致；`format_code` 在 Task 3 的 combo data、`start_compression`、worker 三处一致 `keep/JPG/JPEG/PNG/WebP`；`page_size` 在 Task 5 五处一致 `auto/A4/A3/original/smart`。`SidebarButton` 构造签名 `(plugin_id, text, icon_text)` 在 Task 2 定义并被 `register_plugin` 以 `SidebarButton(plugin.id, plugin.name, plugin.icon)` 调用，参数顺序一致。

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-10-18-i18n-decoupling-refactor.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
