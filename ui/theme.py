"""
主题与样式 — 腾讯管家风格 QSS
"""

# ──────────────── 色板 ────────────────

PRIMARY    = "#2D8CF0"
PRIMARY_LT = "#57A3F3"
PRIMARY_DK = "#2070C8"

SUCCESS    = "#19BE6B"
WARNING    = "#FF9900"
DANGER     = "#ED4014"
INFO       = "#2DB7F5"

BG_PAGE    = "#F0F2F5"
BG_CARD    = "#FFFFFF"
BG_HEADER  = "#FFFFFF"
BG_SIDEBAR = "#FAFBFC"

TEXT_PRIMARY   = "#333333"
TEXT_SECONDARY = "#999999"
TEXT_TITLE     = "#1A1A1A"

BORDER     = "#E4E7ED"
BORDER_LT  = "#EBEEF5"
SHADOW     = "rgba(0,0,0,0.06)"

# ──────────────── 字体 ────────────────

FONT_FAMILY = "Microsoft YaHei UI"
FONT_MONO   = "Consolas"

# ── 勾选图标路径 ──
import os as _os
_CHECK_SVG = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "check.svg").replace("\\", "/")

# ──────────────── QSS ────────────────

QSS = f"""
/* ─── 全局 ─── */
QWidget {{
    font-family: "{FONT_FAMILY}";
    font-size: 12px;
    color: {TEXT_PRIMARY};
}}

QMainWindow {{
    background: {BG_PAGE};
}}

/* ─── 顶栏 ─── */
#HeaderBar {{
    background: {BG_HEADER};
    border-bottom: 1px solid {BORDER};
}}

/* ─── Tab 栏 ─── */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar {{
    background: {BG_HEADER};
    border-bottom: 2px solid {BORDER_LT};
    qproperty-drawBase: 0;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_SECONDARY};
    padding: 5px 14px;
    margin: 0 1px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    min-width: 48px;
}}
QTabBar::tab:hover {{
    color: {PRIMARY};
    background: rgba(45, 140, 240, 0.04);
}}
QTabBar::tab:selected {{
    color: {PRIMARY};
    font-weight: bold;
    border-bottom: 2px solid {PRIMARY};
    background: rgba(45, 140, 240, 0.06);
}}

/* ─── 按钮 ─── */
QPushButton {{
    background: {PRIMARY};
    color: white;
    border: none;
    border-radius: 3px;
    padding: 4px 10px;
    font-size: 12px;
    min-width: 52px;
    min-height: 22px;
}}
QPushButton:hover {{
    background: {PRIMARY_LT};
}}
QPushButton:pressed {{
    background: {PRIMARY_DK};
}}
QPushButton:disabled {{
    background: #C5C8CE;
    color: #F0F0F0;
}}

/* 次要按钮 */
QPushButton[cssClass="secondary"] {{
    background: transparent;
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
}}
QPushButton[cssClass="secondary"]:hover {{
    color: {PRIMARY};
    border-color: {PRIMARY};
    background: rgba(45, 140, 240, 0.04);
}}

/* 成功 */
QPushButton[cssClass="success"] {{
    background: {SUCCESS};
}}
QPushButton[cssClass="success"]:hover {{
    background: #47CB89;
}}

/* 危险 */
QPushButton[cssClass="danger"] {{
    background: {DANGER};
}}
QPushButton[cssClass="danger"]:hover {{
    background: #F16643;
}}
QPushButton[cssClass="danger-outline"] {{
    background: transparent;
    color: {DANGER};
    border: 1px solid {DANGER};
}}
QPushButton[cssClass="danger-outline"]:hover {{
    background: {DANGER};
    color: white;
}}

/* 警告 */
QPushButton[cssClass="warning"] {{
    background: {WARNING};
}}
QPushButton[cssClass="warning"]:hover {{
    background: #FFB340;
}}
QPushButton[cssClass="warning-outline"] {{
    background: transparent;
    color: {WARNING};
    border: 1px solid {WARNING};
}}
QPushButton[cssClass="warning-outline"]:hover {{
    background: {WARNING};
    color: white;
}}

/* 信息 / link 样式 */
QPushButton[cssClass="link"] {{
    background: transparent;
    color: {PRIMARY};
    border: none;
    padding: 4px 8px;
    min-width: 0;
    min-height: 0;
}}
QPushButton[cssClass="link"]:hover {{
    text-decoration: underline;
}}

/* ─── 卡片容器 ─── */
QFrame[cssClass="card"] {{
    background: {BG_CARD};
    border: 1px solid {BORDER_LT};
    border-radius: 8px;
}}
QFrame[cssClass="card"]:hover {{
    border-color: {PRIMARY_LT};
    background: #FAFCFF;
}}

/* ─── 输入框 ─── */
QLineEdit, QComboBox {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 3px 8px;
    font-size: 12px;
    color: {TEXT_PRIMARY};
    min-height: 20px;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_SECONDARY};
    margin-right: 6px;
}}

/* ─── 复选框 ─── */
QCheckBox {{
    spacing: 4px;
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid #C0C4CC;
    border-radius: 3px;
    background: white;
}}
QCheckBox::indicator:hover {{
    border-color: {PRIMARY};
}}
QCheckBox::indicator:checked {{
    background: {PRIMARY};
    border-color: {PRIMARY};
    image: url({_CHECK_SVG});
}}

/* ─── 进度条 ─── */
QProgressBar {{
    background: {BORDER_LT};
    border: none;
    border-radius: 4px;
    min-height: 8px;
    max-height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PRIMARY_DK}, stop:0.4 {PRIMARY},
        stop:0.6 {PRIMARY_LT}, stop:1 {PRIMARY});
    border-radius: 4px;
}}

/* ─── 滚动区域 ─── */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #D0D3D9;
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #A0A4AA;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

/* ─── 日志面板 ─── */
QPlainTextEdit[cssClass="log"] {{
    background: #F7F8FA;
    border: 1px solid {BORDER_LT};
    border-radius: 6px;
    font-family: "{FONT_MONO}";
    font-size: 12px;
    color: {TEXT_PRIMARY};
    padding: 6px;
    selection-background-color: #D6EAFF;
}}

/* ─── 分隔线 ─── */
QFrame[cssClass="separator"] {{
    background: {BORDER_LT};
    max-height: 1px;
    min-height: 1px;
}}

/* ─── 标签 ─── */
QLabel[cssClass="section-title"] {{
    font-size: 13px;
    font-weight: bold;
    color: {TEXT_TITLE};
}}
QLabel[cssClass="hint"] {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}
QLabel[cssClass="success"] {{
    color: {SUCCESS};
    font-size: 12px;
}}
QLabel[cssClass="warning"] {{
    color: {WARNING};
    font-size: 12px;
}}
QLabel[cssClass="danger"] {{
    color: {DANGER};
    font-size: 12px;
}}

/* ─── GroupBox (监控卡片) ─── */
QGroupBox {{
    background: {BG_CARD};
    border: 1px solid {BORDER_LT};
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
    font-size: 13px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    color: {PRIMARY};
}}

/* ─── 底部状态栏 ─── */
#BottomStatusBar {{
    background: {BG_CARD};
    border-top: 1px solid {BORDER};
}}
"""
