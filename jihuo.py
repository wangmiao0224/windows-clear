import platform
import subprocess
import sys

try:
    import winreg  # Only available on Windows
except Exception:
    winreg = None

def get_windows_info():
    """自动获取当前Windows版本和Edition"""
    try:
        version = platform.version()
        build = int(version.split('.')[2]) if '.' in version else 0

        product_name = ""
        edition = "Professional"

        if sys.platform == "win32" and winreg is not None:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
            ) as key:
                product_name = winreg.QueryValueEx(key, "ProductName")[0]
                edition_id = winreg.QueryValueEx(key, "EditionID")[0]
                if isinstance(edition_id, str) and edition_id:
                    edition = edition_id

        # 检测 Windows Server
        if "Server" in product_name:
            if "2025" in product_name or build >= 26100:
                os_name = "Windows Server 2025"
            elif "2022" in product_name or build >= 20348:
                os_name = "Windows Server 2022"
            elif "2019" in product_name or build >= 17763:
                os_name = "Windows Server 2019"
            elif "2016" in product_name or build >= 14393:
                os_name = "Windows Server 2016"
            else:
                os_name = "Windows Server"
        elif "Windows 11" in product_name or build >= 22000:
            os_name = "Windows 11"
        elif "Windows 10" in product_name or build >= 10240:
            os_name = "Windows 10"
        elif build >= 9600:
            os_name = "Windows 8.1"
        elif build >= 9200:
            os_name = "Windows 8"
        elif build >= 7601:
            os_name = "Windows 7"
        else:
            os_name = "Windows 10"

        return os_name, edition
    except Exception:
        return "Windows 10", "Professional"


# 内置 KMS 激活密钥（按操作系统名回退用）
KMS_KEYS = {
    "Windows 11": "W269N-WFGWX-YVC9B-4J6C9-T83GX",
    "Windows 10": "W269N-WFGWX-YVC9B-4J6C9-T83GX",
    "Windows 8.1": "GCRJD-8NW9H-F2CDX-CCM8D-9D6T9",
    "Windows 8": "NG4HW-VH26C-733KW-K6F98-J8CK4",
    "Windows 7": "FJ82H-XT6CR-J8D7P-XQJJ2-GPDD4",
}

