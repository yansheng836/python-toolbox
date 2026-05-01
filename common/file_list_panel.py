"""
通用文件列表面板组件
供多个插件复用，减少重复代码
"""
import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
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

    def __init__(self, parent=None, *,
                 columns=None,
                 file_filter="所有文件 (*.*)",
                 button_class=None,
                 show_buttons=None):
        """
        Args:
            parent: 父组件
            columns: 列定义，格式 [("列名", callable), ...]，callable 接收文件路径返回显示文本
            file_filter: 文件选择对话框的过滤器
            button_class: 按钮类（如 AnimatedButton 或 QPushButton）
            show_buttons: 显示的按钮列表，可选值 ["add", "remove", "up", "down", "clear"]
        """
        super().__init__(parent)
        self.files = []
        self.columns = columns or [("文件名", lambda f: os.path.basename(f))]
        self.file_filter = file_filter
        self.button_class = button_class
        self.show_buttons = show_buttons if show_buttons is not None else ["add", "remove", "up", "down"]
        # 从 file_filter 解析允许的文件扩展名，用于拖拽过滤
        self._allowed_extensions = self._parse_filter_extensions(file_filter)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels([col[0] for col in self.columns])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(200)
        # 启用拖拽支持
        self.table.setAcceptDrops(True)
        self.table.installEventFilter(self)
        layout.addWidget(self.table)

        # 按钮（按 show_buttons 顺序添加）
        btn_layout = QHBoxLayout()
        for btn_key in self.show_buttons:
            if btn_key == "add":
                self.add_btn = self._create_btn("添加文件", "add")
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
            added = False
            for f in files:
                if f not in self.files:
                    self.files.append(f)
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
        self.table.setRowCount(0)
        for file_path in self.files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col_idx, (col_name, col_func) in enumerate(self.columns):
                try:
                    text = str(col_func(file_path))
                except Exception:
                    text = "错误"
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col_idx, item)

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
        """事件过滤器：处理表格的拖拽事件"""
        if obj is self.table:
            if event.type() == QEvent.Type.DragEnter:
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
            added = False
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if self._is_allowed_file(file_path) and file_path not in self.files:
                        self.files.append(file_path)
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
                padding: 8px;
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
