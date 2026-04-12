"""
开机自启管理工作线程
"""

import winreg
from PySide6.QtCore import Signal
from ui.workers.base_worker import BaseWorker

# winreg 常量值太大, PySide6 Signal 无法序列化,
# 用字符串映射代替
_HIVE_MAP = {
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
}
_HIVE_REVERSE = {v: k for k, v in _HIVE_MAP.items()}


def hive_to_handle(hive_str: str):
    return _HIVE_MAP[hive_str]


class StartupScanWorker(BaseWorker):

    items_ready = Signal(list)

    def run(self):
        items = self._read_startup_registry()
        self.items_ready.emit(items)

    @staticmethod
    def _read_startup_registry() -> list[dict]:
        locations = [
            (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",     "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",     "HKLM"),
            (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU(Once)"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM(Once)"),
        ]

        disabled_cu: dict[str, bool] = {}
        disabled_lm: dict[str, bool] = {}
        for hive, dmap in ((winreg.HKEY_CURRENT_USER, disabled_cu),
                           (winreg.HKEY_LOCAL_MACHINE, disabled_lm)):
            try:
                with winreg.OpenKey(
                    hive,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
                ) as dk:
                    i = 0
                    while True:
                        try:
                            name, data, _ = winreg.EnumValue(dk, i)
                            dmap[name] = isinstance(data, bytes) and len(data) > 0 and data[0] == 0x03
                            i += 1
                        except OSError:
                            break
            except OSError:
                pass

        items: list[dict] = []
        for root, subkey, label in locations:
            try:
                with winreg.OpenKey(root, subkey) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            dmap = disabled_cu if root == winreg.HKEY_CURRENT_USER else disabled_lm
                            items.append({
                                "name": name,
                                "command": str(value),
                                "root_str": _HIVE_REVERSE.get(root, "HKCU"),
                                "subkey": subkey,
                                "label": label,
                                "enabled": not dmap.get(name, False),
                            })
                            i += 1
                        except OSError:
                            break
            except OSError:
                pass
        return items
