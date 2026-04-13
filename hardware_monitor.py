"""
性能监控模块
获取 CPU、内存、磁盘、网络、GPU 等硬件状态
"""

import psutil
import subprocess
import platform


def _run_powershell(command):
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_cpu_info():
    """获取 CPU 信息和使用率"""
    info = {}
    info["usage"] = psutil.cpu_percent(interval=0.5)
    info["cores_physical"] = psutil.cpu_count(logical=False) or 0
    info["cores_logical"] = psutil.cpu_count(logical=True) or 0
    info["freq"] = ""
    freq = psutil.cpu_freq()
    if freq:
        info["freq"] = f"{freq.current:.0f} MHz"

    # CPU 名称
    name = _run_powershell(
        "(Get-CimInstance Win32_Processor).Name"
    )
    info["name"] = name or platform.processor() or "未知"

    # CPU 温度（可能不可用）
    temp = _run_powershell(
        "(Get-CimInstance -Namespace root\\OpenHardwareMonitor -ClassName Sensor "
        "| Where-Object { $_.SensorType -eq 'Temperature' -and $_.Name -like '*CPU*' } "
        "| Select-Object -First 1).Value"
    )
    info["temp"] = f"{temp}°C" if temp else "N/A"

    return info


def get_memory_info():
    """获取内存信息"""
    vm = psutil.virtual_memory()
    return {
        "total": vm.total / 1024 / 1024 / 1024,  # GB
        "used": vm.used / 1024 / 1024 / 1024,
        "available": vm.available / 1024 / 1024 / 1024,
        "percent": vm.percent,
    }


def get_disk_info():
    """获取磁盘信息"""
    disks = []
    for part in psutil.disk_partitions():
        if "cdrom" in part.opts.lower() or part.fstype == "":
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total / 1024 / 1024 / 1024,
                "used": usage.used / 1024 / 1024 / 1024,
                "free": usage.free / 1024 / 1024 / 1024,
                "percent": usage.percent,
            })
        except Exception:
            pass
    return disks


def get_network_info():
    """获取网络信息"""
    counters = psutil.net_io_counters()
    return {
        "bytes_sent": counters.bytes_sent,
        "bytes_recv": counters.bytes_recv,
        "sent_mb": counters.bytes_sent / 1024 / 1024,
        "recv_mb": counters.bytes_recv / 1024 / 1024,
    }


