"""
系统优化工具-专业版 - 入口文件 (PySide6)
功能：一键初始化 Windows 系统设置 + 自动安装常用应用
"""

import sys
import os
import ctypes


def request_admin():
    """请求管理员权限重新运行（如果当前不是管理员）"""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        is_admin = False

    if not is_admin:
        try:
            script = os.path.abspath(sys.argv[0])
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}"', None, 1
            )
            sys.exit(0)
        except Exception:
            pass


def main():
    request_admin()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from PySide6.QtWidgets import QApplication, QSplashScreen, QLabel
    from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon, QPen, QBrush, QPainterPath
    from PySide6.QtCore import Qt, QRectF

    app = QApplication(sys.argv)

    # ── 生成应用图标 ──
    def _make_app_icon():
        sizes = [16, 24, 32, 48, 64, 128, 256]
        icon = QIcon()
        for sz in sizes:
            pm = QPixmap(sz, sz)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)

            m = sz * 0.06  # margin
            r = QRectF(m, m, sz - 2 * m, sz - 2 * m)

            # 圆角矩形背景 — 蓝色渐变
            path = QPainterPath()
            path.addRoundedRect(r, sz * 0.18, sz * 0.18)
            p.setPen(Qt.PenStyle.NoPen)
            from PySide6.QtGui import QLinearGradient
            grad = QLinearGradient(r.topLeft(), r.bottomRight())
            grad.setColorAt(0, QColor("#2D8CF0"))
            grad.setColorAt(1, QColor("#1B6ED4"))
            p.setBrush(QBrush(grad))
            p.drawPath(path)

            # 中心齿轮 (简化: 白色圆 + 文字 ⚙)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255, 40)))
            inner = sz * 0.22
            p.drawEllipse(QRectF(inner, inner, sz - 2 * inner, sz - 2 * inner))

            # "S" 字母 (System/Setting)
            p.setPen(QColor("#FFFFFF"))
            fsize = max(int(sz * 0.48), 8)
            f = QFont("Microsoft YaHei UI", fsize, QFont.Weight.Bold)
            p.setFont(f)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "S")

            p.end()
            icon.addPixmap(pm)
        return icon

    app_icon = _make_app_icon()
    app.setWindowIcon(app_icon)

    # ── Splash Screen ──
    splash_pm = QPixmap(340, 120)
    splash_pm.fill(QColor("#F0F2F5"))
    p = QPainter(splash_pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor("#333333"))
    p.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
    p.drawText(splash_pm.rect().adjusted(0, 20, 0, -20), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "系统优化工具-专业版")
    p.setPen(QColor("#999999"))
    p.setFont(QFont("Microsoft YaHei UI", 10))
    p.drawText(splash_pm.rect().adjusted(0, 20, 0, 0), Qt.AlignmentFlag.AlignCenter, "正在加载，请稍候...")
    p.end()

    splash = QSplashScreen(splash_pm)
    splash.show()
    app.processEvents()

    try:
        from ui.main_window import MainWindow
        window = MainWindow()
        splash.finish(window)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        log_path = os.path.join(os.path.expanduser("~"), "Desktop", "startup_error.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        splash.close()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "启动失败", f"程序启动失败:\n{e}\n\n详情已写入桌面 startup_error.txt")
        raise


if __name__ == "__main__":
    main()
