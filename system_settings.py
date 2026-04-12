"""
系统设置管理模块
提供 Windows 系统设置的自动化操作（注册表修改、服务管理等）
"""

import winreg
import subprocess
import os
import ctypes


def is_admin():
    """检查当前是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def create_restore_point(description="桌面设置工具自动还原点", callback=None):
    """创建系统还原点（需要管理员权限）"""
    if callback:
        callback("正在创建系统还原点...")
    cmd = (
        "$null = Enable-ComputerRestore -Drive 'C:\\' -ErrorAction SilentlyContinue; "
        f"Checkpoint-Computer -Description '{description}' -RestorePointType MODIFY_SETTINGS -ErrorAction Stop; "
        "Write-Output 'OK'"
    )
    success, output = _run_powershell(cmd)
    if success and "OK" in output:
        msg = "系统还原点已创建"
    else:
        msg = f"还原点创建失败: {output}"
        success = False
    if callback:
        callback(msg)
    return success, msg


def _set_registry_value(hive, key_path, value_name, value, value_type=winreg.REG_DWORD):
    """设置注册表值，如果键不存在则创建"""
    try:
        key = winreg.CreateKeyEx(hive, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, value_name, 0, value_type, value)
        winreg.CloseKey(key)
        return True, f"已设置 {value_name} = {value}"
    except PermissionError:
        return False, f"权限不足，无法修改 {key_path}\\{value_name}（需要管理员权限）"
    except Exception as e:
        return False, f"设置 {value_name} 失败: {e}"


def _run_powershell(command):
    """执行 PowerShell 命令并返回结果"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "命令执行超时"
    except Exception as e:
        return False, str(e)


def disable_lockscreen_ads(callback=None):
    """
    关闭锁屏广告
    修改 ContentDeliveryManager 相关注册表项
    """
    results = []
    base_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"

    registry_values = {
        "RotatingLockScreenOverlayEnabled": 0,
        "RotatingLockScreenEnabled": 0,
        "SubscribedContent-338387Enabled": 0,
        "SubscribedContent-353696Enabled": 0,
        "SubscribedContent-353694Enabled": 0,
    }

    for name, value in registry_values.items():
        success, msg = _set_registry_value(winreg.HKEY_CURRENT_USER, base_path, name, value)
        results.append((success, msg))
        if callback:
            callback(msg)

    all_success = all(r[0] for r in results)
    return all_success, "锁屏广告已关闭" if all_success else "部分设置失败，请查看日志"


def disable_taskbar_ads(callback=None):
    """
    关闭任务栏广告和开始菜单推荐
    """
    results = []

    # 关闭资源管理器中的广告
    adv_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    success, msg = _set_registry_value(
        winreg.HKEY_CURRENT_USER, adv_path, "ShowSyncProviderNotifications", 0
    )
    results.append((success, msg))
    if callback:
        callback(msg)

    # 关闭开始菜单中的建议/广告
    cdm_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
    cdm_values = {
        "SubscribedContent-338388Enabled": 0,
        "SubscribedContent-338389Enabled": 0,
        "SubscribedContent-310093Enabled": 0,
        "SystemPaneSuggestionsEnabled": 0,
        "SoftLandingEnabled": 0,
    }

    for name, value in cdm_values.items():
        success, msg = _set_registry_value(winreg.HKEY_CURRENT_USER, cdm_path, name, value)
        results.append((success, msg))
        if callback:
            callback(msg)

    # 关闭 "从Windows获取提示和建议"
    tips_values = {
        "SubscribedContent-338393Enabled": 0,
        "SubscribedContent-353698Enabled": 0,
    }
    for name, value in tips_values.items():
        success, msg = _set_registry_value(winreg.HKEY_CURRENT_USER, cdm_path, name, value)
        results.append((success, msg))
        if callback:
            callback(msg)

    all_success = all(r[0] for r in results)
    return all_success, "任务栏广告已关闭" if all_success else "部分设置失败，请查看日志"


