# -*- encoding: utf-8 -*-
"""
共享的目录拖拽输入框

提供一个只读的 QLineEdit，支持从文件管理器拖入本地文件夹，
拖入后发出 directory_dropped(path) 信号。
"""

import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLineEdit


class DirectoryDropLineEdit(QLineEdit):
    """只读输入框，支持拖入本地文件夹"""

    directory_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptDrops(True)

    @staticmethod
    def _local_directory_from_event(event):
        """返回事件中的第一个本地目录路径，没有则返回 None"""
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            if url.isLocalFile():
                directory = url.toLocalFile()
                if os.path.isdir(directory):
                    return directory
        return None

    def dragEnterEvent(self, event):
        """只接受包含本地目录的拖入事件"""
        if self._local_directory_from_event(event) is None:
            event.ignore()
            return
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """只接受包含本地目录的拖拽移动事件"""
        if self._local_directory_from_event(event) is None:
            event.ignore()
            return
        event.acceptProposedAction()

    def dropEvent(self, event):
        """设置拖入的目录路径并发出信号"""
        directory = self._local_directory_from_event(event)
        if directory is None:
            event.ignore()
            return
        self.setText(directory)
        self.directory_dropped.emit(directory)
        event.acceptProposedAction()