# Edition → GVLK 密钥（优先使用，来源: Microsoft 官方文档）
KMS_KEYS_BY_EDITION = {
    # ── Windows 10/11 消费者版 ──
    "Core":                 "TX9XD-98N7V-6WMQ6-BX7FG-H8Q99",          # 家庭版
    "CoreN":                "3KHY7-WNT83-DGQKR-F7HPR-844BM",          # 家庭版 N
    "CoreCountrySpecific":  "PVMJN-6DFY6-9CCP6-7BKTT-D3WVR",          # 家庭中文版
    "CoreSingleLanguage":   "7HNRX-D7KGG-3K4RQ-4WPJ4-YTDFH",          # 家庭单语言版

    # ── Windows 10/11 专业版 ──
    "Professional":         "W269N-WFGWX-YVC9B-4J6C9-T83GX",
    "ProfessionalN":        "MH37W-N47XK-V7XM9-C7227-GCQG9",
    "ProfessionalWorkstation":  "NRG8B-VKK3Q-CXVCJ-9G2XF-6Q84J",      # 专业工作站
    "ProfessionalWorkstationN": "9FNHH-K3HBT-3W4TD-6383H-6XYWF",
    "ProfessionalEducation":    "6TP4R-GNPTD-KYYHQ-7B7DP-J447Y",       # 专业教育版
    "ProfessionalEducationN":   "YVWGF-BXNMC-HTQYQ-CPQ99-66QFC",

    # ── Windows 10/11 企业版 ──
    "Enterprise":           "NPPR9-FWDCX-D2C8J-H872K-2YT43",
    "EnterpriseN":          "DPH2V-TTNVB-4X9Q3-TJR4H-KHJW4",
    "EnterpriseG":          "YYVX9-NTFWV-6MDM3-9PT4T-4M68B",           # 政府版
    "EnterpriseGN":         "44RPN-FTY23-9VTTB-MP9BX-T84FV",
    "EnterpriseS":          "M7XTQ-FN8P6-TTKYV-9D4CC-J462D",           # LTSC 2024/2021/2019
    "EnterpriseSN":         "92NFX-8DJQP-P6BBQ-THF9C-7CG2H",

    # ── Windows 10/11 教育版 ──
    "Education":            "NW6C2-QMPVW-D7KKK-3GKT6-VCFB2",
    "EducationN":           "2WH4N-8QGBV-H22JP-CT43Q-MDWWJ",

    # ── Windows 10 LTSB ──
    "EnterpriseS2016":      "DCPHK-NFMTC-H88MJ-PFHPY-QJ4BJ",          # LTSB 2016
    "EnterpriseS2015":      "WNMTR-4C88C-JK8YV-HQ7T2-76DF9",          # LTSB 2015

    # ── IoT Enterprise ──
    "IoTEnterprise":        "XQQYW-NFFMW-XJPBH-K8732-CKFFD",
    "IoTEnterpriseS":       "QPM6N-7J2WJ-P88HH-P3YRH-YY74H",          # IoT LTSC

    # ── Windows 8.1 ──
    "Professional8.1":      "GCRJD-8NW9H-F2CDX-CCM8D-9D6T9",
    "Enterprise8.1":        "MHF9N-XY6XB-WVXMC-BTDCT-MKKG7",

    # ── Windows Server 2025 ──
    "ServerStandard2025":       "TVRH6-WHNXV-R9WG3-9XRFY-MY832",
    "ServerDatacenter2025":     "D764K-2NDRG-47T6Q-P8T8W-YP6DF",

    # ── Windows Server 2022 ──
    "ServerStandard2022":       "VDYBN-27WPP-V4HQT-9VMD4-VMK7H",
    "ServerDatacenter2022":     "WX4NM-KYWYW-QJJR4-XV3QB-6VM33",

    # ── Windows Server 2019 ──
    "ServerStandard2019":       "N69G4-B89J2-4G8F4-WWYCC-J464C",
    "ServerDatacenter2019":     "WMDGN-G9PQG-XVVXX-R3X43-63DFG",

    # ── Windows Server 2016 ──
    "ServerStandard2016":       "WC2BQ-8NRM3-FDDYY-2BFGV-KHKQY",
    "ServerDatacenter2016":     "CB7KF-BWN84-R7R2Y-793K2-8XDDG",
}

KMS_SERVERS = [
    "kms.cx",
    "kms.03k.org",
    "kms.luody.info",
    "kms8.msguides.com",
]