def disable_auto_update(callback=None):
    """
    关闭 Windows 自动更新
    通过注册表设置组策略 + 停止/禁用 Windows Update 服务
    """
    results = []

    # 方法1: 通过组策略注册表禁用自动更新
    au_path = r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
    success, msg = _set_registry_value(winreg.HKEY_LOCAL_MACHINE, au_path, "NoAutoUpdate", 1)
    results.append((success, msg))
    if callback:
        callback(msg)

    # 设置通知下载和安装（而不是自动安装）作为备选
    success, msg = _set_registry_value(winreg.HKEY_LOCAL_MACHINE, au_path, "AUOptions", 2)
    results.append((success, msg))
    if callback:
        callback(msg)

    # 方法2: 停止并禁用 Windows Update 服务
    commands = [
        'Stop-Service -Name "wuauserv" -Force -ErrorAction SilentlyContinue',
        'Set-Service -Name "wuauserv" -StartupType Disabled -ErrorAction SilentlyContinue',
    ]
    for cmd in commands:
        success, msg = _run_powershell(cmd)
        result_msg = f"执行: {cmd.split('-Name')[0].strip()} -> {'成功' if success else '失败'}"
        results.append((success, result_msg))
        if callback:
            callback(result_msg)

    all_success = all(r[0] for r in results)
    return all_success, "Windows自动更新已关闭" if all_success else "部分设置失败（可能需要管理员权限）"


def change_save_location(target_drive, folders=None, callback=None):
    """
    修改默认保存位置（桌面、文档、下载等）到目标磁盘
    target_drive: 目标盘符路径，如 "D:\\"
    folders: 要修改的文件夹列表，默认为全部
    """
    if folders is None:
        folders = ["Desktop", "Documents", "Downloads", "Music", "Pictures", "Videos"]

    # Shell Folder GUID 映射
    folder_guids = {
        "Desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
        "Documents": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
        "Downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
        "Music": "{4BD8D571-6D19-48D3-BE97-422220080E43}",
        "Pictures": "{33E28130-4E1E-4676-835A-98395C3BC3BB}",
        "Videos": "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}",
    }

    # 中文名映射
    folder_cn = {
        "Desktop": "桌面",
        "Documents": "文档",
        "Downloads": "下载",
        "Music": "音乐",
        "Pictures": "图片",
        "Videos": "视频",
    }

    results = []

    for folder in folders:
        if folder not in folder_guids:
            continue

        new_path = os.path.join(target_drive, folder_cn.get(folder, folder))

        # 创建目标文件夹
        try:
            os.makedirs(new_path, exist_ok=True)
        except Exception as e:
            msg = f"创建目录 {new_path} 失败: {e}"
            results.append((False, msg))
            if callback:
                callback(msg)
            continue

        # 使用 PowerShell 的 Known Folder API 移动
        # 先尝试通过注册表修改
        uf_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        shell_names = {
            "Desktop": "Desktop",
            "Documents": "Personal",
            "Downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
            "Music": "My Music",
            "Pictures": "My Pictures",
            "Videos": "My Video",
        }

        reg_name = shell_names.get(folder, folder)
        success, msg = _set_registry_value(
            winreg.HKEY_CURRENT_USER, uf_path, reg_name, new_path, winreg.REG_EXPAND_SZ
        )

        if success:
            result_msg = f"{folder_cn.get(folder, folder)} -> {new_path} 设置成功"
        else:
            result_msg = f"{folder_cn.get(folder, folder)} 设置失败: {msg}"

        results.append((success, result_msg))
        if callback:
            callback(result_msg)

    all_success = all(r[0] for r in results)
    summary = "默认保存位置已修改（重启资源管理器后生效）" if all_success else "部分文件夹修改失败"
    return all_success, summary


