"""
应用安装工作线程 — 并行下载/安装，支持逐个取消
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PySide6.QtCore import Signal
from ui.workers.base_worker import BaseWorker
from app_installer import install_app

MAX_CONCURRENT = 3  # 最大并行下载数


class InstallWorker(BaseWorker):

    app_status = Signal(str, str, str)    # winget_id, text, color
    app_progress = Signal(str, int)       # winget_id, 0-100

    def __init__(self, apps: list[dict]):
        super().__init__()
        self._apps = apps
        self._cancel_all = threading.Event()
        self._cancel_map: dict[str, threading.Event] = {}
        for app in apps:
            self._cancel_map[app["winget_id"]] = threading.Event()

    def cancel(self):
        """取消所有"""
        self._cancel_all.set()
        for ev in self._cancel_map.values():
            ev.set()

    def cancel_app(self, winget_id: str):
        """取消单个应用"""
        ev = self._cancel_map.get(winget_id)
        if ev:
            ev.set()

    def _install_one(self, app: dict) -> tuple[str, bool]:
        wid = app["winget_id"]
        cancel_ev = self._cancel_map[wid]

        if cancel_ev.is_set() or self._cancel_all.is_set():
            self.app_status.emit(wid, "取消", "#F59E0B")
            return wid, None  # cancelled

        self.app_status.emit(wid, "...", "#2D8CF0")
        self.app_progress.emit(wid, 0)

        def _progress(pct, _wid=wid):
            self.app_progress.emit(_wid, pct)

        s, _ = install_app(app, callback=self._log, progress_cb=_progress, cancel_event=cancel_ev)

        if cancel_ev.is_set():
            self.app_status.emit(wid, "取消", "#F59E0B")
            self.app_progress.emit(wid, 0)
            return wid, None

        if s:
            self.app_status.emit(wid, "OK", "#19BE6B")
            self.app_progress.emit(wid, 100)
        else:
            self.app_status.emit(wid, "NG", "#ED4014")
            self.app_progress.emit(wid, 0)

        return wid, s

    def run(self):
        n = len(self._apps)
        ok = fail = cancelled = 0
        done_count = 0

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
            futures = {pool.submit(self._install_one, app): app for app in self._apps}

            for future in as_completed(futures):
                wid, success = future.result()
                done_count += 1
                self._progress(int(done_count / n * 100), f"已完成 {done_count}/{n}")

                if success is None:
                    cancelled += 1
                elif success:
                    ok += 1
                else:
                    fail += 1

        self._progress(100, "完成")
        msg = f"\n══ 完成: 成功 {ok}  失败 {fail}"
        if cancelled:
            msg += f"  取消 {cancelled}"
        msg += " ══"
        self._log(msg)
        self.finished.emit(ok, fail)
