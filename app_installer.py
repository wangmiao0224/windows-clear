"""
应用安装模块
优先使用 winget 安装，不可用时回退到直接下载安装
"""

import subprocess
import shutil
import os
import tempfile
import urllib.request
import ssl


_winget_available = None
_download_dir = None
_install_dir = None


def set_download_dir(path):
    global _download_dir
    _download_dir = path


def set_install_dir(path):
    global _install_dir
    _install_dir = path


def _get_download_dir():
    if _download_dir:
        d = _download_dir
    elif os.path.isdir("D:\\"):
        d = os.path.join("D:\\", "desktopSetting_downloads")
    else:
        d = os.path.join(tempfile.gettempdir(), "desktopSetting_downloads")
    os.makedirs(d, exist_ok=True)
    return d


def _get_install_dir():
    if _install_dir:
        return _install_dir
    if os.path.isdir("D:\\"):
        return "D:\\Programs"
    return None


def check_winget_available():
    global _winget_available
    if _winget_available is not None:
        return _winget_available

    try:
        result = subprocess.run(
            ["winget", "--version"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0 and result.stdout.strip():
            _winget_available = True
            return True
    except Exception:
        pass
    _winget_available = False
    return False


def _install_via_winget(winget_id, app_name, callback=None):
    try:
        cmd = ["winget", "install", "--id", winget_id,
               "--accept-package-agreements", "--accept-source-agreements", "-h"]
        install_dir = _get_install_dir()
        if install_dir:
            cmd += ["--location", install_dir]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        stdout, stderr = process.communicate(timeout=600)

        if process.returncode == 0:
            return True, f"✓ {app_name} 安装成功 (winget)"
        if "already installed" in stdout.lower() or "已安装" in stdout:
            return True, f"● {app_name} 已经安装"

        error_detail = stderr.strip() or stdout.strip()
        return False, f"winget失败: {error_detail[:150]}"
    except subprocess.TimeoutExpired:
        process.kill()
        return False, "winget超时"
    except Exception as e:
        return False, f"winget错误: {e}"


def _download_file(url, dest_path, app_name, callback=None, progress_cb=None, cancel_event=None):
    if callback:
        callback(f"  ↓ 正在下载 {app_name}...")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, context=ctx, timeout=180) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block = 1024 * 64
            with open(dest_path, "wb") as f:
                while True:
                    if cancel_event and cancel_event.is_set():
                        if callback:
                            callback(f"  ✗ {app_name} 下载已取消")
                        return False
                    data = resp.read(block)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if total > 0:
                        pct = downloaded * 100 // total
                        if progress_cb:
                            progress_cb(pct)
                        if callback:
                            mb = downloaded / 1024 / 1024
                            callback(f"  ↓ {app_name}: {mb:.1f}MB ({pct}%)")

        if callback:
            callback(f"  ↓ {app_name} 下载完成")
        return True
    except Exception as e:
        if callback:
            callback(f"  ✗ 下载失败: {e}")
        return False


def _install_downloaded(installer_path, app_name, silent_args="", installer_type="exe", callback=None):
    if callback:
        callback(f"  ▶ 正在安装 {app_name}...")
    try:
        install_dir = _get_install_dir()
        if installer_type == "msi":
            cmd = ["msiexec", "/i", installer_path] + (silent_args.split() if silent_args else ["/quiet", "/norestart"])
            if install_dir:
                cmd += [f'INSTALLDIR="{install_dir}\\{app_name}"']
        else:
            args = silent_args.split() if silent_args else []
            if install_dir:
                # 常见安装程序的安装路径参数
                args += [f'/D={install_dir}\\{app_name}']
            cmd = [installer_path] + args

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        process.communicate(timeout=600)

        if process.returncode == 0:
            return True, f"✓ {app_name} 安装成功 (下载安装)"
        else:
            return False, f"✗ {app_name} 安装返回代码 {process.returncode}"
    except subprocess.TimeoutExpired:
        process.kill()
        return False, f"✗ {app_name} 安装超时"
    except Exception as e:
        return False, f"✗ {app_name} 安装出错: {e}"


def _install_via_download(app, callback=None, progress_cb=None, cancel_event=None):
    url = app.get("download_url", "")
    if not url:
        # 无下载地址 → 尝试打开官网
        website = app.get("website", "")
        if website:
            import webbrowser
            webbrowser.open(website)
            return False, f"⊙ {app['name']} 已打开官网下载页，请手动安装"
        return False, f"✗ {app['name']} 无下载地址且 winget 不可用"

    ext = ".msi" if app.get("installer_type") == "msi" else ".exe"
    download_dir = _get_download_dir()
    safe_name = app["winget_id"].replace(".", "_")
    dest = os.path.join(download_dir, f"{safe_name}{ext}")

    if not _download_file(url, dest, app["name"], callback, progress_cb, cancel_event):
        return False, f"✗ {app['name']} 下载失败"

    success, msg = _install_downloaded(
        dest, app["name"],
        app.get("silent_args", ""),
        app.get("installer_type", "exe"),
        callback,
    )

    try:
        os.remove(dest)
    except Exception:
        pass

    return success, msg


def install_app(app, callback=None, progress_cb=None, cancel_event=None):
    """优先 winget，失败则下载安装"""
    app_name = app["name"]
    winget_id = app["winget_id"]
    if callback:
        callback(f"正在安装 {app_name} ({winget_id})...")

    if cancel_event and cancel_event.is_set():
        return False, f"✗ {app_name} 已取消"

    if check_winget_available():
        success, msg = _install_via_winget(winget_id, app_name, callback)
        if success:
            if callback:
                callback(msg)
            return True, msg
        if callback:
            callback(f"  ⚠ {msg}，尝试下载安装...")
    else:
        if callback:
            callback(f"  ⚠ winget 不可用，尝试下载安装...")

    if cancel_event and cancel_event.is_set():
        return False, f"✗ {app_name} 已取消"

    success, msg = _install_via_download(app, callback, progress_cb, cancel_event)
    if callback:
        callback(msg)
    return success, msg


def install_apps_batch(apps, callback=None, progress_callback=None):
    """
    批量安装应用
    apps: [{"name": "...", "winget_id": "...", "download_url": "...", ...}]
    callback: 日志回调
    progress_callback: 进度回调 progress_callback(current, total)
    返回: (success_count, fail_count, results)
    """
    total = len(apps)
    success_count = 0
    fail_count = 0
    results = []

    for i, app in enumerate(apps):
        if progress_callback:
            progress_callback(i, total)

        success, msg = install_app(app, callback)
        results.append({"app": app["name"], "success": success, "message": msg})

        if success:
            success_count += 1
        else:
            fail_count += 1

    if progress_callback:
        progress_callback(total, total)

    return success_count, fail_count, results