def get_available_refresh_rates():
    """获取当前显示器支持的刷新率列表"""
    cmd = (
        "Get-CimInstance -ClassName Win32_VideoController | "
        "Select-Object -ExpandProperty CurrentRefreshRate; "
        "(Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorBasicDisplayParams -ErrorAction SilentlyContinue) | "
        "Select-Object -ExpandProperty Active"
    )

    # 使用更可靠的方式获取刷新率
    cmd2 = (
        "$modes = @(); "
        "Add-Type -TypeDefinition '"
        'using System; using System.Runtime.InteropServices; '
        'public class DisplayHelper { '
        '[StructLayout(LayoutKind.Sequential, CharSet=CharSet.Ansi)] '
        'public struct DEVMODE { '
        '[MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dmDeviceName; '
        'public short dmSpecVersion; public short dmDriverVersion; public short dmSize; '
        'public short dmDriverExtra; public int dmFields; '
        'public int dmPositionX; public int dmPositionY; '
        'public int dmDisplayOrientation; public int dmDisplayFixedOutput; '
        'public short dmColor; public short dmDuplex; public short dmYResolution; '
        'public short dmTTOption; public short dmCollate; '
        '[MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dmFormName; '
        'public short dmLogPixels; public int dmBitsPerPel; '
        'public int dmPelsWidth; public int dmPelsHeight; '
        'public int dmDisplayFlags; public int dmDisplayFrequency; '
        '} '
        '[DllImport("user32.dll")] '
        'public static extern bool EnumDisplaySettings(string deviceName, int modeNum, ref DEVMODE devMode); '
        '}' "'; "
        "$dm = New-Object DisplayHelper+DEVMODE; "
        "$dm.dmSize = [System.Runtime.InteropServices.Marshal]::SizeOf($dm); "
        "$i = 0; $rates = @(); "
        "while([DisplayHelper]::EnumDisplaySettings($null, $i, [ref]$dm)) { "
        "$rates += $dm.dmDisplayFrequency; $i++ }; "
        "$rates | Sort-Object -Unique"
    )

    success, output = _run_powershell(cmd2)
    if success and output:
        rates = []
        for line in output.strip().split("\n"):
            line = line.strip()
            if line.isdigit():
                rate = int(line)
                if rate > 0:
                    rates.append(rate)
        return sorted(set(rates))

    # 回退：返回常见刷新率
    return [60, 75, 120, 144, 165, 240]


def set_refresh_rate(rate, callback=None):
    """
    设置屏幕刷新率
    rate: 目标刷新率 (Hz)
    """
    cmd = (
        f"$dm = New-Object -TypeName 'DisplayHelper+DEVMODE'; "
        f"# 使用 QRes 或 ChangeDisplaySettings 方式设置刷新率"
    )

    # 使用更直接的方式通过 PowerShell 设置
    ps_cmd = (
        "Add-Type -TypeDefinition '"
        'using System; using System.Runtime.InteropServices; '
        'public class DisplaySettings { '
        '[StructLayout(LayoutKind.Sequential, CharSet=CharSet.Ansi)] '
        'public struct DEVMODE { '
        '[MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dmDeviceName; '
        'public short dmSpecVersion; public short dmDriverVersion; public short dmSize; '
        'public short dmDriverExtra; public int dmFields; '
        'public int dmPositionX; public int dmPositionY; '
        'public int dmDisplayOrientation; public int dmDisplayFixedOutput; '
        'public short dmColor; public short dmDuplex; public short dmYResolution; '
        'public short dmTTOption; public short dmCollate; '
        '[MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dmFormName; '
        'public short dmLogPixels; public int dmBitsPerPel; '
        'public int dmPelsWidth; public int dmPelsHeight; '
        'public int dmDisplayFlags; public int dmDisplayFrequency; '
        '} '
        'public const int DM_DISPLAYFREQUENCY = 0x400000; '
        'public const int CDS_UPDATEREGISTRY = 0x01; '
        'public const int ENUM_CURRENT_SETTINGS = -1; '
        '[DllImport("user32.dll")] '
        'public static extern bool EnumDisplaySettings(string deviceName, int modeNum, ref DEVMODE devMode); '
        '[DllImport("user32.dll")] '
        'public static extern int ChangeDisplaySettings(ref DEVMODE devMode, int flags); '
        '}' "'; "
        "$dm = New-Object DisplaySettings+DEVMODE; "
        "$dm.dmSize = [System.Runtime.InteropServices.Marshal]::SizeOf($dm); "
        "[DisplaySettings]::EnumDisplaySettings($null, [DisplaySettings]::ENUM_CURRENT_SETTINGS, [ref]$dm) | Out-Null; "
        f"$dm.dmDisplayFrequency = {int(rate)}; "
        "$dm.dmFields = [DisplaySettings]::DM_DISPLAYFREQUENCY; "
        "$result = [DisplaySettings]::ChangeDisplaySettings([ref]$dm, [DisplaySettings]::CDS_UPDATEREGISTRY); "
        "if($result -eq 0) { Write-Output 'SUCCESS' } else { Write-Output \"FAILED:$result\" }"
    )

    success, output = _run_powershell(ps_cmd)

    if success and "SUCCESS" in output:
        msg = f"屏幕刷新率已设置为 {rate}Hz"
        if callback:
            callback(msg)
        return True, msg
    else:
        msg = f"设置刷新率失败: {output}"
        if callback:
            callback(msg)
        return False, msg


