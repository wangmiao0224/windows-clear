"""
系统修复工作线程
"""

from ui.workers.base_worker import BaseWorker
from system_cleanup import CLEANUP_FUNCTIONS


class CleanupWorker(BaseWorker):

    def __init__(self, keys: list[str]):
        super().__init__()
        self._keys = keys

    def run(self):
        n = len(self._keys)
        ok = fail = 0

        for i, k in enumerate(self._keys):
            self._progress(int(i / n * 100), f"修复 {i + 1}/{n}")
            try:
                if k in CLEANUP_FUNCTIONS:
                    self._log(f"\n── {k} ──")
                    s, m = CLEANUP_FUNCTIONS[k](callback=self._log)
                    self._log(m)
                    ok += s
                    fail += (not s)
                else:
                    self._log(f"  未知: {k}")
                    fail += 1
            except Exception as e:
                self._log(f"  {k}: {e}")
                fail += 1

        self._progress(100, "完成")
        self._log(f"\n══ 完成: 成功 {ok}  失败 {fail} ══")
        self.finished.emit(ok, fail)
