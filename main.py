"""
系统优化工具-专业版 - 入口文件 (PySide6)
功能：一键初始化 Windows 系统设置 + 自动安装常用应用
"""

import sys
import os
import ctypes
import ctypes.wintypes as wt


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


# ── Win32 原生 Splash（在导入 PySide6 之前极速显示） ──

_user32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32
_kernel32 = ctypes.windll.kernel32

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
SW_SHOW = 5
WM_PAINT = 0x000F
WM_DESTROY = 0x0002
CS_HREDRAW = 0x0002
CS_VREDRAW = 0x0001
DT_CENTER = 0x0001
DT_VCENTER = 0x0004
DT_SINGLELINE = 0x0020
COLOR_WINDOW = 5
SM_CXSCREEN = 0
SM_CYSCREEN = 1
FW_BOLD = 700
FW_NORMAL = 400

_splash_hwnd = None
_splash_progress = 0  # 0-100


def _wnd_proc(hwnd, msg, wparam, lparam):
    if msg == WM_PAINT:
        class PAINTSTRUCT(ctypes.Structure):
            _fields_ = [
                ("hdc", wt.HDC), ("fErase", wt.BOOL), ("rcPaint", wt.RECT),
                ("fRestore", wt.BOOL), ("fIncUpdate", wt.BOOL), ("rgbReserved", wt.BYTE * 32),
            ]
        ps = PAINTSTRUCT()
        hdc = _user32.BeginPaint(hwnd, ctypes.byref(ps))

        # 背景
        bg_brush = _gdi32.CreateSolidBrush(0x00F5F2F0)  # #F0F2F5 in BGR
        rc = wt.RECT()
        _user32.GetClientRect(hwnd, ctypes.byref(rc))
        _user32.FillRect(hdc, ctypes.byref(rc), bg_brush)
        _gdi32.DeleteObject(bg_brush)

        _gdi32.SetBkMode(hdc, 1)  # TRANSPARENT

        # 标题
        title_font = _gdi32.CreateFontW(
            -24, 0, 0, 0, FW_BOLD, 0, 0, 0, 1, 0, 0, 4, 0, "Microsoft YaHei UI")
        old_font = _gdi32.SelectObject(hdc, title_font)
        _gdi32.SetTextColor(hdc, 0x00333333)
        rc_title = wt.RECT(rc.left, rc.top + 15, rc.right, rc.top + 55)
        _user32.DrawTextW(hdc, "系统优化工具-专业版", -1, ctypes.byref(rc_title),
                          DT_CENTER | DT_SINGLELINE | DT_VCENTER)
        _gdi32.SelectObject(hdc, old_font)
        _gdi32.DeleteObject(title_font)

        # 副标题
        sub_font = _gdi32.CreateFontW(
            -13, 0, 0, 0, FW_NORMAL, 0, 0, 0, 1, 0, 0, 4, 0, "Microsoft YaHei UI")
        old_font = _gdi32.SelectObject(hdc, sub_font)
        _gdi32.SetTextColor(hdc, 0x00999999)
        rc_sub = wt.RECT(rc.left, rc.top + 52, rc.right, rc.top + 75)
        _user32.DrawTextW(hdc, "正在加载，请稍候...", -1, ctypes.byref(rc_sub),
                          DT_CENTER | DT_SINGLELINE | DT_VCENTER)
        _gdi32.SelectObject(hdc, old_font)
        _gdi32.DeleteObject(sub_font)

        # 进度条
        bar_margin = 40
        bar_y = rc.bottom - 22
        bar_h = 6
        bar_w = rc.right - 2 * bar_margin

        # 背景槽
        track_brush = _gdi32.CreateSolidBrush(0x00E0DDD8)  # #D8DDE0 BGR
        rc_track = wt.RECT(bar_margin, bar_y, bar_margin + bar_w, bar_y + bar_h)
        _user32.FillRect(hdc, ctypes.byref(rc_track), track_brush)
        _gdi32.DeleteObject(track_brush)

        # 填充
        if _splash_progress > 0:
            fill_w = max(1, int(bar_w * _splash_progress / 100))
            fill_brush = _gdi32.CreateSolidBrush(0x00D4781B)  # #1B78D4 BGR (蓝色)
            rc_fill = wt.RECT(bar_margin, bar_y, bar_margin + fill_w, bar_y + bar_h)
            _user32.FillRect(hdc, ctypes.byref(rc_fill), fill_brush)
            _gdi32.DeleteObject(fill_brush)

        _user32.EndPaint(hwnd, ctypes.byref(ps))
        return 0
    if msg == WM_DESTROY:
        return 0
    return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)


# prevent GC of the callback
_wnd_proc_cb = WNDPROC(_wnd_proc)


def show_native_splash():
    """创建并显示一个纯 Win32 splash 窗口，返回 HWND"""
    global _splash_hwnd

    class WNDCLASSEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
            ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON), ("hCursor", wt.HANDLE),
            ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
            ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON),
        ]

    hInst = _kernel32.GetModuleHandleW(None)
    cls_name = "NativeSplash_SysOpt"

    wc = WNDCLASSEXW()
    wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
    wc.style = CS_HREDRAW | CS_VREDRAW
    wc.lpfnWndProc = _wnd_proc_cb
    wc.hInstance = hInst
    wc.hbrBackground = _gdi32.CreateSolidBrush(0x00F5F2F0)
    wc.lpszClassName = cls_name
    _user32.RegisterClassExW(ctypes.byref(wc))

    w, h = 340, 120
    sx = _user32.GetSystemMetrics(SM_CXSCREEN)
    sy = _user32.GetSystemMetrics(SM_CYSCREEN)
    x = (sx - w) // 2
    y = (sy - h) // 2

    hwnd = _user32.CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
        cls_name, None, WS_POPUP | WS_VISIBLE,
        x, y, w, h, None, None, hInst, None,
    )
    _user32.ShowWindow(hwnd, SW_SHOW)
    _user32.UpdateWindow(hwnd)
    _splash_hwnd = hwnd
    return hwnd


def close_native_splash():
    """关闭原生 splash 窗口"""
    global _splash_hwnd
    if _splash_hwnd:
        _user32.DestroyWindow(_splash_hwnd)
        _splash_hwnd = None


def update_native_splash(progress: int):
    """更新进度条 (0-100) 并刷新窗口"""
    global _splash_progress
    _splash_progress = max(0, min(100, progress))
    if _splash_hwnd:
        _user32.InvalidateRect(_splash_hwnd, None, True)
        _user32.UpdateWindow(_splash_hwnd)


def main():
    request_admin()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # 先用 Win32 原生窗口极速显示 splash（~0.2 秒内可见）
    show_native_splash()
    update_native_splash(10)

    from PySide6.QtWidgets import QApplication, QSplashScreen, QLabel
    from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon, QPen, QBrush, QPainterPath
    from PySide6.QtCore import Qt, QRectF
    update_native_splash(50)

    app = QApplication(sys.argv)
    update_native_splash(60)

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
    update_native_splash(70)

    try:
        from ui.main_window import MainWindow
        update_native_splash(85)
        window = MainWindow()
        update_native_splash(100)
        close_native_splash()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        close_native_splash()
        log_path = os.path.join(os.path.expanduser("~"), "Desktop", "startup_error.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "启动失败", f"程序启动失败:\n{e}\n\n详情已写入桌面 startup_error.txt")
        raise


if __name__ == "__main__":
    main()
