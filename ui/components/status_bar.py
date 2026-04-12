"""
底部状态栏组件 — 多模块进度条 + 日志弹窗
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QDialog, QPlainTextEdit,
    QTabWidget,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve


class _SmoothProgressBar(QProgressBar):
    """进度条平滑过渡动画"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def smooth_set(self, value: int):
        self._anim.stop()
        self._anim.setStartValue(self.value())
        self._anim.setEndValue(value)
        self._anim.start()


# ─────────────────── 日志弹窗 ───────────────────


class LogDialog(QDialog):
    """按模块分 Tab 的实时日志弹窗"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("执行日志")
        self.resize(560, 380)
        self.setMinimumSize(360, 260)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E4E7ED;
                border-radius: 4px;
                background: #FAFAFA;
            }
            QTabBar::tab {
                padding: 4px 14px;
                font-size: 12px;
                border: none;
                border-bottom: 2px solid transparent;
                color: #909399;
                background: transparent;
                min-width: 0; min-height: 0;
            }
            QTabBar::tab:selected {
                color: #2D8CF0;
                border-bottom: 2px solid #2D8CF0;
            }
            QTabBar::tab:hover {
                color: #409EFF;
            }
        """)
        lay.addWidget(self._tabs, 1)

        self._module_texts: dict[str, QPlainTextEdit] = {}

        bot = QHBoxLayout()
        bot.addStretch()
        clear_btn = QPushButton("清空当前")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #DCDFE6;
                border-radius: 3px; font-size: 11px; color: #606266;
                padding: 3px 10px; min-width: 0; min-height: 0;
            }
            QPushButton:hover { border-color: #2D8CF0; color: #2D8CF0; }
        """)
        clear_btn.clicked.connect(self._clear_current)
        bot.addWidget(clear_btn)
        lay.addLayout(bot)

    def _ensure_tab(self, module: str) -> QPlainTextEdit:
        if module not in self._module_texts:
            text = QPlainTextEdit()
            text.setReadOnly(True)
            text.setStyleSheet("""
                QPlainTextEdit {
                    background: #1E1E2E;
                    color: #CDD6F4;
                    border: none;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: 12px;
                    padding: 6px;
                }
            """)
            self._module_texts[module] = text
            self._tabs.addTab(text, module)
        return self._module_texts[module]

    def append(self, module: str, text: str):
        w = self._ensure_tab(module)
        w.appendPlainText(text)

    def set_module_logs(self, module: str, logs: list[str]):
        w = self._ensure_tab(module)
        w.setPlainText("\n".join(logs))
        sb = w.verticalScrollBar()
        sb.setValue(sb.maximum())

    def focus_module(self, module: str):
        if module in self._module_texts:
            self._tabs.setCurrentWidget(self._module_texts[module])

    def _clear_current(self):
        w = self._tabs.currentWidget()
        if isinstance(w, QPlainTextEdit):
            w.clear()


# ─────────────────── 单模块进度行 ───────────────────


class _ModuleRow(QWidget):
    """一个模块的进度展示行: 单行紧凑 — 模块名 + 状态 + 进度条 + 百分比"""

    def __init__(self, module_name: str, parent=None):
        super().__init__(parent)
        self._name = module_name
        self.setFixedHeight(22)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        name_lbl = QLabel(f"【{module_name}】")
        name_lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
        name_lbl.setFixedWidth(64)
        lay.addWidget(name_lbl)

        self._status_lbl = QLabel("准备中…")
        self._status_lbl.setStyleSheet("font-size: 11px; color: #666;")
        self._status_lbl.setFixedWidth(180)
        lay.addWidget(self._status_lbl)

        self._progress = _SmoothProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        lay.addWidget(self._progress, 1)

        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setStyleSheet("font-size: 11px; color: #666;")
        self._pct_lbl.setFixedWidth(30)
        self._pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self._pct_lbl)

    def set_progress(self, value: int, status: str = ""):
        self._progress.smooth_set(value)
        self._pct_lbl.setText(f"{value}%")
        if status:
            self._status_lbl.setText(status)
            self._status_lbl.setStyleSheet("font-size: 12px; color: #666;")

    def set_action(self, text: str):
        """显示当前执行的操作"""
        # 截取干净的文字，去掉前缀符号
        clean = text.strip().lstrip("═ ●▸▹►✔✗·")
        if clean:
            # 限制长度避免溢出
            if len(clean) > 40:
                clean = clean[:40] + "…"
            self._status_lbl.setText(clean)
            self._status_lbl.setStyleSheet("font-size: 12px; color: #666;")

    def set_finished(self, ok: int, fail: int):
        self._progress.smooth_set(100)
        self._pct_lbl.setText("100%")
        if fail == 0:
            self._status_lbl.setText(f"✔ 全部成功 ({ok}项)")
            self._status_lbl.setStyleSheet("font-size: 12px; color: #19BE6B;")
        else:
            self._status_lbl.setText(f"完成: 成功{ok} 失败{fail}")
            self._status_lbl.setStyleSheet("font-size: 12px; color: #ED4014;")

    def reset(self):
        self._progress.setValue(0)
        self._pct_lbl.setText("0%")
        self._status_lbl.setText("准备中…")


# ─────────────────── 底部状态栏 ───────────────────


class BottomStatusBar(QWidget):
    """固定在窗口底部的状态栏: 多模块进度条 + 日志按钮"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._module_logs: dict[str, list[str]] = {}  # 按模块存储日志
        self._log_dialog: LogDialog | None = None
        self._module_rows: dict[str, _ModuleRow] = {}
        self._build()

    def _build(self):
        self.setObjectName("BottomStatusBar")

        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(12, 4, 12, 4)
        main_lay.setSpacing(8)

        # 左侧: 模块进度行容器
        self._rows_container = QWidget()
        self._rows_lay = QVBoxLayout(self._rows_container)
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(2)

        self._idle_lbl = QLabel("就绪")
        self._idle_lbl.setStyleSheet("color: #999; font-size: 12px;")
        self._rows_lay.addWidget(self._idle_lbl)

        main_lay.addWidget(self._rows_container, 1)

        # 右侧: 日志按钮
        log_btn = QPushButton("日志")
        log_btn.setToolTip("查看执行日志")
        log_btn.setFixedHeight(24)
        log_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #DCDFE6;
                border-radius: 3px;
                font-size: 11px;
                color: #606266;
                padding: 2px 10px;
                min-width: 0;
                min-height: 0;
            }
            QPushButton:hover {
                background: rgba(45, 140, 240, 0.08);
                border-color: #2D8CF0;
                color: #2D8CF0;
            }
        """)
        log_btn.clicked.connect(self._show_log_dialog)
        main_lay.addWidget(log_btn, 0, Qt.AlignVCenter)

    # ── 模块行管理 ──

    def _ensure_module_row(self, name: str) -> _ModuleRow:
        if name not in self._module_rows:
            self._idle_lbl.hide()
            row = _ModuleRow(name, self._rows_container)
            self._module_rows[name] = row
            self._rows_lay.addWidget(row)
        return self._module_rows[name]

    def _check_idle(self):
        if not self._module_rows:
            self._idle_lbl.show()

    def set_module_progress(self, module: str, value: int, status: str = ""):
        row = self._ensure_module_row(module)
        row.set_progress(value, status)

    def set_module_finished(self, module: str, ok: int, fail: int):
        row = self._ensure_module_row(module)
        row.set_finished(ok, fail)

    def set_module_action(self, module: str, text: str):
        row = self._ensure_module_row(module)
        row.set_action(text)

    def reset_module(self, module: str):
        """重置模块行（若已存在则归零，否则新建）"""
        row = self._ensure_module_row(module)
        row.reset()

    def remove_module(self, module: str):
        if module in self._module_rows:
            row = self._module_rows.pop(module)
            self._rows_lay.removeWidget(row)
            row.deleteLater()
            self._check_idle()

    # ── 日志 ──

    def append_log(self, module: str, text: str):
        self._module_logs.setdefault(module, []).append(text)
        # 更新状态栏显示最新操作
        self.set_module_action(module, text)
        if self._log_dialog and self._log_dialog.isVisible():
            self._log_dialog.append(module, text)

    def clear_module_logs(self, module: str):
        self._module_logs.pop(module, None)

    def _show_log_dialog(self):
        if self._log_dialog is None:
            self._log_dialog = LogDialog(self.window())
            self._log_dialog.setStyleSheet(self.window().styleSheet())
        # 加载所有模块的已有日志
        for mod, logs in self._module_logs.items():
            self._log_dialog.set_module_logs(mod, logs)
        self._log_dialog.show()
        self._log_dialog.raise_()
        self._log_dialog.activateWindow()


# ─────────────────── 模块日志代理 ───────────────────


class ModuleLog:
    """
    LogPanel 的直接替代品 — 每个模块一个实例。
    保持与 LogPanel 完全相同的公开 API:
        append(str), set_progress(int, str), reset(), clear()
    """

    def __init__(self, status_bar: BottomStatusBar, module_name: str):
        self._bar = status_bar
        self._name = module_name

    def append(self, text: str):
        self._bar.append_log(self._name, text)

    def set_progress(self, value: int, status: str = ""):
        self._bar.set_module_progress(self._name, value, status)

    def set_finished(self, ok: int, fail: int):
        self._bar.set_module_finished(self._name, ok, fail)

    def reset(self):
        self._bar.reset_module(self._name)

    def clear(self):
        self._bar.clear_module_logs(self._name)
