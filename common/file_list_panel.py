# -*- encoding: utf-8 -*-
"""
通用文件列表面板组件
供多个插件复用，减少重复代码
"""
import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QSizePolicy, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent


class FileListPanel(QWidget):
    """通用文件列表面板

    管理文件列表的表格显示和操作按钮（添加/删除/上下移/清空）。
    通过 columns 参数配置表格列，通过 file_filter 配置文件选择过滤器。

    Signals:
        files_changed: 文件列表发生变化时发出
    """

    files_changed = pyqtSignal()

    # 默认列宽映射：列名 -> 宽度（px），None 表示使用 Stretch
    DEFAULT_COLUMN_WIDTHS = {
        "文件名": None,  # Stretch
        "大小": 80,
        "页数": 50,
        "尺寸": 100,
        "创建时间": 150,
        "修改时间": 150,
    }

    def __init__(self, parent=None, *,
                 columns=None,
                 file_filter="所有文件 (*.*)",
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
        self.columns = columns or [("文件名", lambda f: os.path.basename(f))]
        self.file_filter = file_filter
        self.button_class = button_class
        self.show_buttons = show_buttons if show_buttons is not None else ["add", "remove", "up", "down"]
        self.column_widths = column_widths
        self.table_min_height = table_min_height
        # 从 file_filter 解析允许的文件扩展名，用于拖拽过滤
        self._allowed_extensions = self._parse_filter_extensions(file_filter)
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

        self.watermark_label = QLabel(
            "拖拽文件到此处，或点击下方「添加文件」"
        )
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
        self.table.setHorizontalHeaderLabels([col[0] for col in self.columns])
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
                self.add_btn = self._create_btn("添加文件(💡支持拖拽)", "add")
                btn_layout.addWidget(self.add_btn)
            elif btn_key == "remove":
                self.remove_btn = self._create_btn("删除选中", "remove")
                btn_layout.addWidget(self.remove_btn)
            elif btn_key == "clear":
                self.clear_btn = self._create_btn("清空列表", "clear")
                btn_layout.addWidget(self.clear_btn)
            elif btn_key == "up":
                self.up_btn = self._create_btn("上移", "up")
                btn_layout.addWidget(self.up_btn)
            elif btn_key == "down":
                self.down_btn = self._create_btn("下移", "down")
                btn_layout.addWidget(self.down_btn)
            elif btn_key == "sort_name":
                self.sort_name_btn = self._create_btn("按名称排序", "sort_name")
                btn_layout.addWidget(self.sort_name_btn)
            elif btn_key == "sort_time":
                self.sort_time_btn = self._create_btn("按创建时间排序", "sort_time")
                btn_layout.addWidget(self.sort_time_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _apply_column_widths(self, header):
        """应用列宽设置

        优先级：用户指定 > DEFAULT_COLUMN_WIDTHS > 默认（第0列Stretch，其余Interactive）
        """
        # 构建列名到索引的映射
        col_name_to_idx = {col[0]: idx for idx, col in enumerate(self.columns)}

        # 初始化每列的设置为 None（表示未设置）
        col_settings = [None] * len(self.columns)

        # 1. 先应用默认值
        for col_name, default_width in self.DEFAULT_COLUMN_WIDTHS.items():
            if col_name in col_name_to_idx:
                col_settings[col_name_to_idx[col_name]] = default_width

        # 2. 再应用用户指定的设置（覆盖默认值）
        if self.column_widths is not None:
            if isinstance(self.column_widths, dict):
                # 格式: {"列名": 宽度, ...}
                for col_name, width in self.column_widths.items():
                    if col_name in col_name_to_idx:
                        col_settings[col_name_to_idx[col_name]] = width
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
                # None 表示 Stretch
                header.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Stretch)
            else:
                # 固定宽度
                header.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Fixed)
                header.resizeSection(col_idx, width)

    def _create_btn(self, text, action):
        """创建按钮并连接信号"""
        btn = self.button_class(text) if self.button_class else QWidget()
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
            self, "选择文件", "", self.file_filter
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
        self.files.sort(key=lambda f: os.path.getctime(f))
        self.update_list()
        self.files_changed.emit()

    def update_list(self):
        """根据 self.files 和 columns 配置更新表格"""
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.files))
        for row, file_path in enumerate(self.files):
            for col_idx, (col_name, col_func) in enumerate(self.columns):
                try:
                    text = str(col_func(file_path))
                except Exception as e:
                    print(f"Error in file_list_panel: {e}")
                    text = "错误"
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col_idx, item)
        self.table.setUpdatesEnabled(True)
        # 切换水印可见性
        self.table_container.setCurrentIndex(0 if not self.files else 1)

    def _parse_filter_extensions(self, file_filter):
        """从 file_filter 解析允许的文件扩展名列表"""
        # file_filter 格式如 "图片文件 (*.jpg *.jpeg *.png)"
        match = re.search(r'\((.*?)\)', file_filter)
        if not match:
            return []
        extensions = []
        for part in match.group(1).split():
            if part.startswith('*.'):
                extensions.append(os.path.splitext(part)[1].lower())
        return extensions

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
