# -*- encoding: utf-8 -*-
"""
BaseWorker — 共享的 QThread 工作线程基类

所有插件的工作线程应继承此类，以获得统一的信号接口。
定义三个标准信号：progress（int）、status（str）、result（bool, str）。
注意 signal 命名为 result 而非 finished，避免遮蔽 QThread 自带的无参 finished 信号
（run() 结束由 C++ 发出，供线程收尾 / deleteLater 惯用法使用）。
子类可根据需要添加额外信号。
"""

from PyQt6.QtCore import QThread, pyqtSignal


class BaseWorker(QThread):
    """工作线程基类

    标准信号:
        progress: 进度值（0-100 或当前处理索引）
        status: 状态文本消息
        result: (是否成功, 结果消息)

    子类只需实现 run() 方法，可按需添加额外信号。
    """

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result = pyqtSignal(bool, str)