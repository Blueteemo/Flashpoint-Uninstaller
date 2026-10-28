<p align="center">
  <img src="assets/icon_v2.png" alt="Flashpoint Uninstaller 图标" width="112">
</p>
<h1 align="center">Flashpoint Uninstaller</h1>
<p align="center">独立、轻量的 Windows Flashpoint 卸载工具</p>
<p align="center"><strong>简体中文</strong> · <a href="README.en.md">English</a></p>

> **Windows 10 / 11 · 64 位 · 单文件 EXE · 无需安装 Python**  
> 这是独立社区项目，并非 Flashpoint Archive 官方工具。亦可参考[官方卸载说明](https://flashpointarchive.org/faq)。

## 下载

**[下载 v2.0.0](https://github.com/Blueteemo/Flashpoint-Uninstaller/releases/download/v2.0.0/Flashpoint-Uninstaller.exe)** · [查看所有版本](https://github.com/Blueteemo/Flashpoint-Uninstaller/releases)

> **安全提示（2026-10-28）**：v2.0.0 发布后的代码审核发现尚未解决的目录删除安全风险。建议暂缓在含重要数据的安装目录上使用，等待 [v2.0.1 安全修复](https://github.com/Blueteemo/Flashpoint-Uninstaller/pull/2) 完成。

## 主要功能

- 自动寻找常见 Flashpoint 安装目录，支持手动选择位置。
- 删除前检查启动器、安装特征和目标路径，拦截部分危险目录及链接路径。
- 显示目标和备份提醒，需要勾选并再次确认才能删除。
- 后台执行删除，遇到权限不足或文件占用会报告失败。
- 成功删除后，尝试清理已确认指向该安装位置的 `Flashpoint.lnk` 快捷方式。
- 不自动关闭进程，也不清理注册表。

## 使用方法

1. 下载并启动 `Flashpoint-Uninstaller.exe`。
2. 检查识别出的路径，或点击“浏览…”选择 Flashpoint **安装主目录**，然后点击“检查目录”。
3. 备份重要数据、阅读提示、勾选确认框，再点击“卸载 Flashpoint”并完成最终确认。

**删除永久生效、无法撤销。** 下载内容、播放列表、收藏和部分存档可能在安装目录内。部分游戏存档位于 Windows 用户目录，本工具不主动清理。参见[官方存档位置说明](https://flashpointarchive.org/datahub/Save_Data_Locations)。

遇到权限不足或文件被占用时，请先关闭 Flashpoint 及相关进程；必要时以管理员身份运行卸载器。不要从待删除目录内部运行卸载器。

## 兼容性与验证

主要面向 Windows 10/11 64 位系统，以及采用标准 `Launcher/Flashpoint.exe` 结构的 Flashpoint Infinity / Ultimate。不能充分识别的历史版本或残缺安装可能被拒绝。

v2.0.0 通过了 Windows 云端单元测试、合成目录测试、EXE 构建与启动检查；**并未在完整真实的 Flashpoint 安装上进行破坏性卸载测试，也不能视为已解决发布后的安全审核意见**。

## 从源码运行

需要 Python 3.10 或更高版本：

~~~powershell
python -m unittest discover -s tests -v
python launch_v2.py
~~~

MIT License · [Blueteemo](https://github.com/Blueteemo)