def kms_activate(callback=None):
    """
    自动 KMS 激活 Windows。
    依次尝试多个 KMS 服务器，全部失败才返回失败。
    callback: 日志回调函数
    返回: (success: bool, message: str)
    """
    log = callback or (lambda msg: None)

    win_ver, edition = get_windows_info()
    key = KMS_KEYS_BY_EDITION.get(edition)
    if not key:
        edition_lower = (edition or "").lower()
        # Windows Server 版本匹配
        if "Server" in win_ver:
            year = win_ver.split()[-1] if win_ver.split()[-1].isdigit() else ""
            if "datacenter" in edition_lower:
                key = KMS_KEYS_BY_EDITION.get(f"ServerDatacenter{year}")
            else:
                key = KMS_KEYS_BY_EDITION.get(f"ServerStandard{year}")
        elif "iot" in edition_lower and "enterprise" in edition_lower:
            if "ltsc" in edition_lower or edition_lower.endswith("s"):
                key = KMS_KEYS_BY_EDITION.get("IoTEnterpriseS")
            else:
                key = KMS_KEYS_BY_EDITION.get("IoTEnterprise")
        elif "core" in edition_lower:
            key = KMS_KEYS_BY_EDITION.get("Core")
        elif "professional" in edition_lower:
            if "workstation" in edition_lower:
                key = KMS_KEYS_BY_EDITION.get("ProfessionalWorkstation")
            elif "education" in edition_lower:
                key = KMS_KEYS_BY_EDITION.get("ProfessionalEducation")
            else:
                key = KMS_KEYS_BY_EDITION.get("Professional")
        elif "enterprise" in edition_lower:
            if "ltsc" in edition_lower or edition_lower.endswith("s"):
                key = KMS_KEYS_BY_EDITION.get("EnterpriseS")
            elif "g" in edition_lower:
                key = KMS_KEYS_BY_EDITION.get("EnterpriseG")
            else:
                key = KMS_KEYS_BY_EDITION.get("Enterprise")
        elif "education" in edition_lower:
            key = KMS_KEYS_BY_EDITION.get("Education")
    if not key:
        key = KMS_KEYS.get(win_ver, KMS_KEYS.get("Windows 10", "W269N-WFGWX-YVC9B-4J6C9-T83GX"))

    log(f"系统版本: {win_ver} {edition}")
    log(f"激活密钥: {key}")

    cflags = subprocess.CREATE_NO_WINDOW

    # 先安装产品密钥（只需一次）
    log("正在安装产品密钥...")
    try:
        p = subprocess.run(
            ["cscript", "//nologo", r"C:\Windows\System32\slmgr.vbs", "/ipk", key],
            capture_output=True, text=True, timeout=30, creationflags=cflags,
        )
        out = p.stdout.strip()
        log(out if out else "(无输出)")
        if p.returncode != 0:
            err = p.stderr.strip() or out
            log(f"✗ 安装密钥失败: {err}")
            return False, f"✗ 安装密钥失败: {err}"
    except Exception as e:
        log(f"✗ 安装密钥出错: {e}")
        return False, f"✗ 安装密钥出错: {e}"

    # 依次尝试每个 KMS 服务器
    last_err = ""
    for idx, server in enumerate(KMS_SERVERS, 1):
        log(f"\n── 尝试 KMS 服务器 ({idx}/{len(KMS_SERVERS)}): {server} ──")

        # 设置 KMS 服务器
        log("正在设置 KMS 服务器...")
        try:
            p = subprocess.run(
                ["cscript", "//nologo", r"C:\Windows\System32\slmgr.vbs", "/skms", server],
                capture_output=True, text=True, timeout=30, creationflags=cflags,
            )
            out = p.stdout.strip()
            log(out if out else "(无输出)")
            if p.returncode != 0:
                err = p.stderr.strip() or out
                log(f"✗ 设置 KMS 服务器失败: {err}")
                last_err = err
                continue
        except Exception as e:
            log(f"✗ 设置 KMS 服务器出错: {e}")
            last_err = str(e)
            continue

        # 激活
        log("正在激活...")
        try:
            p = subprocess.run(
                ["cscript", "//nologo", r"C:\Windows\System32\slmgr.vbs", "/ato"],
                capture_output=True, text=True, timeout=60, creationflags=cflags,
            )
            out = p.stdout.strip()
            log(out if out else "(无输出)")
            if p.returncode == 0 and ("成功" in out or "successfully" in out.lower()):
                log(f"✓ KMS 激活成功！(服务器: {server})")
                return True, key
            else:
                log(f"⚠ 激活返回: {out}")
                last_err = out
        except Exception as e:
            log(f"✗ 激活出错: {e}")
            last_err = str(e)

    log(f"\n✗ 所有 KMS 服务器均失败")
    return False, f"✗ 所有 KMS 服务器均失败: {last_err}"

if __name__ == "__main__":
    if sys.platform != "win32":
        print("❌ 仅支持Windows")
    else:
        ok, msg = kms_activate(callback=print)
        print(msg)