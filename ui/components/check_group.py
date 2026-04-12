"""
复选框组组件 — 可复用的带标题 + 全选/取消全选 的复选框网格
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QCheckBox, QPushButton, QFrame,
)
from PySide6.QtCore import Qt


class CheckGroup(QWidget):
    """
    标题 + [全选] [取消全选] + 多列复选框网格

    使用:
        group = CheckGroup("常规设置", columns=4)
        group.add_item("key1", "显示文件扩展名")
        group.add_item("key2", "显示隐藏文件")
        selected = group.selected_keys()   # -> ["key1", ...]
    """

    def __init__(self, title: str = "", columns: int = 4,
                 show_buttons: bool = True, parent=None):
        super().__init__(parent)
        self._columns = columns
        self._checks: dict[str, QCheckBox] = {}
        self._row = 0
        self._col = 0

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(6)

        if title or show_buttons:
            hdr = QHBoxLayout()
            hdr.setSpacing(8)
            if title:
                lbl = QLabel(title)
                lbl.setProperty("cssClass", "section-title")
                hdr.addWidget(lbl)
            hdr.addStretch()
            if show_buttons:
                btn_all = QPushButton("全 选")
                btn_all.setProperty("cssClass", "secondary")
                btn_all.setFixedWidth(60)
                btn_all.clicked.connect(lambda: self.set_all(True))
                hdr.addWidget(btn_all)

                btn_none = QPushButton("取消全选")
                btn_none.setProperty("cssClass", "secondary")
                btn_none.setFixedWidth(72)
                btn_none.clicked.connect(lambda: self.set_all(False))
                hdr.addWidget(btn_none)
            self._lay.addLayout(hdr)

        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(16)
        self._grid.setVerticalSpacing(8)
        self._lay.addLayout(self._grid)

    # ── 公共 API ──

    def add_item(self, key: str, label: str, checked: bool = True,
                 icon=None, tooltip: str = ""):
        cb = QCheckBox(label)
        cb.setChecked(checked)
        if tooltip:
            cb.setToolTip(tooltip)
        if icon:
            cb.setIcon(icon)
        self._checks[key] = cb
        self._grid.addWidget(cb, self._row, self._col)
        self._col += 1
        if self._col >= self._columns:
            self._col = 0
            self._row += 1

    def selected_keys(self) -> list[str]:
        return [k for k, cb in self._checks.items() if cb.isChecked()]

    def set_all(self, checked: bool):
        for cb in self._checks.values():
            cb.setChecked(checked)

    def set_enabled(self, enabled: bool):
        for cb in self._checks.values():
            cb.setEnabled(enabled)

    def checkbox(self, key: str) -> QCheckBox | None:
        return self._checks.get(key)
