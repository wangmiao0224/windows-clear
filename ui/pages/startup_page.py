"""
开机自启管理页 — 扫描/启用/禁用/删除 注册表自启动项
"""

import winreg
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt, Slot

from ui.workers.startup_worker import StartupScanWorker, hive_to_handle
from ui.theme import SUCCESS, DANGER, TEXT_SECONDARY


class StartupPage(QWidget):

    def __init__(self, log_panel, parent=None):
        super().__init__(parent)
        self._log = log_panel
        self._items: list[dict] = []
        self._scan_worker: StartupScanWorker | None = None
        self._build()
        # 延迟自动扫描
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self.scan)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("开机自启动项管理")
        title.setProperty("cssClass", "section-title")
        hdr.addWidget(title)
        hdr.addStretch()
        self._refresh_btn = QPushButton("刷新列表")
        self._refresh_btn.setProperty("cssClass", "secondary")
        self._refresh_btn.clicked.connect(self.scan)
        hdr.addWidget(self._refresh_btn)
        lay.addLayout(hdr)

        # 滚动列表
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._container = QWidget()
        self._list_lay = QVBoxLayout(self._container)
        self._list_lay.setContentsMargins(4, 4, 4, 4)
        self._list_lay.setSpacing(4)
        self._list_lay.addWidget(QLabel("点击「刷新列表」扫描开机自启项"))
        self._list_lay.addStretch()
        self._scroll.setWidget(self._container)
        lay.addWidget(self._scroll, 1)

    def scan(self):
        self._refresh_btn.setEnabled(False)
        self._clear_list()
        self._list_lay.addWidget(QLabel("正在扫描..."))
        self._scan_worker = StartupScanWorker()
        self._scan_worker.items_ready.connect(self._show_items)
        self._scan_worker.start()

    @Slot(list)
    def _show_items(self, items: list[dict]):
        self._clear_list()
        self._items = items

        if not items:
            self._list_lay.addWidget(QLabel("未发现开机自启项"))
            self._refresh_btn.setEnabled(True)
            return

        summary = QLabel(f"共发现 {len(items)} 个开机自启项")
        summary.setProperty("cssClass", "success")
        self._list_lay.addWidget(summary)

        for item in items:
            row = self._build_item_row(item)
            self._list_lay.addWidget(row)

        self._list_lay.addStretch()
        self._refresh_btn.setEnabled(True)

    def _build_item_row(self, item: dict) -> QFrame:
        frame = QFrame()
        frame.setProperty("cssClass", "card")
        row = QHBoxLayout(frame)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(4)

        # 注册表位置
        loc = QLabel(f"[{item['label']}]")
        loc.setFixedWidth(56)
        loc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        row.addWidget(loc)

        # 名称
        name_lbl = QLabel(item["name"])
        name_lbl.setStyleSheet("font-weight: bold;")
        name_lbl.setFixedWidth(120)
        name_lbl.setToolTip(item["name"])
        row.addWidget(name_lbl)

        # 命令
        cmd_lbl = QLabel(item["command"][:50])
        cmd_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        cmd_lbl.setToolTip(item["command"])
        row.addWidget(cmd_lbl, 1)

        # 状态
        enabled = item["enabled"]
        status_text = "启用" if enabled else "禁用"
        status_color = SUCCESS if enabled else DANGER
        status_lbl = QLabel(status_text)
        status_lbl.setFixedWidth(36)
        status_lbl.setStyleSheet(f"color: {status_color}; font-size: 12px;")
        row.addWidget(status_lbl)

        # 删除按钮
        del_btn = QPushButton("删除")
        del_btn.setProperty("cssClass", "secondary")
        del_btn.setFixedWidth(40)
        del_btn.clicked.connect(lambda checked=False, it=item: self._delete_item(it))
        row.addWidget(del_btn)

        # 启用/禁用按钮
        if enabled:
            toggle_btn = QPushButton("禁用")
            toggle_btn.setProperty("cssClass", "danger-outline")
        else:
            toggle_btn = QPushButton("启用")
            toggle_btn.setProperty("cssClass", "success")
        toggle_btn.setFixedWidth(40)
        toggle_btn.clicked.connect(
            lambda checked=False, it=item, sl=status_lbl: self._toggle_item(it, not it["enabled"], sl)
        )
        row.addWidget(toggle_btn)

        return frame

    def _toggle_item(self, item: dict, enable: bool, status_label: QLabel):
        try:
            approved = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
            with winreg.OpenKey(hive_to_handle(item["root_str"]), approved, 0, winreg.KEY_SET_VALUE) as key:
                data = (b"\x02" if enable else b"\x03") + b"\x00" * 11
                winreg.SetValueEx(key, item["name"], 0, winreg.REG_BINARY, data)
            item["enabled"] = enable
            self._log.append(f"  已{'启用' if enable else '禁用'}: {item['name']}")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(300, self.scan)
        except Exception as e:
            self._log.append(f"  操作失败: {e}")

    def _delete_item(self, item: dict):
        if QMessageBox.question(
            self, "确认",
            f"确定删除自启项「{item['name']}」？\n{item['command']}",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            with winreg.OpenKey(hive_to_handle(item["root_str"]), item["subkey"], 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, item["name"])
            self._log.append(f"  已删除: {item['name']}")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(300, self.scan)
        except Exception as e:
            self._log.append(f"  删除失败: {e}")

    def _clear_list(self):
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
