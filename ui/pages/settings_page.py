"""
系统设置页 — 常规设置 + 高级设置 (刷新率/DNS/保存位置)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QLineEdit, QComboBox, QPushButton, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, Slot, QThread

from ui.components.check_group import CheckGroup
from ui.workers.settings_worker import SettingsWorker
from system_settings import get_available_refresh_rates


class _RateDetectThread(QThread):
    result = Signal(list)

    def run(self):
        rates = get_available_refresh_rates()
        self.result.emit([str(r) for r in rates])


class SettingsPage(QWidget):

    def __init__(self, config_data: dict, log_panel, parent=None):
        super().__init__(parent)
        self._log = log_panel
        self._config = config_data
        self._worker: SettingsWorker | None = None
        self._build()
        self._detect_rates()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)

        simple = [s for s in self._config.get("settings", []) if not s.get("requires_input")]
        extra  = [s for s in self._config.get("settings", []) if s.get("requires_input")]

        # 常规设置
        self._check_group = CheckGroup("常规设置", columns=4)
        for s in simple:
            self._check_group.add_item(s["key"], s["name"])
        lay.addWidget(self._check_group)

        # 高级设置
        if extra:
            sep = QFrame()
            sep.setProperty("cssClass", "separator")
            sep.setFrameShape(QFrame.Shape.HLine)
            lay.addWidget(sep)

            lbl = QLabel("高级设置")
            lbl.setProperty("cssClass", "section-title")
            lay.addWidget(lbl)

            self._extra_checks: dict[str, tuple] = {}
            for s in extra:
                row, cb = self._build_extra_row(s)
                self._extra_checks[s["key"]] = cb
                lay.addLayout(row)

        lay.addStretch()

        # 执行按钮
        bot = QHBoxLayout()
        bot.addStretch()
        self._run_btn = QPushButton("  执行系统设置")
        self._run_btn.clicked.connect(self._run)
        bot.addWidget(self._run_btn)
        lay.addLayout(bot)

    def _build_extra_row(self, setting: dict):
        from PySide6.QtWidgets import QCheckBox, QSpinBox
        row = QHBoxLayout()
        row.setSpacing(8)

        cb = QCheckBox(setting["name"])
        cb.setChecked(True)
        row.addWidget(cb)

        t = setting["input_type"]
        widget = None

        if t == "folder":
            self._save_loc = QLineEdit("D:\\")
            self._save_loc.setFixedWidth(200)
            row.addWidget(self._save_loc)
            browse_btn = QPushButton("浏览")
            browse_btn.setProperty("cssClass", "secondary")
            browse_btn.setFixedWidth(50)
            browse_btn.clicked.connect(self._browse_folder)
            row.addWidget(browse_btn)
            widget = self._save_loc

            # 文件夹选择复选框（桌面/文档/下载等）
            self._folder_checks: dict[str, QCheckBox] = {}
            folder_names = {
                "Desktop": "桌面", "Documents": "文档", "Downloads": "下载",
                "Music": "音乐", "Pictures": "图片", "Videos": "视频",
            }
            row.addWidget(QLabel("  迁移:"))
            for fkey, fname in folder_names.items():
                fcb = QCheckBox(fname)
                fcb.setChecked(fkey != "Desktop")
                self._folder_checks[fkey] = fcb
                row.addWidget(fcb)

        elif t == "refresh_rate":
            self._rate_combo = QComboBox()
            self._rate_combo.setFixedWidth(100)
            self._rate_combo.addItem("检测中...")
            row.addWidget(self._rate_combo)
            row.addWidget(QLabel("Hz"))
            detect_btn = QPushButton("检测")
            detect_btn.setProperty("cssClass", "secondary")
            detect_btn.setFixedWidth(50)
            detect_btn.clicked.connect(self._detect_rates)
            row.addWidget(detect_btn)
            widget = self._rate_combo

        elif t == "dns":
            row.addWidget(QLabel("首选:"))
            self._dns1 = QLineEdit("114.114.114.114")
            self._dns1.setFixedWidth(140)
            row.addWidget(self._dns1)
            row.addWidget(QLabel("备用:"))
            self._dns2 = QLineEdit("223.5.5.5")
            self._dns2.setFixedWidth(140)
            row.addWidget(self._dns2)
            widget = (self._dns1, self._dns2)

        elif t == "taskbar_alignment":
            self._taskbar_combo = QComboBox()
            self._taskbar_combo.setFixedWidth(100)
            self._taskbar_combo.addItems(["居左", "居中"])
            row.addWidget(self._taskbar_combo)
            widget = self._taskbar_combo

        elif t == "screen_timeout":
            self._timeout_spin = QSpinBox()
            self._timeout_spin.setRange(0, 120)
            self._timeout_spin.setValue(0)
            self._timeout_spin.setSpecialValueText("永不")
            self._timeout_spin.setFixedWidth(80)
            row.addWidget(self._timeout_spin)
            row.addWidget(QLabel("分钟"))
            widget = self._timeout_spin

        elif t == "computer_name":
            import socket
            self._comp_name = QLineEdit(socket.gethostname())
            self._comp_name.setFixedWidth(200)
            row.addWidget(self._comp_name)
            widget = self._comp_name

        row.addStretch()
        return row, cb

    def _browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存位置")
        if d:
            self._save_loc.setText(d)

    def _detect_rates(self):
        self._rate_thread = _RateDetectThread()
        self._rate_thread.result.connect(self._on_rates_ready)
        self._rate_thread.start()

    @Slot(list)
    def _on_rates_ready(self, strs: list):
        if hasattr(self, "_rate_combo") and strs:
            self._rate_combo.clear()
            self._rate_combo.addItems(strs)
            self._rate_combo.setCurrentIndex(len(strs) - 1)

    def _run(self, skip_confirm=False):
        keys = self._check_group.selected_keys()
        if hasattr(self, "_extra_checks"):
            for k, cb in self._extra_checks.items():
                if cb.isChecked():
                    keys.append(k)

        if not keys:
            if not skip_confirm:
                QMessageBox.warning(self, "提示", "请至少选择一项")
            return
        if not skip_confirm:
            if QMessageBox.question(self, "确认", f"执行 {len(keys)} 项系统设置？") != QMessageBox.StandardButton.Yes:
                return

        self._run_btn.setEnabled(False)
        self._log.reset()
        self._log.append("══ 开始系统设置 ══")

        self._worker = SettingsWorker(
            keys,
            save_location=getattr(self, "_save_loc", QLineEdit()).text(),
            save_folders=[k for k, cb in getattr(self, "_folder_checks", {}).items() if cb.isChecked()] or None,
            refresh_rate=getattr(self, "_rate_combo", QComboBox()).currentText(),
            primary_dns=getattr(self, "_dns1", QLineEdit()).text(),
            secondary_dns=getattr(self, "_dns2", QLineEdit()).text(),
            taskbar_alignment="left" if getattr(self, "_taskbar_combo", QComboBox()).currentIndex() == 0 else "center",
            screen_timeout=getattr(self, "_timeout_spin", None).value() if hasattr(self, "_timeout_spin") else 15,
            computer_name=getattr(self, "_comp_name", QLineEdit()).text(),
        )
        self._worker.log.connect(self._log.append)
        self._worker.progress.connect(self._log.set_progress)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_done(self, ok: int, fail: int):
        self._run_btn.setEnabled(True)
        self._log.set_finished(ok, fail)
