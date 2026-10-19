# -*- encoding: utf-8 -*-
"""
BaseWorker — 共享的 QThread 工作线程基类

所有插件的工作线程应继承此类，以获得统一的信号接口。
定义三个标准信号：progress（int）、status（str）、result（bool, str）。
注意 signal 命名为 result 而非 finished，避免遮蔽 QThread 自带的无参 finished 信号
（run() 结束由 C++ 发出，供线程收尾 / deleteLater 惯用法使用）。
子类可根据需要添加额外信号。

取消约定：子类在 run() 的批处理循环中应调用 is_cancelled() 检查取消标志，
若返回 True 则尽早 emit 取消结果并 return。cancel() 线程安全：仅置标志，
不等待线程退出（退出由 QThread.finished 收尾处理）。
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

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def cancel(self):
        """请求取消；仅置标志，由 run() 循环检查后尽早退出"""
        self._cancelled = True

    def is_cancelled(self):
        """run() 循环调用，True 表示已收到取消请求应尽快退出"""
        return self._cancelled


def worker_cancelled(worker):
    """安全判定 worker 是否收到取消请求（worker 可能为 None 或尚未创建）"""
    return bool(worker is not None and worker.is_cancelled())