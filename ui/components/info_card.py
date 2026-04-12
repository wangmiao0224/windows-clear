"""
信息卡片组件 — 用于性能监控的小型数据展示卡
"""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt

from ui.theme import TEXT_SECONDARY


class InfoCard(QGroupBox):
    """
    带标题的信息卡片, 内含 key-value 行

    使用:
        card = InfoCard("CPU")
        card.add_row("型号:", "cpu_name")
        card.add_row("频率:", "cpu_freq")
        card.update_value("cpu_name", "Intel i7-9700K")
    """

    def __init__(self, title: str, parent=None):
        super().__init__(f"  {title}", parent)
        self._labels: dict[str, QLabel] = {}
        self._bars: dict[str, QProgressBar] = {}
        self._lay = QVBoxLayout(self)
        self._lay.setSpacing(4)
        self._lay.setContentsMargins(10, 8, 10, 8)

    def add_row(self, label: str, key: str, default: str = "加载中...") -> QLabel:
        row = QHBoxLayout()
        row.setSpacing(4)

        name_lbl = QLabel(label)
        name_lbl.setFixedWidth(48)
        name_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        row.addWidget(name_lbl)

        val_lbl = QLabel(default)
        val_lbl.setStyleSheet("font-size: 12px;")
        row.addWidget(val_lbl, 1)

        self._labels[key] = val_lbl
        self._lay.addLayout(row)
        return val_lbl

    def add_progress(self, key: str, color: str = "") -> QProgressBar:
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setTextVisible(False)
        bar.setFixedHeight(6)
        if color:
            bar.setStyleSheet(
                f"QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}"
            )
        self._bars[key] = bar
        self._lay.addWidget(bar)
        return bar

    def update_value(self, key: str, text: str):
        lbl = self._labels.get(key)
        if lbl:
            lbl.setText(text)

    def update_progress(self, key: str, value: int):
        bar = self._bars.get(key)
        if bar:
            bar.setValue(value)