def get_display_info():
    """获取所有显示器的分辨率和刷新率"""
    try:
        import ctypes
        import ctypes.wintypes as wt

        class DEVMODEW(ctypes.Structure):
            _fields_ = [
                ("dmDeviceName", ctypes.c_wchar * 32),
                ("dmSpecVersion", ctypes.c_ushort),
                ("dmDriverVersion", ctypes.c_ushort),
                ("dmSize", ctypes.c_ushort),
                ("dmDriverExtra", ctypes.c_ushort),
                ("dmFields", ctypes.c_uint),
                ("dmPositionX", ctypes.c_int),
                ("dmPositionY", ctypes.c_int),
                ("dmDisplayOrientation", ctypes.c_uint),
                ("dmDisplayFixedOutput", ctypes.c_uint),
                ("dmColor", ctypes.c_short),
                ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short),
                ("dmCollate", ctypes.c_short),
                ("dmFormName", ctypes.c_wchar * 32),
                ("dmLogPixels", ctypes.c_ushort),
                ("dmBitsPerPel", ctypes.c_uint),
                ("dmPelsWidth", ctypes.c_uint),
                ("dmPelsHeight", ctypes.c_uint),
                ("dmDisplayFlags", ctypes.c_uint),
                ("dmDisplayFrequency", ctypes.c_uint),
            ]

        class DISPLAY_DEVICEW(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("DeviceName", ctypes.c_wchar * 32),
                ("DeviceString", ctypes.c_wchar * 128),
                ("StateFlags", ctypes.c_ulong),
                ("DeviceID", ctypes.c_wchar * 128),
                ("DeviceKey", ctypes.c_wchar * 128),
            ]

        user32 = ctypes.windll.user32
        monitors = []
        i = 0
        while True:
            dd = DISPLAY_DEVICEW()
            dd.cb = ctypes.sizeof(DISPLAY_DEVICEW)
            if not user32.EnumDisplayDevicesW(None, i, ctypes.byref(dd), 0):
                break
            i += 1
            # 只检测活动的显示器
            if not (dd.StateFlags & 1):  # DISPLAY_DEVICE_ATTACHED_TO_DESKTOP
                continue
            dm = DEVMODEW()
            dm.dmSize = ctypes.sizeof(DEVMODEW)
            if user32.EnumDisplaySettingsW(dd.DeviceName, -1, ctypes.byref(dm)):
                monitors.append({
                    "name": dd.DeviceString.strip() or dd.DeviceName.strip(),
                    "resolution": f"{dm.dmPelsWidth}×{dm.dmPelsHeight}",
                    "refresh_rate": f"{dm.dmDisplayFrequency}Hz" if dm.dmDisplayFrequency > 0 else "N/A",
                })

        if monitors:
            # 返回主显示器的信息用于简单显示，同时返回全部列表
            res_parts = [m["resolution"] for m in monitors]
            hz_parts = [m["refresh_rate"] for m in monitors]
            res_str = " | ".join(res_parts) if len(res_parts) > 1 else res_parts[0]
            hz_str = " | ".join(hz_parts) if len(hz_parts) > 1 else hz_parts[0]
            return res_str, hz_str

        # 回退到简单方式
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        dc = user32.GetDC(0)
        gdi32 = ctypes.windll.gdi32
        hz = gdi32.GetDeviceCaps(dc, 116)
        user32.ReleaseDC(0, dc)
        return f"{w}×{h}", f"{hz}Hz" if hz > 0 else "N/A"
    except Exception:
        return "N/A", "N/A"


def get_gpu_info():
    """获取 GPU 信息"""
    resolution, refresh = get_display_info()

    # 尝试 nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            if len(parts) >= 5:
                return {
                    "name": parts[0].strip(),
                    "temp": f"{parts[1].strip()}°C",
                    "usage": f"{parts[2].strip()}%",
                    "mem_used": f"{parts[3].strip()} MB",
                    "mem_total": f"{parts[4].strip()} MB",
                    "resolution": resolution,
                    "refresh_rate": refresh,
                }
    except Exception:
        pass

    # 回退到 WMI
    name = _run_powershell("(Get-CimInstance Win32_VideoController).Name")
    vram = _run_powershell(
        "[math]::Round((Get-CimInstance Win32_VideoController).AdapterRAM / 1MB)"
    )

    return {
        "name": name or "未知",
        "temp": "N/A",
        "usage": "N/A",
        "mem_used": "N/A",
        "mem_total": f"{vram} MB" if vram else "N/A",
        "resolution": resolution,
        "refresh_rate": refresh,
    }


def get_system_info():
    """获取系统基本信息"""
    os_name = _run_powershell(
        "(Get-CimInstance Win32_OperatingSystem).Caption"
    )
    os_version = platform.version()
    boot_time = psutil.boot_time()
    import datetime
    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes = remainder // 60

    return {
        "os": os_name or f"Windows {platform.release()}",
        "version": os_version,
        "uptime": f"{hours}小时{minutes}分钟",
        "hostname": platform.node(),
    }


def get_all_info():
    """获取所有硬件信息（用于首次加载）"""
    return {
        "system": get_system_info(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disks": get_disk_info(),
        "network": get_network_info(),
        "gpu": get_gpu_info(),
    }


def get_realtime_info():
    """获取实时信息（仅快速指标，用于定时刷新）"""
    return {
        "cpu_usage": psutil.cpu_percent(interval=0),
        "memory": get_memory_info(),
        "network": get_network_info(),
    }
