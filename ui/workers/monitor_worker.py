"""
性能监控工作线程 — 首次加载 + 周期刷新
"""

from PySide6.QtCore import Signal
from ui.workers.base_worker import BaseWorker
from hardware_monitor import get_all_info, get_realtime_info


class MonitorInitWorker(BaseWorker):
    """首次加载全部硬件信息"""

    data_ready = Signal(dict)

    def run(self):
        info = get_all_info()
        self.data_ready.emit(info)


class MonitorTickWorker(BaseWorker):
    """周期刷新实时数据"""

    data_ready = Signal(dict)

    def run(self):
        rt = get_realtime_info()
        self.data_ready.emit(rt)
