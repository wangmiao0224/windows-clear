"""
系统设置工作线程
"""

from ui.workers.base_worker import BaseWorker
from system_settings import (
    SETTINGS_FUNCTIONS, change_save_location, set_refresh_rate, set_dns,
    set_taskbar_alignment, set_screen_timeout, set_computer_name,
    create_restore_point,
)


class SettingsWorker(BaseWorker):

    def __init__(self, keys: list[str],
                 save_location: str = "",
                 save_folders: list[str] | None = None,
                 refresh_rate: str = "",
                 primary_dns: str = "",
                 secondary_dns: str = "",
                 taskbar_alignment: str = "left",
                 screen_timeout: int = 15,
                 computer_name: str = ""):
        super().__init__()
        self._keys = keys
        self._save_location = save_location
        self._save_folders = save_folders
        self._refresh_rate = refresh_rate
        self._primary_dns = primary_dns
        self._secondary_dns = secondary_dns
        self._taskbar_alignment = taskbar_alignment
        self._screen_timeout = screen_timeout
        self._computer_name = computer_name

    def run(self):
        # 先创建系统还原点
        self._log("▸ 创建系统还原点...")
        self._progress(0, "创建还原点")
        rp_ok, rp_msg = create_restore_point(callback=self._log)
        if not rp_ok:
            self._log(f"⚠ {rp_msg}（继续执行设置）")

        n = len(self._keys)
        ok = fail = 0

        for i, k in enumerate(self._keys):
            self._progress(int((i + 1) / (n + 1) * 100), f"设置 {i + 1}/{n}")
            try:
                s, m = self._exec_one(k)
                self._log(m)
                ok += s
                fail += (not s)
            except Exception as e:
                self._log(f"  {k}: {e}")
                fail += 1

        self._progress(100, "完成")
        self._log(f"\n══ 完成: 成功 {ok}  失败 {fail} ══")
        self.finished.emit(ok, fail)

    def _exec_one(self, key: str) -> tuple[bool, str]:
        if key == "change_save_location":
            if not self._save_location:
                return False, "  未指定路径"
            return change_save_location(
                self._save_location, folders=self._save_folders, callback=self._log)
        if key == "set_refresh_rate":
            if not self._refresh_rate or not self._refresh_rate.isdigit():
                return False, "  未选刷新率"
            return set_refresh_rate(int(self._refresh_rate), callback=self._log)
        if key == "set_dns":
            if not self._primary_dns:
                return False, "  未填 DNS"
            return set_dns(self._primary_dns, self._secondary_dns, callback=self._log)
        if key == "set_taskbar_alignment":
            return set_taskbar_alignment(self._taskbar_alignment, callback=self._log)
        if key == "set_screen_timeout":
            return set_screen_timeout(self._screen_timeout, callback=self._log)
        if key == "set_computer_name":
            if not self._computer_name:
                return False, "  未填计算机名"
            return set_computer_name(self._computer_name, callback=self._log)
        if key in SETTINGS_FUNCTIONS:
            return SETTINGS_FUNCTIONS[key](callback=self._log)
        return False, f"  未知: {key}"