def disable_notifications(callback=None):
    """
    关闭 Windows 系统通知
    """
    results = []

    # 关闭 Toast 通知
    push_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\PushNotifications"
    success, msg = _set_registry_value(winreg.HKEY_CURRENT_USER, push_path, "ToastEnabled", 0)
    results.append((success, msg))
    if callback:
        callback(msg)

    # 关闭通知中心
    policies_path = r"SOFTWARE\Policies\Microsoft\Windows\Explorer"
    success, msg = _set_registry_value(winreg.HKEY_CURRENT_USER, policies_path, "DisableNotificationCenter", 1)
    results.append((success, msg))
    if callback:
        callback(msg)

    # 关闭锁屏上的通知
    success, msg = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings",
        "NOC_GLOBAL_SETTING_ALLOW_TOASTS_ABOVE_LOCK", 0
    )
    results.append((success, msg))
    if callback:
        callback(msg)

    all_success = all(r[0] for r in results)
    return all_success, "系统通知已关闭" if all_success else "部分设置失败"


def set_high_performance(callback=None):
    """
    设置电源计划为高性能模式
    """
    # 高性能模式 GUID
    high_perf_guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"

    if callback:
        callback("正在设置电源模式为高性能...")

    # 先尝试激活内置的高性能方案
    success, output = _run_powershell(f'powercfg /setactive {high_perf_guid}')

    if not success:
        # 如果高性能方案不存在，先复制一个
        if callback:
            callback("内置高性能方案不可用，正在创建...")
        _run_powershell(f'powercfg /duplicatescheme {high_perf_guid}')
        success, output = _run_powershell(f'powercfg /setactive {high_perf_guid}')

    if success:
        msg = "电源模式已设置为高性能"
        if callback:
            callback(msg)
        return True, msg
    else:
        msg = f"设置电源模式失败: {output}"
        if callback:
            callback(msg)
        return False, msg


def show_file_extensions(callback=None):
    """显示已知文件类型的扩展名"""
    adv_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    success, msg = _set_registry_value(winreg.HKEY_CURRENT_USER, adv_path, "HideFileExt", 0)
    result_msg = "文件扩展名已设为显示" if success else f"设置失败: {msg}"
    if callback:
        callback(result_msg)
    return success, result_msg


def show_hidden_files(callback=None):
    """显示隐藏的文件和文件夹"""
    adv_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    results = []

    # 显示隐藏文件
    s, m = _set_registry_value(winreg.HKEY_CURRENT_USER, adv_path, "Hidden", 1)
    results.append((s, m))
    # 显示受保护的操作系统文件（可选，这里不开启以免误删）

    if callback:
        callback("隐藏文件已设为显示" if s else f"设置失败: {m}")

    return s, "隐藏文件已设为显示" if s else f"设置失败: {m}"


