"""
图标辅助 — 使用 QPainter 生成应用图标 (Qt 原生, 无需 PIL)
"""

from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QBrush, QPen, QIcon
from PySide6.QtCore import Qt, QRect

# ── 品牌色 ──
APP_COLORS: dict[str, str] = {
    "Google.Chrome": "#4285F4",
    "Mozilla.Firefox": "#FF7139",
    "Microsoft.Edge": "#0078D7",
    "Tencent.WeChat": "#07C160",
    "Tencent.QQ": "#12B7F5",
    "Tencent.QQMusic": "#31C27C",
    "Alibaba.DingDing": "#3072F6",
    "ByteDance.Feishu": "#3370FF",
    "Valve.Steam": "#1B2838",
    "7zip.7zip": "#E40000",
    "Kingsoft.WPSOffice": "#D4372C",
    "VideoLAN.VLC": "#FF8800",
    "Notepad++.Notepad++": "#90E59A",
    "vscode": "#007ACC",
    "Git.Git": "#F05032",
    "Python.Python.3": "#3776AB",
    "Oracle.JDK.17": "#ED8B00",
    "Huorong.Sysdiag": "#5BB448",
}

# ── 首字母 ──
APP_INITIALS: dict[str, str] = {
    "Google.Chrome": "C",
    "Mozilla.Firefox": "Fx",
    "Tencent.WeChat": "微",
    "Tencent.QQ": "Q",
    "Alibaba.DingDing": "钉",
    "ByteDance.Feishu": "飞",
    "Kingsoft.WPSOffice": "W",
    "Valve.Steam": "S",
    "Huorong.Sysdiag": "火",
}

# ── 分类色 ──
CATEGORY_COLORS: dict[str, str] = {
    "浏览器": "#4A90D9",
    "社交": "#07C160",
    "安全工具": "#E6522C",
    "办公": "#FF6A00",
    "工具": "#8E44AD",
    "娱乐": "#E74C3C",
    "游戏": "#2C3E50",
}

_cache: dict[str, QPixmap] = {}


def get_icon_pixmap(winget_id: str, category: str = "", size: int = 18) -> QPixmap:
    """获取应用图标 QPixmap (带缓存)"""
    key = f"{winget_id}_{size}"
    if key in _cache:
        return _cache[key]
    pm = _generate(winget_id, category, size)
    _cache[key] = pm
    return pm


def get_icon(winget_id: str, category: str = "", size: int = 18) -> QIcon:
    """获取应用图标 QIcon"""
    return QIcon(get_icon_pixmap(winget_id, category, size))


def _generate(winget_id: str, category: str, size: int) -> QPixmap:
    color_hex = APP_COLORS.get(winget_id) or CATEGORY_COLORS.get(category, "#5B6B7F")
    initial = APP_INITIALS.get(winget_id, winget_id.split(".")[-1][:2])

    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.setBrush(QBrush(QColor(color_hex)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, size, size, size * 0.22, size * 0.22)

    p.setPen(QColor("#FFFFFF"))
    font = QFont("Microsoft YaHei UI", max(size // 3, 6))
    font.setBold(True)
    p.setFont(font)
    p.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, initial)

    p.end()
    return pm
