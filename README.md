# 系统优化工具 - 专业版

> Windows 桌面初始化一站式工具，一键完成系统设置优化、软件批量安装、垃圾清理、KMS 激活等操作。

![PySide6](https://img.shields.io/badge/GUI-PySide6-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![Windows](https://img.shields.io/badge/OS-Windows%2010%2F11-blue)

## 功能特性

### 🔧 系统设置（27 项）

| 分类 | 设置项 |
|------|--------|
| 广告优化 | 关闭锁屏广告、任务栏广告、系统通知 |
| 系统优化 | 关闭自动更新、高性能电源模式、优化虚拟内存、关闭 SysMain |
| 资源管理器 | 显示文件扩展名、显示隐藏文件、桌面显示此电脑 |
| Win11 专属 | 恢复经典右键菜单、任务栏对齐方式（居左/居中） |
| 隐私安全 | 关闭 Cortana、关闭遥测跟踪、关闭后台应用 |
| 任务栏 | 隐藏小组件、隐藏搜索框、关闭任务视图 |
| 游戏 | 关闭 Game Bar |
| 系统 | 关闭开机声音、屏幕休眠时间、修改计算机名 |
| 存储 | 修改保存位置（桌面/文档/下载迁移）、默认安装目录改到 D 盘 |
| 网络 | 设置 DNS、设置屏幕刷新率 |
| 清理 | 卸载预装应用（Xbox/新闻/天气等） |

### 📦 应用安装（12 款常用软件）

支持 **winget 优先安装 + 直链下载回退 + 官网打开兜底**，最多 3 个应用并行下载。

| 分类 | 应用 |
|------|------|
| 浏览器 | Google Chrome、QQ 浏览器 |
| 社交 | 微信、QQ |
| 办公 | WPS Office |
| 工具 | WinRAR、7-Zip |
| 娱乐 | QQ 音乐、网易云音乐、腾讯视频 |
| 游戏 | WeGame、Steam |

### 🛠 系统修复

- 浏览器主页劫持修复
- 垃圾应用扫描与卸载
- Windows KMS 激活（支持 Win7-11 全版本 + Server 2016-2025）

### 📊 性能监控

- 实时 CPU、内存、磁盘、网络监控

### 🚀 开机自启管理

- 扫描注册表自启项
- 启用/禁用/删除自启动项

## 安装与运行

### 环境要求

- Python 3.10+
- Windows 10/11（建议以**管理员身份**运行）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

### 打包 EXE

```bash
pyinstaller 桌面初始化设置工具_pyside6.spec
```

输出文件位于 `dist/系统优化工具-专业版.exe`

## 项目结构

```
├── main.py                 # 程序入口
├── config.json             # 应用列表和设置项配置
├── app_installer.py        # 应用安装模块（winget + 下载安装）
├── system_settings.py      # 系统设置模块（注册表 + PowerShell）
├── system_cleanup.py       # 系统清理模块
├── hardware_monitor.py     # 硬件监控模块
├── jihuo.py                # KMS 激活模块
├── requirements.txt        # Python 依赖
├── ui/
│   ├── main_window.py      # 主窗口（标签页 + 顶栏 + 底部状态栏）
│   ├── theme.py            # 全局主题样式（QSS）
│   ├── icon_helper.py      # 应用图标生成
│   ├── components/
│   │   ├── status_bar.py   # 底部状态栏 + 日志弹窗
│   │   ├── check_group.py  # 复选框组组件
│   │   └── info_card.py    # 信息卡片组件
│   ├── pages/
│   │   ├── settings_page.py    # 系统设置页
│   │   ├── apps_page.py        # 应用安装页
│   │   ├── cleanup_page.py     # 系统修复页
│   │   ├── monitor_page.py     # 性能监控页
│   │   └── startup_page.py     # 开机自启管理页
│   └── workers/
│       ├── base_worker.py       # Worker 基类
│       ├── settings_worker.py   # 系统设置 Worker
│       ├── install_worker.py    # 应用安装 Worker（并行）
│       ├── cleanup_worker.py    # 系统清理 Worker
│       ├── monitor_worker.py    # 性能监控 Worker
│       └── startup_worker.py    # 自启管理 Worker
```

## 技术栈

- **GUI**: PySide6 (Qt6)
- **系统操作**: winreg + PowerShell + subprocess
- **应用安装**: winget + urllib 直链下载
- **并发**: ThreadPoolExecutor（最多 3 路并行安装）
- **监控**: psutil