def show_my_computer(callback=None):
    """在桌面显示"此电脑"图标"""
    # "此电脑" CLSID
    key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel"
    clsid = "{20D04FE0-3AEA-1069-A2D8-08002B30309D}"

    success, msg = _set_registry_value(winreg.HKEY_CURRENT_USER, key_path, clsid, 0)
    result_msg = "桌面已显示「此电脑」图标" if success else f"设置失败: {msg}"
    if callback:
        callback(result_msg)
    return success, result_msg


def classic_context_menu(callback=None):
    """Win11 恢复经典完整右键菜单"""
    key_path = r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32"
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "")
        winreg.CloseKey(key)
        msg = "经典右键菜单已恢复（重启资源管理器后生效）"
        if callback:
            callback(msg)
        return True, msg
    except Exception as e:
        msg = f"恢复经典右键菜单失败: {e}"
        if callback:
            callback(msg)
        return False, msg


def disable_search_highlights(callback=None):
    """关闭搜索热点/高亮"""
    results = []

    # 关闭搜索高亮
    search_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\SearchSettings"
    s, m = _set_registry_value(winreg.HKEY_CURRENT_USER, search_path, "IsDynamicSearchBoxEnabled", 0)
    results.append((s, m))
    if callback:
        callback(m)

    # 关闭搜索框中的 Bing 搜索
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Policies\Microsoft\Windows\Explorer",
        "DisableSearchBoxSuggestions", 1
    )
    results.append((s, m))
    if callback:
        callback(m)

    all_ok = all(r[0] for r in results)
    return all_ok, "搜索热点已关闭" if all_ok else "部分设置失败"


def disable_cortana(callback=None):
    """禁用 Cortana"""
    results = []

    # 禁用 Cortana
    cortana_path = r"SOFTWARE\Policies\Microsoft\Windows\Windows Search"
    s, m = _set_registry_value(winreg.HKEY_LOCAL_MACHINE, cortana_path, "AllowCortana", 0)
    results.append((s, m))
    if callback:
        callback(m)

    # 禁用 Cortana 在任务栏
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "ShowCortanaButton", 0
    )
    results.append((s, m))
    if callback:
        callback(m)

    all_ok = all(r[0] for r in results)
    return all_ok, "Cortana已禁用" if all_ok else "部分设置失败（可能需要管理员权限）"


def set_dns(primary_dns, secondary_dns="", callback=None):
    """
    设置 DNS 服务器
    primary_dns: 首选 DNS
    secondary_dns: 备用 DNS
    """
    if callback:
        callback(f"正在设置 DNS: {primary_dns} / {secondary_dns}...")

    # 获取活动网络适配器并设置 DNS
    cmd = (
        "$adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }; "
        "foreach($a in $adapters) { "
        f"Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex -ServerAddresses @('{primary_dns}'"
    )
    if secondary_dns:
        cmd += f",'{secondary_dns}'"
    cmd += ") }"

    success, output = _run_powershell(cmd)

    if success:
        dns_str = primary_dns
        if secondary_dns:
            dns_str += f", {secondary_dns}"
        msg = f"DNS已设置为 {dns_str}"
    else:
        msg = f"设置DNS失败: {output}"

    if callback:
        callback(msg)
    return success, msg


# ══════════════════════ 新增优化项 ══════════════════════


def disable_telemetry(callback=None):
    """关闭 Windows 遥测/隐私跟踪数据上传"""
    results = []

    # 设置诊断数据为最低
    s, m = _set_registry_value(
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
        "AllowTelemetry", 0)
    results.append((s, m))
    if callback:
        callback(m)

    # 禁用应用启动跟踪
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "Start_TrackProgs", 0)
    results.append((s, m))
    if callback:
        callback(m)

    # 禁用广告 ID
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
        "Enabled", 0)
    results.append((s, m))
    if callback:
        callback(m)

    # 停止诊断跟踪服务
    _run_powershell('Stop-Service -Name "DiagTrack" -Force -ErrorAction SilentlyContinue')
    _run_powershell('Set-Service -Name "DiagTrack" -StartupType Disabled -ErrorAction SilentlyContinue')
    if callback:
        callback("DiagTrack 服务已禁用")

    all_ok = all(r[0] for r in results)
    return all_ok, "遥测/隐私跟踪已关闭" if all_ok else "部分设置失败"


