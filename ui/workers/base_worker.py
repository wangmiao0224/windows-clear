"""
基础工作线程 — 提供日志/进度/完成信号的 QThread 基类
"""

from PySide6.QtCore import QThread, Signal


class BaseWorker(QThread):
    """
    所有后台工作线程的基类。

    信号:
        log(str)               → 日志消息
        progress(int, str)     → 进度值 0-100, 状态文本
        finished(int, int)     → 成功数, 失败数
    """

    log = Signal(str)
    progress = Signal(int, str)
    finished = Signal(int, int)

    def _log(self, msg: str):
        """供回调使用的日志方法"""
        self.log.emit(msg)

    def _progress(self, value: int, status: str = ""):
        self.progress.emit(value, status)
