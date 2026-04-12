"""
性能监控页 — 6 张信息卡片 + 实时刷新
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QProgressBar,
)
from PySide6.QtCore import QTimer

from ui.components.info_card import InfoCard
from ui.workers.monitor_worker import MonitorInitWorker, MonitorTickWorker
from ui.theme import WARNING, INFO, SUCCESS


class MonitorPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._prev_net: dict | None = None
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(2000)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_worker: MonitorTickWorker | None = None
        self._build()
        self._load_initial()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)

        # 上排: 系统 / CPU / GPU
        top = QHBoxLayout()
        top.setSpacing(8)

        self._sys_card = InfoCard("系统")
        self._sys_card.add_row("系统:", "sys_os")
        self._sys_card.add_row("版本:", "sys_ver")
        self._sys_card.add_row("主机:", "sys_host")
        self._sys_card.add_row("运行:", "sys_uptime")
        top.addWidget(self._sys_card)

        self._cpu_card = InfoCard("CPU")
        self._cpu_card.add_row("型号:", "cpu_name")
        self._cpu_card.add_row("核心:", "cpu_cores")
        self._cpu_card.add_row("频率:", "cpu_freq")
        self._cpu_card.add_row("占用:", "cpu_usage")
        self._cpu_card.add_row("温度:", "cpu_temp")
        top.addWidget(self._cpu_card)

        self._gpu_card = InfoCard("GPU")
        self._gpu_card.add_row("型号:", "gpu_name")
        self._gpu_card.add_row("温度:", "gpu_temp")
        self._gpu_card.add_row("占用:", "gpu_usage")
        self._gpu_card.add_row("显存:", "gpu_mem")
        top.addWidget(self._gpu_card)

        lay.addLayout(top)

        # 下排: 内存 / 磁盘 / 网络
        bot = QHBoxLayout()
        bot.setSpacing(8)

        self._mem_card = InfoCard("内存")
        self._mem_card.add_row("总量:", "mem_total")
        self._mem_card.add_row("已用:", "mem_used")
        self._mem_card.add_row("可用:", "mem_avail")
        self._mem_card.add_progress("mem_bar", WARNING)
        bot.addWidget(self._mem_card)

        self._disk_card = InfoCard("磁盘")
        self._disk_container = self._disk_card
        bot.addWidget(self._disk_card, 2)

        self._net_card = InfoCard("网络")
        self._net_card.add_row("上传:", "net_sent")
        self._net_card.add_row("下载:", "net_recv")
        self._net_card.add_row("速率↑:", "net_up_speed")
        self._net_card.add_row("速率↓:", "net_dn_speed")
        bot.addWidget(self._net_card)

        lay.addLayout(bot)
        lay.addStretch()

    # ── 数据加载 ──

    def _load_initial(self):
        self._init_worker = MonitorInitWorker()
        self._init_worker.data_ready.connect(self._on_init_data)
        self._init_worker.start()

    def _on_init_data(self, info: dict):
        s = info["system"]
        self._sys_card.update_value("sys_os", s["os"])
        self._sys_card.update_value("sys_ver", s["version"])
        self._sys_card.update_value("sys_host", s["hostname"])
        self._sys_card.update_value("sys_uptime", s["uptime"])

        cpu = info["cpu"]
        self._cpu_card.update_value("cpu_name", cpu["name"][:30])
        self._cpu_card.update_value("cpu_cores",
            f"{cpu['cores_physical']}物理 / {cpu['cores_logical']}逻辑")
        self._cpu_card.update_value("cpu_freq", cpu["freq"])
        self._cpu_card.update_value("cpu_usage", f"{cpu['usage']}%")
        self._cpu_card.update_value("cpu_temp", cpu["temp"])

        gpu = info["gpu"]
        self._gpu_card.update_value("gpu_name", gpu["name"][:30])
        self._gpu_card.update_value("gpu_temp", gpu["temp"])
        self._gpu_card.update_value("gpu_usage", gpu["usage"])
        self._gpu_card.update_value("gpu_mem", f"{gpu['mem_used']} / {gpu['mem_total']}")

        self._update_mem(info["memory"])
        self._build_disks(info["disks"])

        net = info["network"]
        self._prev_net = net
        self._net_card.update_value("net_sent", f"{net['sent_mb']:.1f} MB")
        self._net_card.update_value("net_recv", f"{net['recv_mb']:.1f} MB")
        self._net_card.update_value("net_up_speed", "0 KB/s")
        self._net_card.update_value("net_dn_speed", "0 KB/s")

        self._tick_timer.start()

    def _update_mem(self, mem: dict):
        self._mem_card.update_value("mem_total", f"{mem['total']:.1f} GB")
        self._mem_card.update_value("mem_used", f"{mem['used']:.1f} GB ({mem['percent']}%)")
        self._mem_card.update_value("mem_avail", f"{mem['available']:.1f} GB")
        self._mem_card.update_progress("mem_bar", int(mem["percent"]))

    def _build_disks(self, disks: list[dict]):
        for d in disks:
            self._disk_card.add_row(
                d["mountpoint"],
                f"disk_{d['mountpoint']}",
                f"{d['used']:.0f}/{d['total']:.0f}G ({d['percent']}%)",
            )
            self._disk_card.add_progress(f"disk_bar_{d['mountpoint']}", INFO)
            self._disk_card.update_progress(f"disk_bar_{d['mountpoint']}", int(d["percent"]))

    # ── 实时刷新 ──

    def _tick(self):
        if self._tick_worker and self._tick_worker.isRunning():
            return
        self._tick_worker = MonitorTickWorker()
        self._tick_worker.data_ready.connect(self._on_tick_data)
        self._tick_worker.start()

    def _on_tick_data(self, rt: dict):
        self._cpu_card.update_value("cpu_usage", f"{rt['cpu_usage']}%")
        self._update_mem(rt["memory"])

        net = rt["network"]
        self._net_card.update_value("net_sent", f"{net['sent_mb']:.1f} MB")
        self._net_card.update_value("net_recv", f"{net['recv_mb']:.1f} MB")

        if self._prev_net:
            up = (net["bytes_sent"] - self._prev_net["bytes_sent"]) / 2 / 1024
            dn = (net["bytes_recv"] - self._prev_net["bytes_recv"]) / 2 / 1024
            self._net_card.update_value("net_up_speed",
                f"{up / 1024:.1f} MB/s" if up > 1024 else f"{up:.0f} KB/s")
            self._net_card.update_value("net_dn_speed",
                f"{dn / 1024:.1f} MB/s" if dn > 1024 else f"{dn:.0f} KB/s")
        self._prev_net = net
