"""
系统修复页 — 修复选项 + 垃圾应用扫描 + Windows 激活
所有后台操作均使用 QThread + Signal, 确保线程安全
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
    QLabel, QCheckBox, QLineEdit, QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, Slot, QThread

from ui.components.check_group import CheckGroup
from ui.workers.cleanup_worker import CleanupWorker
from system_cleanup import (
    CLEANUP_ITEMS, scan_installed_apps, uninstall_app,
    get_activation_status, activate_windows,
)
from jihuo import kms_activate


# ── 辅助工作线程 (全部使用 Signal 通信) ──

class _JunkScanThread(QThread):
    result = Signal(list, int)

    def run(self):
        apps = scan_installed_apps()
        junk = [a for a in apps if a["is_junk"]]
        self.result.emit(junk, len(apps))


class _JunkUninstallThread(QThread):
    log = Signal(str)
    progress = Signal(int, str)
    done = Signal(int, int)

    def __init__(self, apps):
        super().__init__()
        self._apps = apps

    def run(self):
        ok = fail = 0
        n = len(self._apps)
        for i, a in enumerate(self._apps):
            self.progress.emit(int(i / n * 100), f"卸载 {a['name']} ({i + 1}/{n})")
            s, _ = uninstall_app(a, callback=lambda m: self.log.emit(m))
            ok += s
            fail += (not s)
        self.progress.emit(100, "完成")
        self.log.emit(f"\n══ 卸载完成: 成功 {ok}  失败 {fail} ══")
        self.done.emit(ok, fail)


class _ActivationCheckThread(QThread):
    log = Signal(str)
    status = Signal(str, str)

    def run(self):
        info = get_activation_status(callback=lambda m: self.log.emit(m))
        color = "#19BE6B" if info["status"] == "已激活" else "#ED4014"
        self.status.emit(info["status"], color)


class _KmsThread(QThread):
    log = Signal(str)
    status = Signal(str, str)
    key_found = Signal(str)

    def run(self):
        ok, used_key = kms_activate(callback=lambda m: self.log.emit(m))
        self.log.emit(f"\n══ {'激活成功' if ok else '激活失败'} ══")
        if ok:
            self.key_found.emit(used_key)
        self.log.emit("\n══ 重新检测激活状态 ══")
        info = get_activation_status(callback=lambda m: self.log.emit(m))
        color = "#19BE6B" if info["status"] == "已激活" else "#ED4014"
        self.status.emit(info["status"], color)


class _ActivateThread(QThread):
    log = Signal(str)
    done = Signal()

    def __init__(self, key: str):
        super().__init__()
        self._key = key

    def run(self):
        ok, msg = activate_windows(self._key, callback=lambda m: self.log.emit(m))
        self.log.emit(f"\n══ {'激活成功' if ok else '激活失败'} ══")
        self.done.emit()


# ── 主页面 ──

class CleanupPage(QWidget):

    def __init__(self, log_panel, parent=None):
        super().__init__(parent)
        self._log = log_panel
        self._worker = None
        self._junk_vars: dict[str, dict] = {}
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(10)

        # ── 系统修复 ──
        hint = QLabel("以下操作适用于长期使用后出现问题的电脑")
        hint.setProperty("cssClass", "warning")
        lay.addWidget(hint)

        self._cleanup_group = CheckGroup("", columns=2, show_buttons=True)
        for item in CLEANUP_ITEMS:
            tooltip = item.get("description", "")
            self._cleanup_group.add_item(item["key"], item["name"], tooltip=tooltip)
        lay.addWidget(self._cleanup_group)

        row_btn = QHBoxLayout()
        row_btn.addStretch()
        self._cleanup_btn = QPushButton("执行系统修复")
        self._cleanup_btn.setProperty("cssClass", "warning")
        self._cleanup_btn.setMinimumWidth(120)
        self._cleanup_btn.clicked.connect(self._run_cleanup)
        row_btn.addWidget(self._cleanup_btn)
        lay.addLayout(row_btn)

        self._add_sep(lay)

        # ── 垃圾应用检测 ──
        junk_hdr = QHBoxLayout()
        junk_hdr.addWidget(self._section_label("垃圾应用检测"))
        junk_hdr.addStretch()

        self._scan_btn = QPushButton("扫描已安装应用")
        self._scan_btn.setProperty("cssClass", "secondary")
        self._scan_btn.setMinimumWidth(120)
        self._scan_btn.clicked.connect(self._scan_junk)
        junk_hdr.addWidget(self._scan_btn)

        self._uninstall_btn = QPushButton("卸载选中")
        self._uninstall_btn.setProperty("cssClass", "danger-outline")
        self._uninstall_btn.setMinimumWidth(80)
        self._uninstall_btn.setEnabled(False)
        self._uninstall_btn.clicked.connect(self._uninstall_junk)
        junk_hdr.addWidget(self._uninstall_btn)
        lay.addLayout(junk_hdr)

        self._junk_scroll = QScrollArea()
        self._junk_scroll.setWidgetResizable(True)
        self._junk_scroll.setFixedHeight(120)
        self._junk_container = QWidget()
        self._junk_lay = QVBoxLayout(self._junk_container)
        self._junk_lay.setContentsMargins(4, 4, 4, 4)
        self._junk_lay.setSpacing(2)
        self._junk_lay.addWidget(QLabel("点击「扫描已安装应用」开始检测"))
        self._junk_lay.addStretch()
        self._junk_scroll.setWidget(self._junk_container)
        lay.addWidget(self._junk_scroll)

        self._add_sep(lay)

        # ── Windows 激活 ──
        act_hdr = QHBoxLayout()
        act_hdr.addWidget(self._section_label("Windows 激活"))
        self._act_status = QLabel("")
        self._act_status.setProperty("cssClass", "hint")
        act_hdr.addWidget(self._act_status)
        act_hdr.addStretch()

        check_btn = QPushButton("检测状态")
        check_btn.setProperty("cssClass", "secondary")
        check_btn.setMinimumWidth(80)
        check_btn.clicked.connect(self._check_activation)
        act_hdr.addWidget(check_btn)

        self._kms_btn = QPushButton("KMS 激活")
        self._kms_btn.setProperty("cssClass", "warning-outline")
        self._kms_btn.setMinimumWidth(80)
        self._kms_btn.clicked.connect(self._run_kms)
        act_hdr.addWidget(self._kms_btn)
        lay.addLayout(act_hdr)

        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("密钥:"))
        self._key_edit = QLineEdit()
        self._key_edit.setFixedWidth(280)
        self._key_edit.setPlaceholderText("输入产品密钥或使用 KMS 激活")
        key_row.addWidget(self._key_edit)
        self._act_btn = QPushButton("激活")
        self._act_btn.setProperty("cssClass", "success")
        self._act_btn.setMinimumWidth(60)
        self._act_btn.clicked.connect(self._run_activation)
        key_row.addWidget(self._act_btn)
        key_row.addStretch()
        lay.addLayout(key_row)

        lay.addStretch()

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("cssClass", "section-title")
        return lbl

    @staticmethod
    def _add_sep(layout):
        sep = QFrame()
        sep.setProperty("cssClass", "separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

    # ── 系统修复 ──

    def _run_cleanup(self, skip_confirm=False):
        keys = self._cleanup_group.selected_keys()
        if not keys:
            if not skip_confirm:
                QMessageBox.warning(self, "提示", "请至少选择一项")
            return
        if not skip_confirm and QMessageBox.question(
            self, "确认",
            f"执行 {len(keys)} 项系统修复？\n部分操作不可逆，建议先备份数据。",
        ) != QMessageBox.StandardButton.Yes:
            return
        self._cleanup_btn.setEnabled(False)
        self._log.reset()
        self._log.append("══ 开始系统修复 ══")
        self._worker = CleanupWorker(keys)
        self._worker.log.connect(self._log.append)
        self._worker.progress.connect(self._log.set_progress)
        self._worker.finished.connect(self._on_cleanup_done)
        self._worker.start()

    def _on_cleanup_done(self, ok: int, fail: int):
        self._cleanup_btn.setEnabled(True)
        self._log.set_finished(ok, fail)

    # ── 垃圾应用 ──

    def _scan_junk(self):
        self._scan_btn.setEnabled(False)
        self._clear_junk_list()
        self._junk_lay.addWidget(QLabel("正在扫描..."))
        self._scan_thread = _JunkScanThread()
        self._scan_thread.result.connect(self._show_junk_results)
        self._scan_thread.start()

    @Slot(list, int)
    def _show_junk_results(self, junk: list, total: int):
        self._clear_junk_list()
        self._junk_vars.clear()
        css = "warning" if junk else "success"
        summary = QLabel(f"共扫描 {total} 个应用，发现 {len(junk)} 个可疑应用")
        summary.setProperty("cssClass", css)
        self._junk_lay.addWidget(summary)
        for app in junk:
            row = QHBoxLayout()
            cb = QCheckBox(app["name"])
            cb.setChecked(True)
            row.addWidget(cb)
            if app.get("publisher"):
                pub = QLabel(app["publisher"])
                pub.setProperty("cssClass", "hint")
                row.addWidget(pub)
            row.addStretch()
            w = QWidget()
            w.setLayout(row)
            self._junk_lay.addWidget(w)
            self._junk_vars[app["name"]] = {"cb": cb, "app": app}
        self._junk_lay.addStretch()
        self._scan_btn.setEnabled(True)
        self._uninstall_btn.setEnabled(bool(junk))

    def _clear_junk_list(self):
        while self._junk_lay.count():
            item = self._junk_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _uninstall_junk(self):
        sel = [v["app"] for v in self._junk_vars.values() if v["cb"].isChecked()]
        if not sel:
            QMessageBox.warning(self, "提示", "请先选择要卸载的应用")
            return
        if QMessageBox.question(
            self, "确认", f"确定卸载 {len(sel)} 个应用？\n此操作不可逆。",
        ) != QMessageBox.StandardButton.Yes:
            return
        self._uninstall_btn.setEnabled(False)
        self._scan_btn.setEnabled(False)
        self._log.reset()
        self._log.append("══ 开始卸载垃圾应用 ══")
        self._uninstall_thread = _JunkUninstallThread(sel)
        self._uninstall_thread.log.connect(self._log.append)
        self._uninstall_thread.progress.connect(self._log.set_progress)
        self._uninstall_thread.done.connect(self._on_uninstall_done)
        self._uninstall_thread.start()

    @Slot(int, int)
    def _on_uninstall_done(self, ok: int, fail: int):
        self._scan_btn.setEnabled(True)
        self._uninstall_btn.setEnabled(True)
        QMessageBox.information(self, "完成", f"成功: {ok}\n失败: {fail}")
        self._scan_junk()

    # ── Windows 激活 ──

    def _check_activation(self):
        self._act_status.setText("检测中...")
        self._act_status.setStyleSheet("color: #FF9900; font-size: 12px;")
        self._log.reset()
        self._log.append("══ 检测 Windows 激活状态 ══")
        self._act_check_thread = _ActivationCheckThread()
        self._act_check_thread.log.connect(self._log.append)
        self._act_check_thread.status.connect(self._on_act_status)
        self._act_check_thread.start()

    @Slot(str, str)
    def _on_act_status(self, text: str, color: str):
        self._act_status.setText(text)
        self._act_status.setStyleSheet(f"color: {color}; font-size: 12px;")

    def _run_kms(self):
        self._kms_btn.setEnabled(False)
        self._log.reset()
        self._log.append("══ 开始 KMS 激活 ══")
        self._kms_thread = _KmsThread()
        self._kms_thread.log.connect(self._log.append)
        self._kms_thread.status.connect(self._on_act_status)
        self._kms_thread.key_found.connect(self._key_edit.setText)
        self._kms_thread.finished.connect(lambda: self._kms_btn.setEnabled(True))
        self._kms_thread.start()

    def _run_activation(self):
        key = self._key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "请输入产品密钥")
            return
        if QMessageBox.question(
            self, "确认", f"使用密钥激活 Windows？\n{key}",
        ) != QMessageBox.StandardButton.Yes:
            return
        self._act_btn.setEnabled(False)
        self._log.reset()
        self._log.append("══ 开始激活 Windows ══")
        self._activate_thread = _ActivateThread(key)
        self._activate_thread.log.connect(self._log.append)
        self._activate_thread.done.connect(self._on_activate_done)
        self._activate_thread.start()

    @Slot()
    def _on_activate_done(self):
        self._act_btn.setEnabled(True)
        self._check_activation()