def disable_background_apps(callback=None):
    """关闭后台应用运行"""
    results = []

    # Win10 风格
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
        "GlobalUserDisabled", 1)
    results.append((s, m))
    if callback:
        callback(m)

    # Win11 风格
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Search",
        "BackgroundAppGlobalToggle", 0)
    results.append((s, m))
    if callback:
        callback(m)

    all_ok = all(r[0] for r in results)
    return all_ok, "后台应用已关闭" if all_ok else "部分设置失败"


def remove_bloatware(callback=None):
    """卸载预装 UWP 应用 (bloatware)"""
    bloatware = [
        "Microsoft.BingNews",
        "Microsoft.BingWeather",
        "Microsoft.GetHelp",
        "Microsoft.Getstarted",
        "Microsoft.MicrosoftSolitaireCollection",
        "Microsoft.People",
        "Microsoft.PowerAutomateDesktop",
        "Microsoft.Todos",
        "Microsoft.WindowsAlarms",
        "Microsoft.WindowsFeedbackHub",
        "Microsoft.WindowsMaps",
        "Microsoft.YourPhone",
        "Microsoft.ZuneMusic",
        "Microsoft.ZuneVideo",
        "Clipchamp.Clipchamp",
        "Microsoft.MicrosoftOfficeHub",
        "Microsoft.SkypeApp",
        "Microsoft.WindowsCommunicationsApps",
        "Microsoft.Xbox.TCUI",
        "Microsoft.XboxGameOverlay",
        "Microsoft.XboxGamingOverlay",
        "Microsoft.XboxIdentityProvider",
        "Microsoft.XboxSpeechToTextOverlay",
        "Microsoft.GamingApp",
    ]

    removed = 0
    for pkg in bloatware:
        cmd = f'Get-AppxPackage -Name "{pkg}" | Remove-AppxPackage -ErrorAction SilentlyContinue'
        s, _ = _run_powershell(cmd)
        if s:
            removed += 1
            if callback:
                callback(f"  已卸载 {pkg.split('.')[-1]}")
        # 也删除预安装
        _run_powershell(
            f'Get-AppxProvisionedPackage -Online | Where-Object {{$_.DisplayName -eq "{pkg}"}} | '
            f'Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue'
        )

    msg = f"已卸载 {removed} 个预装应用"
    if callback:
        callback(msg)
    return True, msg


def optimize_visual_effects(callback=None):
    """调整视觉效果为最佳性能（保留字体平滑）"""
    # 设置为自定义，关闭大部分动画
    adv_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
    s, m = _set_registry_value(winreg.HKEY_CURRENT_USER, adv_path, "VisualFXSetting", 2)

    # 关闭窗口动画
    dwm_path = r"SOFTWARE\Microsoft\Windows\DWM"
    _set_registry_value(winreg.HKEY_CURRENT_USER, dwm_path, "EnableAeroPeek", 0)

    # 关闭动画效果但保留字体平滑
    desktop_path = r"Control Panel\Desktop"
    _set_registry_value(winreg.HKEY_CURRENT_USER, desktop_path, "UserPreferencesMask",
                        b'\x90\x12\x03\x80\x10\x00\x00\x00', winreg.REG_BINARY)

    # 禁用窗口最小化/最大化动画
    _set_registry_value(winreg.HKEY_CURRENT_USER, desktop_path, "MenuShowDelay", "100", winreg.REG_SZ)

    win_metrics = r"Control Panel\Desktop\WindowMetrics"
    _set_registry_value(winreg.HKEY_CURRENT_USER, win_metrics, "MinAnimate", "0", winreg.REG_SZ)

    msg = "视觉效果已优化为最佳性能"
    if callback:
        callback(msg)
    return True, msg


