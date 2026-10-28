<p align="center">
  <img src="assets/icon_v2.png" alt="Flashpoint Uninstaller 2.0 图标" width="112">
</p>

<h1 align="center">Flashpoint Uninstaller 2.0</h1>
<p align="center">独立、轻量、安全确认的 Windows Flashpoint 卸载工具</p>

> **Windows 10 / 11 · 单文件 EXE · 无需安装**  
> 非 Flashpoint Archive 官方项目。需要使用 Flashpoint Manager 的用户可优先尝试[官方卸载方式](https://flashpointarchive.org/faq)。

## 下载

**[下载 v2.0.0（Windows 64 位）](https://github.com/Blueteemo/Flashpoint-Uninstaller/releases/download/v2.0.0/Flashpoint-Uninstaller.exe)**

[查看所有版本](https://github.com/Blueteemo/Flashpoint-Uninstaller/releases)

> **安全复核提示（2026-10-28）**：发布后的自动代码审查指出若干尚未修复的删除边界问题。建议暂缓在含重要数据的安装目录上运行 v2.0.0，等待完成安全修订与新的验证版本。

## 功能

- 自动发现常见的 Flashpoint 目录；也支持手动选择已移动或自定义路径的安装。
- 检查启动器以及独立的安装特征，并拒绝删除磁盘根目录、系统/用户关键目录、链接和联接点。
- 检查路径后列出识别依据和可能需要备份的数据，要求勾选并再次确认后才会永久删除。
- 后台执行删除，界面保持响应；遇到权限不足或文件占用，会明确报告失败，不虚报成功。
- 安装目录成功移除后，只清理**指向该安装位置**的已知 `Flashpoint.lnk` 快捷方式，不进行模糊匹配。
- 不清理注册表、不关闭其他进程、不删除安装目录之外的个人数据；仅有**确认指向所选安装目录**的已知 Flashpoint 快捷方式会作为清理例外被移除。

## 使用

1. 下载并启动 `Flashpoint-Uninstaller.exe`；无需安装 Python。
2. 检查自动识别的路径，或点击“浏览…”选择 Flashpoint **主目录**，然后点击“检查目录”。
3. 备份需要保留的播放列表、收藏和存档。勾选确认框，点击“卸载 Flashpoint”，再进行最终确认。

**重要：这是永久删除操作，无法撤销。** 完整安装目录内的游戏数据、收藏及部分存档会被一并删除。部分 Flash/Silverlight/Unity 等游戏存档可能存储在用户目录而不是 Flashpoint 目录内；本工具不会清理这些外部数据。请参考[官方存档位置说明](https://flashpointarchive.org/datahub/Save_Data_Locations)。

如果提示权限不足或文件被占用，请先退出 Flashpoint 及相关进程；确有必要时，可通过 Windows 右键菜单以管理员身份重新运行卸载器。请勿在卸载器自身位于待删除目录内部时运行。

## 兼容性与安全边界

主要面向 Windows 上使用标准 `Launcher/Flashpoint.exe` 目录结构的 Flashpoint Infinity / Ultimate，包括 Flashpoint 14 系列。对缺少可识别特征的残缺或历史安装会**拒绝删除**，可以手动确认后使用文件管理器处理。不会为了兼容未知安装而盲目删除目录。

Windows 云端 CI 使用临时合成目录验证卸载前后的安全行为、失败处理与快捷方式边界，同时构建并启动检查 Windows 64 位 EXE。**这不等于在真实完整 Flashpoint 安装上完成了卸载认证**。

## 源码构建

需要 Python 3.10 或更高版本：

```powershell
python -m unittest discover -s tests -v
python launch_v2.py
```

正式 EXE 由仓库的 GitHub Actions Windows 工作流构建。项目采用 MIT License。


Made by **[Blueteemo](https://github.com/Blueteemo)**.
