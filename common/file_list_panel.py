# -*- encoding: utf-8 -*-
"""
通用文件列表面板组件
供多个插件复用，减少重复代码
"""
import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QSizePolicy, QLabel,
    QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent

from common.i18n import t, bind
from common.utils import Column, get_birth_time


class FileListPanel(QWidget):
    """通用文件列表面板

    管理文件列表的表格显示和操作按钮（添加/删除/上下移/清空）。
    通过 columns 参数配置表格列，通过 file_filter 配置文件选择过滤器。

    Signals:
        files_changed: 文件列表发生变化时发出
    """

    files_changed = pyqtSignal()

    # 默认列宽映射：列 id -> 宽度（px），None 表示使用 Stretch
    DEFAULT_COLUMN_WIDTHS = {
        "filename": None,   # Stretch
        "size": 80,
        "pages": 50,
        "dimensions": 100,
        "created": 150,
        "modified": 150,
    }

    def __init__(self, parent=None, *,
                 columns=None,
                 file_filter=None,
                 button_class=None,
                 show_buttons=None,
                 column_widths=None,
                 table_min_height=200):
        """
        Args:
            parent: 父组件
            columns: 列定义，格式 [("列名", callable), ...]，callable 接收文件路径返回显示文本
            file_filter: 文件选择对话框的过滤器
            button_class: 按钮类（如 AnimatedButton 或 QPushButton）
            show_buttons: 显示的按钮列表，可选值 ["add", "remove", "up", "down", "clear"]
            column_widths: 列宽设置，格式 {列名: 宽度} 或 [(列索引, 宽度), ...]
                          宽度为 None 表示 Stretch，否则为固定宽度（px）
                          未指定的列使用 DEFAULT_COLUMN_WIDTHS 中的默认值
            table_min_height: 表格最小高度（px），默认 200
        """
        super().__init__(parent)
        self.files = []
        self._text_secondary = "#94a3b8"  # 默认次级文本颜色（深色模式）
        self.setAcceptDrops(True)  # 允许整个面板接收拖拽事件
        # 规范化列定义：接受 Column 或旧式 (label, func) / (id, label, func) 元组
        raw_cols = columns or [Column("filename", t("column.filename"), lambda f: os.path.basename(f))]
        self.columns = []
        for col in raw_cols:
            if isinstance(col, Column):
                self.columns.append(col)
            elif len(col) == 3:
                self.columns.append(Column(col[0], col[1], col[2]))
            else:  # (label, func) -> 推导 id
                self.columns.append(Column(col[0], col[0], col[1]))
        self.file_filter = file_filter or t("common.filter.all_files")
        self.button_class = button_class
        self.show_buttons = show_buttons if show_buttons is not None else ["add", "remove", "up", "down"]
        self.column_widths = column_widths
        self.table_min_height = table_min_height
        # 从 file_filter 解析允许的文件扩展名，用于拖拽过滤
        self._allowed_extensions = self._parse_filter_extensions(self.file_filter)
        # 单元格文本缓存：key 为 (文件路径, mtime, 列 id)，避免重复解码未变化的文件
        self._cell_cache = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 表格容器：用堆叠布局切换水印和表格
        self.table_container = QStackedWidget()
        self.table_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.table_container)

        # 水印页面（空表格时显示）
        self.watermark_widget = QWidget()
        watermark_layout = QVBoxLayout(self.watermark_widget)
        watermark_layout.setContentsMargins(0, 0, 0, 0)
        watermark_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.watermark_label = QLabel()
        bind(self.watermark_label, "setText", "common.watermark.drop_here")
        self.watermark_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.watermark_label.setCursor(Qt.CursorShape.IBeamCursor)
        self.watermark_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.watermark_label.setStyleSheet(
            f"font-size: 14px; color: {self._text_secondary}; padding: 20px;"
        )
        self.watermark_widget.setMinimumHeight(self.table_min_height)
        self.watermark_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        watermark_layout.addWidget(self.watermark_label)

        self.table_container.addWidget(self.watermark_widget)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels([self._column_label(col) for col in self.columns])
        header = self.table.horizontalHeader()

        # 应用列宽设置
        self._apply_column_widths(header)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(self.table_min_height)
        # 设置表格扩展策略，使其在窗口变大时自动拉伸
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 启用拖拽支持
        self.table.setAcceptDrops(True)
        self.watermark_widget.setAcceptDrops(True)
        # 事件过滤器安装在表格和水印上，两者切换可见时都能处理拖拽
        self.table.installEventFilter(self)
        self.watermark_widget.installEventFilter(self)
        self.table_container.addWidget(self.table)

        # 按钮区域
        btn_layout = QHBoxLayout()
        for btn_key in self.show_buttons:
            if btn_key == "add":
                self.add_btn = self._create_btn("", "add")
                bind(self.add_btn, "setText", "common.button.add_files")
                btn_layout.addWidget(self.add_btn)
            elif btn_key == "remove":
                self.remove_btn = self._create_btn("", "remove")
                bind(self.remove_btn, "setText", "common.button.remove_selected")
                btn_layout.addWidget(self.remove_btn)
            elif btn_key == "clear":
                self.clear_btn = self._create_btn("", "clear")
                bind(self.clear_btn, "setText", "common.button.clear_list")
                btn_layout.addWidget(self.clear_btn)
            elif btn_key == "up":
                self.up_btn = self._create_btn("", "up")
                bind(self.up_btn, "setText", "common.button.move_up")
                btn_layout.addWidget(self.up_btn)
            elif btn_key == "down":
                self.down_btn = self._create_btn("", "down")
                bind(self.down_btn, "setText", "common.button.move_down")
                btn_layout.addWidget(self.down_btn)
            elif btn_key == "sort_name":
                self.sort_name_btn = self._create_btn("", "sort_name")
                bind(self.sort_name_btn, "setText", "common.button.sort_by_name")
                btn_layout.addWidget(self.sort_name_btn)
            elif btn_key == "sort_time":
                self.sort_time_btn = self._create_btn("", "sort_time")
                bind(self.sort_time_btn, "setText", "common.button.sort_by_time")
                btn_layout.addWidget(self.sort_time_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _column_label(self, col):
        """列显示名：优先词典 column.<id>，缺失时回退列自带 label

        创建表头与语言切换重放共用，保证英文启动时表头即为英文。
        """
        key = f"column.{col.id}"
        translated = t(key)
        return translated if translated != key else col.label

    def retranslate_ui(self):
        """语言切换后重放表头并重渲染单元格（按钮/水印已由 bind 自动重放）

        仅当词典中存在 column.<id> 时替换；插件自有列（列 id 无对应
        通用 key）保持原 label，避免把 key 字符串显示给用户。
        """
        for i, col in enumerate(self.columns):
            key = f"column.{col.id}"
            translated = t(key)
            item = self.table.horizontalHeaderItem(i)
            if item is not None and translated != key:
                item.setText(translated)
        # 语言切换后重新解析过滤器，保证拖拽扩展名判定与当前文案一致
        self._allowed_extensions = self._parse_filter_extensions(self.file_filter)
        self.update_list()

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

    def _create_btn(self, text, action):
        """创建按钮并连接信号"""
        # 默认使用 QPushButton：QWidget 无 clicked 信号，不可作为按钮回退
        btn = self.button_class(text) if self.button_class else QPushButton(text)
        if action == "add":
            btn.clicked.connect(self.add_files)
        elif action == "remove":
            btn.clicked.connect(self.remove_selected)
        elif action == "up":
            btn.clicked.connect(self.move_up)
        elif action == "down":
            btn.clicked.connect(self.move_down)
        elif action == "clear":
            btn.clicked.connect(self.clear_files)
        elif action == "sort_name":
            btn.clicked.connect(self.sort_by_name)
        elif action == "sort_time":
            btn.clicked.connect(self.sort_by_time)
        return btn

    def add_files(self):
        """弹出文件选择对话框，添加文件"""
        from PyQt6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(
            self, t("common.dialog.select_files"), "", self.file_filter
        )
        if files:
            existing = set(self.files)
            added = False
            for f in files:
                if f not in existing:
                    self.files.append(f)
                    existing.add(f)
                    added = True
            if added:
                self.update_list()
                self.files_changed.emit()

    def remove_selected(self):
        """删除选中的文件"""
        selected_rows = []
        for item in self.table.selectedItems():
            if item.column() == 0:
                selected_rows.append(item.row())
        if not selected_rows:
            return
        for row in sorted(set(selected_rows), reverse=True):
            if 0 <= row < len(self.files):
                self.files.pop(row)
        self.update_list()
        self.files_changed.emit()

    def move_up(self):
        """上移选中文件"""
        if not self.files:
            return
        selected_rows = []
        for item in self.table.selectedItems():
            if item.column() == 0:
                selected_rows.append(item.row())
        if not selected_rows:
            return
        row = sorted(set(selected_rows))[0]
        if row > 0:
            self.files[row], self.files[row - 1] = self.files[row - 1], self.files[row]
            self.update_list()
            self.table.selectRow(row - 1)
            self.files_changed.emit()

    def move_down(self):
        """下移选中文件"""
        if not self.files:
            return
        selected_rows = []
        for item in self.table.selectedItems():
            if item.column() == 0:
                selected_rows.append(item.row())
        if not selected_rows:
            return
        row = sorted(set(selected_rows))[0]
        if row < len(self.files) - 1:
            self.files[row], self.files[row + 1] = self.files[row + 1], self.files[row]
            self.update_list()
            self.table.selectRow(row + 1)
            self.files_changed.emit()

    def get_files(self):
        """获取文件列表（副本）"""
        return list(self.files)

    def set_files(self, files):
        """设置文件列表"""
        self.files = list(files)
        self.update_list()
        self.files_changed.emit()

    def clear_files(self):
        """清空文件列表"""
        self.files = []
        self.update_list()
        self.files_changed.emit()

    def sort_by_name(self):
        """按文件名称排序"""
        if len(self.files) < 2:
            return
        self.files.sort(key=lambda f: os.path.basename(f).lower())
        self.update_list()
        self.files_changed.emit()

    def sort_by_time(self):
        """按文件创建时间排序（从早到晚）"""
        if len(self.files) < 2:
            return
        self.files.sort(key=get_birth_time)
        self.update_list()
        self.files_changed.emit()

    def update_list(self):
        """根据 self.files 和 columns 配置更新表格

        单元格文本按 (路径, mtime, 列 id) 缓存，未变化的文件不再重复解码，
        避免每次增删都触发全表重算（尤其图片尺寸读取）。
        """
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.files))
        new_cache = {}
        for row, file_path in enumerate(self.files):
            try:
                mtime = os.path.getmtime(file_path)
            except OSError as e:
                print(f"Error stat file {file_path}: {e}")
                mtime = None
            for col_idx, col in enumerate(self.columns):
                cache_key = (file_path, mtime, col.id)
                if cache_key in self._cell_cache:
                    text = self._cell_cache[cache_key]
                else:
                    try:
                        text = str(col.func(file_path))
                    except Exception as e:
                        print(f"Error in file_list_panel: {e}")
                        text = t("common.cell.error")
                new_cache[cache_key] = text
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col_idx, item)
        self._cell_cache = new_cache
        self.table.setUpdatesEnabled(True)
        # 切换水印可见性
        self.table_container.setCurrentIndex(0 if not self.files else 1)

    def _parse_filter_extensions(self, file_filter):
        """从 file_filter 解析允许的文件扩展名列表

        遍历所有 ``;;`` 分段与每个分段中的括号组，收集全部 *.ext 扩展名，
        避免只取第一个括号组导致对话框允许、拖拽拒绝的不一致。
        忽略 ``*.*`` / ``*`` 通配。
        """
        extensions = []
        seen = set()
        for segment in file_filter.split(';;'):
            for match in re.finditer(r'\(([^()]*)\)', segment):
                for part in match.group(1).split():
                    if not part.startswith('*.'):
                        continue
                    ext = os.path.splitext(part)[1].lower()
                    if ext and ext != '.*' and ext not in seen:
                        seen.add(ext)
                        extensions.append(ext)
        return extensions

    def set_file_filter(self, file_filter):
        """更新文件选择过滤器并重新解析拖拽扩展名

        语言切换后插件可调用此方法同步新的过滤器文案，扩展名判定随之更新。
        """
        self.file_filter = file_filter
        self._allowed_extensions = self._parse_filter_extensions(file_filter)

    def _is_allowed_file(self, file_path):
        """检查文件扩展名是否允许"""
        if not self._allowed_extensions:
            return True
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self._allowed_extensions

    def eventFilter(self, obj, event):
        """事件过滤器：处理表格和水印的拖拽事件"""
        if obj is self.table or obj is self.watermark_widget:
            if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                return self._handle_drag_enter(event)
            elif event.type() == QEvent.Type.Drop:
                return self._handle_drop(event)
        return super().eventFilter(obj, event)

    def _handle_drag_enter(self, event):
        """拖拽进入事件：只接受匹配的文件类型"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and self._is_allowed_file(url.toLocalFile()):
                    event.acceptProposedAction()
                    return True
        event.ignore()
        return True

    def _handle_drop(self, event):
        """处理文件放下事件，添加拖拽的文件到列表"""
        if event.mimeData().hasUrls():
            existing = set(self.files)
            added = False
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if self._is_allowed_file(file_path) and file_path not in existing:
                        self.files.append(file_path)
                        existing.add(file_path)
                        added = True
            if added:
                self.update_list()
                self.files_changed.emit()
            event.acceptProposedAction()
            return True
        event.ignore()
        return True

    def update_theme(self, theme):
        """更新表格主题样式"""
        self._text_secondary = theme['text_secondary']
        self.watermark_widget.setStyleSheet(
            f"background-color: {theme['bg']}; border: 1px solid {theme['surface']}; border-radius: 8px;"
        )
        self.watermark_label.setStyleSheet(
            f"font-size: 14px; color: {theme['text_secondary']}; padding: 20px;"
        )
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {theme['bg']};
                border: 1px solid {theme['surface']};
                border-radius: 8px;
                color: {theme['text']};
                gridline-color: {theme['surface']};
            }}
            QHeaderView::section {{
                background-color: {theme['bg_secondary']};
                color: {theme['text_secondary']};
                padding: 4px 8px;
                border: none;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QTableCornerButton::section {{
                background-color: {theme['bg_secondary']};
                border: none;
            }}
        """)
