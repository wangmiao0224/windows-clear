"""
主窗口 — 顶栏 + Tabs + 右侧日志面板
"""

import json
import os
import platform
import socket
import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QFrame, QMessageBox, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

from ui.theme import QSS, PRIMARY, PRIMARY_LT, SUCCESS, WARNING, DANGER, TEXT_SECONDARY
from ui.components.status_bar import BottomStatusBar, ModuleLog
from ui.pages.settings_page import SettingsPage
from ui.pages.apps_page import AppsPage
from ui.pages.cleanup_page import CleanupPage
from ui.pages.monitor_page import MonitorPage
from ui.pages.startup_page import StartupPage
from system_settings import is_admin


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统优化工具-专业版")
        self.resize(780, 600)
        self.setMinimumSize(780, 470)
        self.setStyleSheet(QSS)

        self._config = self._load_config()
        self._build()

    # ── 配置加载 ──

    @staticmethod
    def _load_config() -> dict:
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        # config.json 在项目根目录，__file__ 在 ui/ 下
        for candidate in [
            os.path.join(base, "config.json"),
            os.path.join(os.path.dirname(base), "config.json"),
            os.path.join(os.getcwd(), "config.json"),
        ]:
            if os.path.isfile(candidate):
                with open(candidate, "r", encoding="utf-8") as f:
                    return json.load(f)
        QMessageBox.critical(None, "错误", "无法找到 config.json")
        return {"apps": [], "settings": []}

    # ── UI 构建 ──

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 顶栏
        root.addWidget(self._build_header())

        # 主体 (全宽 tabs)
        body = QHBoxLayout()
        body.setContentsMargins(8, 4, 8, 4)
        body.setSpacing(0)

        # 底部状态栏
        self._status_bar = BottomStatusBar()

        # 每个模块独立的日志/进度代理
        log_settings = ModuleLog(self._status_bar, "系统设置")
        log_apps     = ModuleLog(self._status_bar, "应用安装")
        log_cleanup  = ModuleLog(self._status_bar, "系统修复")
        log_startup  = ModuleLog(self._status_bar, "自启管理")

        self._tabs = QTabWidget()
        self._tabs.addTab(SettingsPage(self._config, log_settings), "  系统设置  ")
        self._tabs.addTab(AppsPage(self._config, log_apps), "  应用安装  ")
        self._tabs.addTab(CleanupPage(log_cleanup), "  系统修复  ")
        self._tabs.addTab(MonitorPage(), "  性能监控  ")
        self._tabs.addTab(StartupPage(log_startup), "  开机自启管理  ")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        body.addWidget(self._tabs, 1)

        root.addLayout(body, 1)

        # 底部状态栏固定在最下方
        root.addWidget(self._status_bar)

    def _on_tab_changed(self, index: int):
        widget = self._tabs.widget(index)
        if widget:
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
            effect.setOpacity(0.0)
            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            # 动画结束后移除 effect，避免渲染问题
            anim.finished.connect(lambda w=widget: w.setGraphicsEffect(None))
            anim.start()
            self._fade_anim = anim  # prevent GC

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(36)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(16)

        # 系统信息组
        pc_name = socket.gethostname()
        os_ver = platform.version()
        os_edition = platform.system() + " " + platform.release()

        info_items = [
            ("计算机", pc_name),
            ("系统", f"{os_edition}  (Build {os_ver})"),
        ]
        for label, value in info_items:
            pair = QHBoxLayout()
            pair.setSpacing(4)
            lk = QLabel(label)
            lk.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            lv = QLabel(value)
            lv.setStyleSheet("font-size: 12px; font-weight: 500;")
            pair.addWidget(lk)
            pair.addWidget(lv)
            lay.addLayout(pair)

        lay.addStretch()

        # 一键优化按钮
        oneclick = QPushButton("⚡ 一键优化")
        oneclick.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {PRIMARY}, stop:1 #19BE6B);
                color: white; border: none; border-radius: 3px;
                padding: 3px 14px; font-size: 12px; font-weight: bold;
                min-width: 0; min-height: 0;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {PRIMARY_LT}, stop:1 #47CB89);
            }}
        """)
        oneclick.clicked.connect(self._one_click_optimize)
        lay.addWidget(oneclick)

        # 管理员状态 — 小圆点 + 文字
        admin_dot = QLabel("●")
        admin_txt = QLabel()
        if is_admin():
            admin_dot.setStyleSheet(f"color: {SUCCESS}; font-size: 10px;")
            admin_txt.setText("管理员")
            admin_txt.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
        else:
            admin_dot.setStyleSheet(f"color: {DANGER}; font-size: 10px;")
            admin_txt.setText("非管理员")
            admin_txt.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
        lay.addWidget(admin_dot)
        lay.addWidget(admin_txt)

        return header

    def _one_click_optimize(self):
        """一键执行: 系统设置 + 应用安装"""
        reply = QMessageBox.question(
            self, "一键优化",
            "将自动执行以下操作:\n"
            "1. 应用所有已勾选的系统设置\n"
            "2. 安装所有已勾选的应用\n\n"
            "确认继续？",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        # 触发系统设置页的执行
        settings_page = self._tabs.widget(0)
        if hasattr(settings_page, "_run"):
            settings_page._run(skip_confirm=True)
        # 触发应用安装页的执行
        apps_page = self._tabs.widget(1)
        if hasattr(apps_page, "_run"):
            apps_page._run(skip_confirm=True)
