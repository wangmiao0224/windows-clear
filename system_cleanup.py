"""
系统修复清理模块
针对长期使用后出现的问题：主页劫持、弹窗广告、默认应用篡改等
"""

import winreg
import subprocess
import os
import glob
import shutil


def _set_registry_value(hive, key_path, value_name, value, value_type=winreg.REG_DWORD):
    try:
        key = winreg.CreateKeyEx(hive, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, value_name, 0, value_type, value)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _run_powershell(command):
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "命令超时"
    except Exception as e:
        return False, str(e)


def _delete_registry_value(hive, key_path, value_name):
    try:
        key = winreg.OpenKeyEx(hive, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, value_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True  # 不存在也算成功
    except Exception:
        return False


def _enum_registry_values(hive, key_path):
    """枚举注册表键下所有值"""
    values = []
    try:
        key = winreg.OpenKeyEx(hive, key_path, 0, winreg.KEY_READ)
        i = 0
        while True:
            try:
                name, data, vtype = winreg.EnumValue(key, i)
                values.append((name, data, vtype))
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
    except Exception:
        pass
    return values


# ══════════════════════ 修复功能 ══════════════════════


def fix_browser_homepage(callback=None):
    """修复浏览器主页被劫持（Chrome / Edge）"""
    fixed = 0

    # --- Chrome ---
    chrome_prefs_dirs = glob.glob(
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\*")
    )
    for d in chrome_prefs_dirs:
        prefs = os.path.join(d, "Preferences")
        secure_prefs = os.path.join(d, "Secure Preferences")
        for pf in [prefs, secure_prefs]:
            if os.path.isfile(pf):
                try:
                    import json
                    with open(pf, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    changed = False
                    # 检查主页
                    if "homepage" in data:
                        hp = data["homepage"]
                        if any(x in hp.lower() for x in ["360", "hao123", "2345", "sogou", "duba"]):
                            data["homepage"] = "https://www.google.com"
                            data["homepage_is_newtabpage"] = True
                            changed = True
                            if callback:
                                callback(f"  Chrome 主页已从 {hp} 修复")

                    # 检查启动页
                    session = data.get("session", {})
                    restore_on_startup_urls = session.get("startup_urls", [])
                    if isinstance(restore_on_startup_urls, list):
                        bad = [u for u in restore_on_startup_urls
                               if any(x in u.lower() for x in ["360", "hao123", "2345", "sogou", "duba"])]
                        if bad:
                            session["startup_urls"] = []
                            data["session"] = session
                            changed = True
                            if callback:
                                callback(f"  Chrome 启动页已清理 {len(bad)} 个劫持URL")

                    if changed:
                        with open(pf, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False)
                        fixed += 1
                except Exception:
                    pass

    # --- Edge ---
    edge_prefs_dirs = glob.glob(
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\*")
    )
    for d in edge_prefs_dirs:
        prefs = os.path.join(d, "Preferences")
        if os.path.isfile(prefs):
            try:
                import json
                with open(prefs, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "homepage" in data:
                    hp = data["homepage"]
                    if any(x in hp.lower() for x in ["360", "hao123", "2345", "sogou", "duba"]):
                        data["homepage"] = "https://www.bing.com"
                        data["homepage_is_newtabpage"] = True
                        with open(prefs, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False)
                        fixed += 1
                        if callback:
                            callback(f"  Edge 主页已修复")
            except Exception:
                pass

    # --- 注册表层面的主页劫持 ---
    hijack_keys = [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Internet Explorer\Main", "Start Page"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Internet Explorer\Main", "Start Page"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Internet Explorer\Main", "Default_Page_URL"),
    ]
    for hive, path, name in hijack_keys:
        try:
            key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            if any(x in val.lower() for x in ["360", "hao123", "2345", "sogou", "duba"]):
                _set_registry_value(hive, path, name, "about:blank", winreg.REG_SZ)
                fixed += 1
                if callback:
                    callback(f"  IE注册表主页 {name} 已修复")
        except Exception:
            pass

    msg = f"浏览器主页修复完成，修复 {fixed} 处" if fixed > 0 else "未发现主页被劫持"
    if callback:
        callback(msg)
    return True, msg


def fix_default_apps(callback=None):
    """修复默认应用被篡改"""
    results = []

    # 清除 UserChoice 覆盖 (需要管理员)
    # 常见被篡改的关联: .html, .htm, .pdf, http, https
    file_types = [".html", ".htm", ".pdf", ".txt", ".jpg", ".png"]

    if callback:
        callback("正在检查默认应用关联...")

    # 检查并报告当前默认浏览器
    s, out = _run_powershell(
        'Get-ItemProperty "HKCU:\\SOFTWARE\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\http\\UserChoice" '
        '| Select-Object -ExpandProperty ProgId -ErrorAction SilentlyContinue'
    )
    if s and out:
        if callback:
            callback(f"  当前默认浏览器: {out}")
        # 如果被设为360等
        if any(x in out.lower() for x in ["360", "2345", "sogou"]):
            if callback:
                callback(f"  ⚠ 默认浏览器疑似被篡改为 {out}")
            results.append(("browser", out))

    # 重置文件关联 — 删除流氓软件的注册
    rogue_progids = ["360browser", "2345Explorer", "SogouExplorer", "DubaExplorer"]
    for pid in rogue_progids:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"SOFTWARE\\Classes\\{pid}")
        except Exception:
            pass

    # 提示用户手动设置（因为 Win10+ 的 UserChoice 有 hash 保护无法直接改）
    if results:
        msg = "已清理流氓浏览器注册信息。请通过 设置→应用→默认应用 手动设置默认浏览器"
    else:
        msg = "默认应用未被篡改"

    if callback:
        callback(msg)
    return True, msg


def clean_popup_ads(callback=None):
    """清理弹窗广告（启动项、计划任务、Run键）"""
    cleaned = 0

    # 广告软件关键词
    ad_keywords = [
        "360", "2345", "hao123", "duba", "kingsofttips", "wpsupdate",
        "sogou", "baidu", "taobaoad", "popup", "advert", "hotshot",
        "kugouupdate", "iqiyiupdate", "newsapp", "weatherapp",
    ]

    # 1) 清理注册表 Run 键中的可疑启动项
    run_paths = [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
    ]

    for hive, path in run_paths:
        values = _enum_registry_values(hive, path)
        for name, data, vtype in values:
            data_lower = str(data).lower()
            name_lower = name.lower()
            if any(kw in data_lower or kw in name_lower for kw in ad_keywords):
                if _delete_registry_value(hive, path, name):
                    cleaned += 1
                    if callback:
                        callback(f"  已移除启动项: {name}")

    # 2) 清理计划任务中的可疑任务
    s, tasks_output = _run_powershell(
        "Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' } | "
        "Select-Object -Property TaskName, TaskPath | Format-Table -AutoSize | Out-String -Width 500"
    )
    if s and tasks_output:
        for line in tasks_output.split("\n"):
            line_lower = line.strip().lower()
            if any(kw in line_lower for kw in ad_keywords):
                # 提取任务名
                task_name = line.strip().split()[0] if line.strip() else ""
                if task_name:
                    ds, _ = _run_powershell(
                        f'Disable-ScheduledTask -TaskName "{task_name}" -ErrorAction SilentlyContinue'
                    )
                    if ds:
                        cleaned += 1
                        if callback:
                            callback(f"  已禁用计划任务: {task_name}")

    # 3) 清理通知区域的弹窗来源
    # 关闭 Windows 推送通知平台的后台
    _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\PushNotifications",
        "ToastEnabled", 0
    )

    msg = f"已清理 {cleaned} 个可疑广告项" if cleaned > 0 else "未发现明显的弹窗广告项"
    if callback:
        callback(msg)
    return True, msg


def clean_startup_items(callback=None):
    """清理启动项（禁用非必要启动程序）"""
    cleaned = 0

    # 获取所有启动项
    s, output = _run_powershell(
        "Get-CimInstance Win32_StartupCommand | "
        "Select-Object Name, Command, Location | "
        "Format-List | Out-String"
    )

    # 标记已知的非必要启动项
    unnecessary = [
        "wechat", "qq", "qqmusic", "kugou", "neteasemusic", "iqiyi",
        "qqbrowser", "sogou", "2345", "360", "duba", "baidunetdisk",
        "steam", "wegame", "epicgames", "discord", "spotify",
    ]

    # 只处理 Run 注册表启动项
    run_paths = [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    ]

    for hive, path in run_paths:
        values = _enum_registry_values(hive, path)
        for name, data, vtype in values:
            data_lower = str(data).lower()
            name_lower = name.lower()
            if any(kw in data_lower or kw in name_lower for kw in unnecessary):
                if _delete_registry_value(hive, path, name):
                    cleaned += 1
                    if callback:
                        callback(f"  已移除启动项: {name}")

    # 使用 Task Manager 的 Startup 禁用（通过注册表）
    startup_approved = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
    vals = _enum_registry_values(winreg.HKEY_CURRENT_USER, startup_approved)
    for name, data, vtype in vals:
        name_lower = name.lower()
        if any(kw in name_lower for kw in unnecessary):
            # 设置为禁用（第一个字节设为 03）
            if isinstance(data, bytes) and len(data) >= 1 and data[0] != 3:
                disabled_data = b'\x03' + data[1:]
                _set_registry_value(
                    winreg.HKEY_CURRENT_USER, startup_approved,
                    name, disabled_data, winreg.REG_BINARY
                )
                cleaned += 1
                if callback:
                    callback(f"  已禁用启动: {name}")

    msg = f"已清理 {cleaned} 个启动项" if cleaned > 0 else "启动项无需清理"
    if callback:
        callback(msg)
    return True, msg


def reset_hosts_file(callback=None):
    """重置 hosts 文件为默认"""
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    default_hosts = (
        "# Copyright (c) 1993-2009 Microsoft Corp.\n"
        "#\n"
        "# This is a sample HOSTS file used by Microsoft TCP/IP for Windows.\n"
        "#\n"
        "# localhost name resolution is handled within DNS itself.\n"
        "#\t127.0.0.1       localhost\n"
        "#\t::1             localhost\n"
    )

    try:
        # 先读取当前 hosts
        with open(hosts_path, "r", encoding="utf-8", errors="ignore") as f:
            current = f.read()

        # 检查是否有可疑条目
        suspicious = []
        for line in current.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                if any(x in line.lower() for x in ["360", "hao123", "2345", "sogou", "baidu"]):
                    suspicious.append(line)

        if suspicious:
            if callback:
                callback(f"  发现 {len(suspicious)} 条可疑 hosts 记录")
            # 备份
            backup = hosts_path + ".bak"
            shutil.copy2(hosts_path, backup)
            if callback:
                callback(f"  已备份到 {backup}")

            # 写入默认内容
            with open(hosts_path, "w", encoding="utf-8") as f:
                f.write(default_hosts)
            msg = "hosts 文件已重置"
        else:
            msg = "hosts 文件正常，无需修复"

    except PermissionError:
        msg = "hosts 文件修改失败（需要管理员权限）"
    except Exception as e:
        msg = f"hosts 文件处理出错: {e}"

    if callback:
        callback(msg)
    return "失败" not in msg, msg


def clean_temp_files(callback=None):
    """清理临时文件和缓存"""
    cleaned_size = 0

    temp_dirs = [
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
        os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
        r"C:\Windows\Temp",
        r"C:\Windows\Prefetch",
    ]

    for d in temp_dirs:
        if not d or not os.path.isdir(d):
            continue
        try:
            for item in os.listdir(d):
                path = os.path.join(d, item)
                try:
                    if os.path.isfile(path):
                        size = os.path.getsize(path)
                        os.remove(path)
                        cleaned_size += size
                    elif os.path.isdir(path):
                        size = sum(
                            os.path.getsize(os.path.join(r, f))
                            for r, _, files in os.walk(path) for f in files
                        )
                        shutil.rmtree(path, ignore_errors=True)
                        cleaned_size += size
                except (PermissionError, OSError):
                    pass  # 跳过正在使用的文件
        except Exception:
            pass

    # 也清理最近文件列表
    recent = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent")
    if os.path.isdir(recent):
        for f in os.listdir(recent):
            try:
                os.remove(os.path.join(recent, f))
            except Exception:
                pass

    # 清理回收站
    try:
        _run_powershell("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
        if callback:
            callback("  回收站已清空")
    except Exception:
        pass

    mb = cleaned_size / 1024 / 1024
    msg = f"已清理临时文件 {mb:.1f} MB"
    if callback:
        callback(msg)
    return True, msg


def scan_suspicious_services(callback=None):
    """扫描可疑服务"""
    suspicious_keywords = [
        "360", "2345", "hao123", "duba", "sogou", "baidu",
        "kingsofttips", "adservice", "popup",
    ]

    found = []
    s, output = _run_powershell(
        "Get-Service | Where-Object { $_.Status -eq 'Running' } | "
        "Select-Object Name, DisplayName | Format-Table -AutoSize | Out-String -Width 500"
    )
    if s and output:
        for line in output.split("\n"):
            line_lower = line.strip().lower()
            if any(kw in line_lower for kw in suspicious_keywords):
                parts = line.strip().split(None, 1)
                if parts:
                    svc_name = parts[0]
                    found.append(svc_name)
                    if callback:
                        callback(f"  发现可疑服务: {line.strip()}")
                    # 尝试停止并禁用
                    _run_powershell(f'Stop-Service -Name "{svc_name}" -Force -ErrorAction SilentlyContinue')
                    _run_powershell(f'Set-Service -Name "{svc_name}" -StartupType Disabled -ErrorAction SilentlyContinue')

    if found:
        msg = f"已处理 {len(found)} 个可疑服务"
    else:
        msg = "未发现可疑服务"
    if callback:
        callback(msg)
    return True, msg


# ══════════════════════ 垃圾应用检测 ══════════════════════

# 已知的垃圾/流氓/捆绑软件关键词
JUNK_APP_KEYWORDS = [
    "360安全", "360杀毒", "360浏览器", "360压缩", "360桌面", "360驱动",
    "2345", "hao123", "鲁大师", "驱动精灵", "驱动人生",
    "金山毒霸", "金山卫士", "猎豹浏览器", "猎豹清理",
    "百度杀毒", "百度卫士", "百度浏览器", "百度输入法",
    "搜狗输入法", "搜狗浏览器", "搜狗壁纸",
    "瑞星", "电脑管家", "腾讯手游助手",
    "迅雷", "迅游",
    "暴风影音", "风行",
    "小鸟壁纸", "桌面日历",
    "装机必备", "一键装机",
    "护眼大师", "鼠标连点",
    "WiFi万能钥匙",
]

# 英文关键词
JUNK_APP_KEYWORDS_EN = [
    "360 total security", "360 safe", "360 browser",
    "2345explorer", "hao123",
    "baidu", "duba", "liebao",
    "sogou", "sougou",
    "adware", "toolbar", "browser hijack",
    "driver booster", "driver talent",
    "ludashi",
    "ask toolbar", "conduit",
    "bytedance", "toutiao",
]


def scan_installed_apps():
    """
    扫描已安装的应用，返回所有应用列表及标记为垃圾的应用
    返回: [{"name": str, "publisher": str, "uninstall": str, "is_junk": bool}, ...]
    """
    apps = []
    seen = set()

    # 从注册表读取已安装程序
    uninstall_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hive, path in uninstall_paths:
        try:
            key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ)
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    i += 1
                    try:
                        subkey = winreg.OpenKeyEx(key, subkey_name, 0, winreg.KEY_READ)
                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        except FileNotFoundError:
                            winreg.CloseKey(subkey)
                            continue

                        if not name or name in seen:
                            winreg.CloseKey(subkey)
                            continue
                        seen.add(name)

                        # 获取发布者
                        try:
                            publisher = winreg.QueryValueEx(subkey, "Publisher")[0]
                        except FileNotFoundError:
                            publisher = ""

                        # 获取卸载命令
                        try:
                            uninstall_cmd = winreg.QueryValueEx(subkey, "UninstallString")[0]
                        except FileNotFoundError:
                            uninstall_cmd = ""

                        # 获取静默卸载命令
                        try:
                            quiet_uninstall = winreg.QueryValueEx(subkey, "QuietUninstallString")[0]
                        except FileNotFoundError:
                            quiet_uninstall = ""

                        # 判断是否垃圾
                        name_lower = name.lower()
                        pub_lower = publisher.lower()
                        is_junk = any(
                            kw.lower() in name_lower or kw.lower() in pub_lower
                            for kw in JUNK_APP_KEYWORDS + JUNK_APP_KEYWORDS_EN
                        )

                        apps.append({
                            "name": name,
                            "publisher": publisher,
                            "uninstall": quiet_uninstall or uninstall_cmd,
                            "is_junk": is_junk,
                        })

                        winreg.CloseKey(subkey)
                    except Exception:
                        pass
                except OSError:
                    break
            winreg.CloseKey(key)
        except Exception:
            pass

    return sorted(apps, key=lambda a: (not a["is_junk"], a["name"].lower()))


def uninstall_app(app_info, callback=None):
    """
    卸载指定应用
    app_info: {"name": str, "uninstall": str}
    """
    name = app_info["name"]
    cmd = app_info.get("uninstall", "")

    if not cmd:
        msg = f"✗ {name} 没有卸载命令"
        if callback:
            callback(msg)
        return False, msg

    if callback:
        callback(f"正在卸载 {name}...")

    try:
        # 尝试静默卸载
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        process.communicate(timeout=120)

        if process.returncode == 0:
            msg = f"✓ {name} 卸载成功"
        else:
            msg = f"⚠ {name} 卸载完成（返回码 {process.returncode}）"

    except subprocess.TimeoutExpired:
        process.kill()
        msg = f"✗ {name} 卸载超时"
    except Exception as e:
        msg = f"✗ {name} 卸载出错: {e}"

    if callback:
        callback(msg)
    return "✓" in msg or "⚠" in msg, msg


# 清理功能映射
CLEANUP_FUNCTIONS = {
    "fix_browser_homepage": fix_browser_homepage,
    "fix_default_apps": fix_default_apps,
    "clean_popup_ads": clean_popup_ads,
    "clean_startup_items": clean_startup_items,
    "reset_hosts_file": reset_hosts_file,
    "clean_temp_files": clean_temp_files,
    "scan_suspicious_services": scan_suspicious_services,
}

# 清理项配置
CLEANUP_ITEMS = [
    {"name": "修复浏览器主页", "key": "fix_browser_homepage",
     "description": "修复被360/hao123/2345劫持的主页"},
    {"name": "修复默认应用", "key": "fix_default_apps",
     "description": "检查并修复默认浏览器被篡改"},
    {"name": "清理弹窗广告", "key": "clean_popup_ads",
     "description": "清理注册表启动项和计划任务中的广告"},
    {"name": "清理启动项", "key": "clean_startup_items",
     "description": "禁用非必要的开机启动程序"},
    {"name": "重置hosts文件", "key": "reset_hosts_file",
     "description": "清除可疑的DNS劫持记录"},
    {"name": "清理临时文件", "key": "clean_temp_files",
     "description": "清理Temp/Prefetch/回收站等"},
    {"name": "扫描可疑服务", "key": "scan_suspicious_services",
     "description": "发现并禁用流氓服务"},
]


# ══════════════════════ Windows 激活 ══════════════════════

def get_activation_status(callback=None):
    """获取当前 Windows 激活状态"""
    result = {"edition": "未知", "status": "未知", "detail": ""}
    try:
        p = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance SoftwareLicensingProduct -Filter "
             "\"ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f' "
             "AND PartialProductKey IS NOT NULL\" | "
             "Select-Object Name,LicenseStatus | Format-List"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out = p.stdout.strip()
        if out:
            for line in out.splitlines():
                if "Name" in line and ":" in line:
                    result["edition"] = line.split(":", 1)[1].strip()
                if "LicenseStatus" in line and ":" in line:
                    code = line.split(":", 1)[1].strip()
                    status_map = {
                        "0": "未授权", "1": "已激活",
                        "2": "宽限期", "3": "OOT宽限期",
                        "4": "非正版宽限期", "5": "通知",
                        "6": "扩展宽限期",
                    }
                    result["status"] = status_map.get(code, f"未知({code})")
        # 补充过期信息
        p2 = subprocess.run(
            ["cscript", "//nologo", r"C:\Windows\System32\slmgr.vbs", "/xpr"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        result["detail"] = p2.stdout.strip()
    except Exception as e:
        result["detail"] = f"检测出错: {e}"
    if callback:
        callback(f"版本: {result['edition']}")
        callback(f"状态: {result['status']}")
        if result["detail"]:
            callback(result["detail"])
    return result


def activate_windows(product_key, callback=None):
    """
    使用产品密钥激活 Windows (slmgr /ipk + /ato)
    product_key: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX 格式
    """
    import re
    key = product_key.strip()
    if not re.match(r'^[A-Za-z0-9]{5}(-[A-Za-z0-9]{5}){4}$', key):
        msg = "✗ 密钥格式无效，应为 XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"
        if callback:
            callback(msg)
        return False, msg

    # 安装密钥
    if callback:
        callback("正在安装产品密钥...")
    try:
        p1 = subprocess.run(
            ["cscript", "//nologo", r"C:\Windows\System32\slmgr.vbs", "/ipk", key],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out1 = p1.stdout.strip()
        if callback:
            callback(out1)
        if p1.returncode != 0:
            return False, f"✗ 安装密钥失败: {p1.stderr.strip() or out1}"
    except Exception as e:
        msg = f"✗ 安装密钥出错: {e}"
        if callback:
            callback(msg)
        return False, msg

    # 激活
    if callback:
        callback("正在激活...")
    try:
        p2 = subprocess.run(
            ["cscript", "//nologo", r"C:\Windows\System32\slmgr.vbs", "/ato"],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out2 = p2.stdout.strip()
        if callback:
            callback(out2)
        if p2.returncode == 0 and ("成功" in out2 or "successfully" in out2.lower()):
            return True, f"✓ 激活成功\n{out2}"
        else:
            return False, f"⚠ 激活返回: {out2}"
    except Exception as e:
        msg = f"✗ 激活出错: {e}"
        if callback:
            callback(msg)
        return False, msg
