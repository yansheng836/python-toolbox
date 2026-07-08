# -*- encoding: utf-8 -*-
"""
BaseWorker — 共享的 QThread 工作线程基类

所有插件的工作线程应继承此类，以获得统一的信号接口。
定义三个标准信号：progress（int）、status（str）、finished（bool, str）。
子类可根据需要添加额外信号。
"""

from PyQt6.QtCore import QThread, pyqtSignal


class BaseWorker(QThread):
    """工作线程基类

    标准信号:
        progress: 进度值（0-100 或当前处理索引）
        status: 状态文本消息
        finished: (是否成功, 结果消息)

    子类只需实现 run() 方法，可按需添加额外信号。
    """

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)