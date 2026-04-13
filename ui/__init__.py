# UI package — PySide6 系统优化工具-专业版

import subprocess
import threading


def notify(title: str, message: str):
    """显示 Windows 桌面通知（非阻塞）"""
    def _show():
        try:
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
                "ContentType = WindowsRuntime] > $null; "
                "$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                "$texts = $xml.GetElementsByTagName('text'); "
                f"$texts[0].AppendChild($xml.CreateTextNode('{title}')) > $null; "
                f"$texts[1].AppendChild($xml.CreateTextNode('{message}')) > $null; "
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('系统优化工具').Show($toast)"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, timeout=5,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            )
        except Exception:
            pass
    threading.Thread(target=_show, daemon=True).start()
