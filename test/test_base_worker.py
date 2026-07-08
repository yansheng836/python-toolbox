# -*- encoding: utf-8 -*-
"""
测试 common/base_worker.py 的 BaseWorker 类
"""

import pytest
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from common.base_worker import BaseWorker


class TestBaseWorker:
    """测试 BaseWorker 基类"""

    def test_inherits_qthread(self):
        """BaseWorker 应继承 QThread"""
        assert issubclass(BaseWorker, QThread)

    def test_has_progress_signal(self):
        """应有 progress 信号 (int)"""
        assert hasattr(BaseWorker, "progress")
        sig = BaseWorker.progress
        assert isinstance(sig, pyqtSignal)

    def test_has_status_signal(self):
        """应有 status 信号 (str)"""
        assert hasattr(BaseWorker, "status")
        sig = BaseWorker.status
        assert isinstance(sig, pyqtSignal)

    def test_has_finished_signal(self):
        """应有 finished 信号 (bool, str)"""
        assert hasattr(BaseWorker, "finished")
        sig = BaseWorker.finished
        assert isinstance(sig, pyqtSignal)

    def test_worker_can_be_instantiated(self, qapp):
        """BaseWorker 可以被实例化"""
        worker = BaseWorker()
        assert isinstance(worker, BaseWorker)
        assert isinstance(worker, QThread)

    def test_worker_emits_signals(self, qapp, qtbot):
        """验证 Worker 能正常发射标准信号"""
        results = {"progress": [], "status": [], "finished": []}

        worker = BaseWorker()

        worker.progress.connect(lambda v: results["progress"].append(v))
        worker.status.connect(lambda v: results["status"].append(v))
        worker.finished.connect(lambda s, m: results["finished"].append((s, m)))

        # 直接发射信号（不启动线程）
        worker.progress.emit(50)
        worker.status.emit("工作中...")
        worker.finished.emit(True, "完成")

        assert results["progress"] == [50]
        assert results["status"] == ["工作中..."]
        assert results["finished"] == [(True, "完成")]

    def test_worker_with_extra_signals(self, qapp):
        """子类可以添加额外信号"""
        class CustomWorker(BaseWorker):
            extra_data = pyqtSignal(str, int)

        worker = CustomWorker()
        assert hasattr(worker, "progress")
        assert hasattr(worker, "status")
        assert hasattr(worker, "finished")
        assert hasattr(worker, "extra_data")

        results = []
        worker.extra_data.connect(lambda s, i: results.append((s, i)))
        worker.extra_data.emit("test", 42)
        assert results == [("test", 42)]