def disable_sysmain(callback=None):
    """关闭 SysMain(Superfetch) 服务"""
    results = []

    s1, _ = _run_powershell('Stop-Service -Name "SysMain" -Force -ErrorAction SilentlyContinue')
    s2, _ = _run_powershell('Set-Service -Name "SysMain" -StartupType Disabled -ErrorAction SilentlyContinue')

    if s1 or s2:
        msg = "SysMain 服务已关闭"
    else:
        msg = "SysMain 服务关闭失败（可能不存在或需要管理员权限）"
    if callback:
        callback(msg)
    return s1 or s2, msg


def hide_taskbar_widgets(callback=None):
    """隐藏任务栏小组件面板"""
    results = []

    # Win11 小组件
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "TaskbarDa", 0)
    results.append((s, m))
    if callback:
        callback(m)

    # Win10 资讯和兴趣
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Feeds",
        "ShellFeedsTaskbarViewMode", 2)
    results.append((s, m))
    if callback:
        callback(m)

    all_ok = all(r[0] for r in results)
    return all_ok, "任务栏小组件已隐藏" if all_ok else "部分设置失败"


def hide_search_box(callback=None):
    """隐藏任务栏搜索框"""
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Search",
        "SearchboxTaskbarMode", 0)  # 0=隐藏, 1=图标, 2=搜索框
    msg = "搜索框已隐藏" if s else f"设置失败: {m}"
    if callback:
        callback(msg)
    return s, msg


def hide_task_view(callback=None):
    """关闭任务栏任务视图按钮"""
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "ShowTaskViewButton", 0)
    msg = "任务视图按钮已隐藏" if s else f"设置失败: {m}"
    if callback:
        callback(msg)
    return s, msg


def disable_game_bar(callback=None):
    """关闭 Xbox Game Bar 和游戏模式"""
    results = []

    # 关闭 Game Bar
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR",
        "AppCaptureEnabled", 0)
    results.append((s, m))
    if callback:
        callback(m)

    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\GameBar",
        "UseNexusForGameBarEnabled", 0)
    results.append((s, m))
    if callback:
        callback(m)

    # 关闭游戏模式
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\GameBar",
        "AutoGameModeEnabled", 0)
    results.append((s, m))
    if callback:
        callback(m)

    all_ok = all(r[0] for r in results)
    return all_ok, "Game Bar/游戏模式已关闭" if all_ok else "部分设置失败"


def disable_startup_sound(callback=None):
    """关闭开机声音"""
    s, m = _set_registry_value(
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Authentication\LogonUI\BootAnimation",
        "DisableStartupSound", 1)

    # 也通过 Beep 注册表关闭
    _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"AppEvents\Schemes",
        "", ".None", winreg.REG_SZ)  # 设置声音方案为无

    msg = "开机声音已关闭" if s else f"设置失败: {m}"
    if callback:
        callback(msg)
    return s, msg


def set_virtual_memory(callback=None):
    """设置虚拟内存为系统管理（优化页面文件）"""
    # 获取物理内存大小，设置1-2倍
    cmd = (
        "$mem = (Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1MB; "
        "$min = [math]::Round($mem); $max = [math]::Round($mem * 2); "
        "# 设置C盘页面文件为系统管理;\n"
        "$cs = Get-CimInstance Win32_ComputerSystem; "
        "if($cs.AutomaticManagedPagefile -eq $false) { "
        "  $cs | Set-CimInstance -Property @{AutomaticManagedPagefile=$true} "
        "}; "
        "Write-Output \"内存: ${mem}MB, 页面文件已设为系统自动管理\""
    )
    s, output = _run_powershell(cmd)

    msg = output if s else f"设置虚拟内存失败: {output}"
    if callback:
        callback(msg)
    return s, msg


