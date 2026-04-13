"""
应用安装页 — 应用卡片网格 + 每个应用独立进度条 + 并行安装/取消
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLabel, QCheckBox, QPushButton, QMessageBox, QProgressBar,
    QScrollArea,
)
from PySide6.QtCore import Qt, Slot, Signal, QThread

from ui.icon_helper import get_icon
from ui.workers.install_worker import InstallWorker
from ui.components.status_bar import _SmoothProgressBar
from app_installer import check_winget_available

COLS = 4


class _WingetCheckThread(QThread):
    result = Signal(bool)

    def run(self):
        self.result.emit(check_winget_available())


class _AppCard(QWidget):
    """单个应用的卡片: 勾选框 + 取消按钮 + 小进度条 + 状态"""

    cancel_requested = Signal(str)  # winget_id

    def __init__(self, app_data: dict, icon, parent=None):
        super().__init__(parent)
        self.app = app_data
        self.setFixedHeight(38)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 1, 2, 1)
        lay.setSpacing(1)

        # 第一行: 勾选框 + 状态 + 取消按钮
        top = QHBoxLayout()
        top.setSpacing(4)
        self.cb = QCheckBox(app_data["name"])
        self.cb.setChecked(True)
        self.cb.setIcon(icon)
        top.addWidget(self.cb, 1)

        self.status_lbl = QLabel("")
        self.status_lbl.setFixedWidth(22)
        self.status_lbl.setStyleSheet("font-family: Consolas; font-size: 12px;")
        top.addWidget(self.status_lbl)

        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setFixedSize(18, 18)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #C0C4CC; font-size: 12px;
                min-width: 18px; min-height: 18px;
                padding: 0;
            }
            QPushButton:hover { color: #ED4014; }
        """)
        self.cancel_btn.setToolTip("取消此应用")
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(
            lambda: self.cancel_requested.emit(self.app["winget_id"])
        )
        top.addWidget(self.cancel_btn)
        lay.addLayout(top)

        # 第二行: 进度条 (默认隐藏)
        self.progress = _SmoothProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        lay.addWidget(self.progress)

    def set_status(self, text: str, color: str):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(
            f"color: {color}; font-family: Consolas; font-size: 12px;"
        )
        # 正在进行时显示取消按钮
        if text == "...":
            self.cancel_btn.show()
        else:
            self.cancel_btn.hide()

    def set_progress(self, value: int):
        if not self.progress.isVisible():
            self.progress.show()
        self.progress.smooth_set(value)

    def reset(self):
        self.status_lbl.setText("")
        self.progress.setValue(0)
        self.progress.hide()
        self.cancel_btn.hide()


class AppsPage(QWidget):

    def __init__(self, config_data: dict, log_panel, parent=None):
        super().__init__(parent)
        self._log = log_panel
        self._config = config_data
        self._app_cards: dict[str, _AppCard] = {}   # winget_id -> card
        self._worker: InstallWorker | None = None
        self._build()
        self._check_winget()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        # 顶栏
        top = QHBoxLayout()
        self._winget_lbl = QLabel("检测 winget...")
        self._winget_lbl.setProperty("cssClass", "hint")
        top.addWidget(self._winget_lbl)
        top.addStretch()

        btn_all = QPushButton("全 选")
        btn_all.setProperty("cssClass", "secondary")
        btn_all.setFixedWidth(60)
        btn_all.clicked.connect(lambda: self._set_all(True))
        top.addWidget(btn_all)

        btn_none = QPushButton("取消全选")
        btn_none.setProperty("cssClass", "secondary")
        btn_none.setFixedWidth(72)
        btn_none.clicked.connect(lambda: self._set_all(False))
        top.addWidget(btn_none)
        lay.addLayout(top)

        # 应用网格
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_content = QWidget()
        scroll_lay = QVBoxLayout(scroll_content)
        scroll_lay.setContentsMargins(0, 0, 0, 0)
        scroll_lay.setSpacing(0)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(2)

        apps = self._config.get("apps", [])
        for i, app in enumerate(apps):
            icon = get_icon(app["winget_id"], app.get("category", ""), 18)
            card = _AppCard(app, icon)
            card.cancel_requested.connect(self._cancel_one)
            self._app_cards[app["winget_id"]] = card
            r, c = divmod(i, COLS)
            grid.addWidget(card, r, c)

        for c in range(COLS):
            grid.setColumnStretch(c, 1)

        scroll_lay.addWidget(grid_w)
        scroll_lay.addStretch()
        scroll.setWidget(scroll_content)
        lay.addWidget(scroll, 1)

        # 分隔线
        sep = QFrame()
        sep.setProperty("cssClass", "separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        # 底栏
        bot = QHBoxLayout()
        self._cancel_btn = QPushButton("  取消安装")
        self._cancel_btn.setProperty("cssClass", "danger-outline")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel)
        bot.addWidget(self._cancel_btn)
        bot.addStretch()

        self._install_btn = QPushButton("  安装选中应用")
        self._install_btn.setProperty("cssClass", "success")
        self._install_btn.clicked.connect(self._run)
        bot.addWidget(self._install_btn)
        lay.addLayout(bot)

    def _check_winget(self):
        self._winget_thread = _WingetCheckThread()
        self._winget_thread.result.connect(self._on_winget_result)
        self._winget_thread.start()

    @Slot(bool)
    def _on_winget_result(self, ok: bool):
        text = "  winget 可用" if ok else "  winget 不可用，将下载安装"
        color = "#19BE6B" if ok else "#FF9900"
        self._winget_lbl.setText(text)
        self._winget_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")

    def _set_all(self, checked: bool):
        for card in self._app_cards.values():
            card.cb.setChecked(checked)

    def _reset_cards(self):
        for card in self._app_cards.values():
            card.reset()

    def _run(self, skip_confirm=False):
        sel = [c.app for c in self._app_cards.values() if c.cb.isChecked()]
        if not sel:
            if not skip_confirm:
                QMessageBox.warning(self, "提示", "请至少选择一个应用")
            return
        if not skip_confirm:
            if QMessageBox.question(self, "确认", f"安装 {len(sel)} 个应用？") != QMessageBox.StandardButton.Yes:
                return

        self._install_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._reset_cards()
        self._log.reset()
        self._log.append("══ 开始安装应用 ══")

        self._worker = InstallWorker(sel)
        self._worker.log.connect(self._log.append)
        self._worker.progress.connect(self._log.set_progress)
        self._worker.app_status.connect(self._on_app_status)
        self._worker.app_progress.connect(self._on_app_progress)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
            self._log.append("  用户取消全部安装...")

    @Slot(str)
    def _cancel_one(self, winget_id: str):
        if self._worker:
            self._worker.cancel_app(winget_id)
            card = self._app_cards.get(winget_id)
            if card:
                card.cancel_btn.hide()

    @Slot(str, str, str)
    def _on_app_status(self, winget_id: str, text: str, color: str):
        card = self._app_cards.get(winget_id)
        if card:
            card.set_status(text, color)

    @Slot(str, int)
    def _on_app_progress(self, winget_id: str, pct: int):
        card = self._app_cards.get(winget_id)
        if card:
            card.set_progress(pct)

    def _on_done(self, ok: int, fail: int):
        self._install_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._log.set_finished(ok, fail)
        from ui import notify
        notify("应用安装完成", f"成功 {ok} 个，失败 {fail} 个")