# 设置函数映射（供 GUI 调用）
SETTINGS_FUNCTIONS = {
    "disable_lockscreen_ads": disable_lockscreen_ads,
    "disable_taskbar_ads": disable_taskbar_ads,
    "disable_notifications": disable_notifications,
    "disable_auto_update": disable_auto_update,
    "set_high_performance": set_high_performance,
    "show_file_extensions": show_file_extensions,
    "show_hidden_files": show_hidden_files,
    "show_my_computer": show_my_computer,
    "classic_context_menu": classic_context_menu,
    "disable_search_highlights": disable_search_highlights,
    "disable_cortana": disable_cortana,
    "disable_telemetry": disable_telemetry,
    "disable_background_apps": disable_background_apps,
    "remove_bloatware": remove_bloatware,
    "optimize_visual_effects": optimize_visual_effects,
    "disable_sysmain": disable_sysmain,
    "hide_taskbar_widgets": hide_taskbar_widgets,
    "hide_search_box": hide_search_box,
    "hide_task_view": hide_task_view,
    "disable_game_bar": disable_game_bar,
    "disable_startup_sound": disable_startup_sound,
    "set_virtual_memory": set_virtual_memory,
    "change_save_location": change_save_location,
    "set_refresh_rate": set_refresh_rate,
    "set_dns": set_dns,
}


def set_taskbar_alignment(alignment="left", callback=None):
    """设置Win11任务栏对齐方式: left=居左, center=居中"""
    val = 0 if alignment == "left" else 1
    s, m = _set_registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        "TaskbarAl", val)
    msg = f"任务栏已设为{'居左' if alignment == 'left' else '居中'}" if s else f"设置失败: {m}"
    if callback:
        callback(msg)
    return s, msg


def set_screen_timeout(minutes=15, callback=None):
    """设置屏幕休眠超时时间（交流电 + 电池）"""
    if callback:
        callback(f"正在设置屏幕休眠时间为 {minutes} 分钟...")
    cmds = [
        f"powercfg /change monitor-timeout-ac {minutes}",
        f"powercfg /change monitor-timeout-dc {minutes}",
    ]
    ok = True
    for cmd in cmds:
        s, _ = _run_powershell(cmd)
        ok = ok and s
    msg = f"屏幕休眠时间已设为 {minutes} 分钟" if ok else "设置失败"
    if callback:
        callback(msg)
    return ok, msg


def set_computer_name(name, callback=None):
    """修改计算机名称（重启后生效）"""
    if not name or not name.strip():
        return False, "计算机名称不能为空"
    name = name.strip()
    if callback:
        callback(f"正在修改计算机名称为 {name}...")
    cmd = f'Rename-Computer -NewName "{name}" -Force -ErrorAction Stop'
    s, output = _run_powershell(cmd)
    msg = f"计算机名称已修改为 {name}（重启后生效）" if s else f"修改失败: {output}"
    if callback:
        callback(msg)
    return s, msg


SETTINGS_FUNCTIONS["set_taskbar_alignment"] = set_taskbar_alignment
SETTINGS_FUNCTIONS["set_screen_timeout"] = set_screen_timeout
SETTINGS_FUNCTIONS["set_computer_name"] = set_computer_name


def set_default_install_dir(target="D:\\Program Files", callback=None):
    """修改 Windows 默认程序安装目录（ProgramFilesDir → D盘）"""
    if callback:
        callback(f"正在修改默认安装目录到 {target}...")

    key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion"
    mappings = [
        ("ProgramFilesDir", target),
        ("ProgramFilesDir (x86)", target.rstrip("\\") + " (x86)"),
        ("ProgramW6432Dir", target),
    ]
    ok_all = True
    for name, val in mappings:
        s, m = _set_registry_value(
            winreg.HKEY_LOCAL_MACHINE, key_path, name, val,
            value_type=winreg.REG_SZ,
        )
        if callback:
            callback(f"  {'✓' if s else '✗'} {name} → {val}")
        ok_all = ok_all and s

    # 创建目标目录
    for d in [target, target.rstrip("\\") + " (x86)"]:
        os.makedirs(d, exist_ok=True)

    msg = f"默认安装目录已修改为 {target}（对新安装的程序生效）" if ok_all else "部分修改失败，请检查管理员权限"
    if callback:
        callback(msg)
    return ok_all, msg


SETTINGS_FUNCTIONS["set_default_install_dir"] = set_default_install_dir
