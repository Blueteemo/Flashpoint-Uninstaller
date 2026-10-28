"""User-facing Chinese/English strings for the portable Windows GUI.

Deletion policy stays in core.py. Translation happens only at the UI boundary.
No language setting is written to disk.
"""
from __future__ import annotations

import locale
import os
import sys


LANGUAGES = ("zh", "en")
LANGUAGE_NAMES = {"zh": "简体中文", "en": "English"}

STRINGS: dict[str, dict[str, str]] = {
    "app_title": {"zh": "Flashpoint Uninstaller 2.0.1", "en": "Flashpoint Uninstaller 2.0.1"},
    "language": {"zh": "语言", "en": "Language"},
    "heading": {"zh": "安全移除 Flashpoint", "en": "Remove Flashpoint safely"},
    "subtitle": {"zh": "独立运行 · 识别安装目录 · 删除前确认", "en": "Standalone · Verify installation · Confirm before removal"},
    "path_label": {"zh": "安装目录", "en": "Installation folder"},
    "browse": {"zh": "浏览…", "en": "Browse…"},
    "status_initial": {"zh": "请先检查目标目录，确认它属于 Flashpoint。", "en": "Inspect the target folder to confirm it belongs to Flashpoint."},
    "details_initial": {"zh": "检测结果会显示在这里。\n\n仅清理选定安装目录与经过验证的 Flashpoint 快捷方式。", "en": "Inspection results will appear here.\n\nOnly the selected installation and verified Flashpoint shortcuts are removed."},
    "ack": {"zh": "我已核对路径，并理解游戏数据和部分存档可能永久丢失", "en": "I checked the path and understand that game data and some saves may be lost permanently"},
    "inspect": {"zh": "检查目录", "en": "Inspect folder"},
    "uninstall": {"zh": "卸载 Flashpoint", "en": "Uninstall Flashpoint"},
    "footer": {"zh": "请先备份收藏、播放列表和存档；删除后无法撤销。", "en": "Back up favorites, playlists, and saves first. Removal cannot be undone."},
    "status_bad": {"zh": "无法通过安全检查", "en": "Safety check failed"},
    "status_good": {"zh": "已识别 Flashpoint 安装目录", "en": "Flashpoint installation identified"},
    "target": {"zh": "目标", "en": "Target"},
    "markers": {"zh": "识别依据", "en": "Identification markers"},
    "backups": {"zh": "可能值得备份", "en": "Data to consider backing up"},
    "no_backups": {"zh": "未在常见位置发现数据目录；不代表没有存档。", "en": "No common data folders found. This does not mean there are no saves."},
    "external_saves": {"zh": "注意：部分游戏存档位于安装目录以外，本工具不会主动清理。", "en": "Note: some saves are outside this installation and will not be intentionally removed."},
    "browse_title": {"zh": "选择 Flashpoint 的主目录", "en": "Select the Flashpoint installation root"},
    "confirm_title": {"zh": "最终确认", "en": "Final confirmation"},
    "confirm_body": {"zh": "将永久删除以下目录的全部内容：\n\n{path}\n\n此操作无法撤销，可能包含游戏下载、收藏和存档。\n\n确定继续？", "en": "All contents of this folder will be permanently removed:\n\n{path}\n\nThis cannot be undone. Downloads, favorites, and saves may be lost.\n\nContinue?"},
    "status_working": {"zh": "正在删除，请不要关闭程序……", "en": "Removing files. Do not close this window…"},
    "status_failed": {"zh": "移除未完成", "en": "Removal incomplete"},
    "status_retry": {"zh": "移除未完成，可再次确认并重试", "en": "Removal incomplete. You can review and retry."},
    "failed_title": {"zh": "操作失败", "en": "Operation failed"},
    "failed_help": {"zh": "请确认相关程序已关闭、权限足够。", "en": "Close related programs and check permissions."},
    "retry_help": {"zh": "剩余目录身份未变，可重新勾选确认后再次尝试。", "en": "The remaining directory has the same identity; review and confirm again to retry."},
    "status_done": {"zh": "安装目录已删除", "en": "Installation folder removed"},
    "done_details": {"zh": "已删除安装目录。\n已清理 {count} 个经过目标验证的快捷方式。", "en": "Installation folder removed.\nRemoved {count} verified shortcut(s)."},
    "shortcuts_failed": {"zh": "\n快捷方式处理失败：{count} 个", "en": "\nShortcut cleanup errors: {count}"},
    "shortcuts_exception": {"zh": "快捷方式清理异常：{error}", "en": "Shortcut cleanup error: {error}"},
    "done_title": {"zh": "完成", "en": "Completed"},
    "done_message": {"zh": "Flashpoint 安装目录已删除。", "en": "The Flashpoint installation folder was removed."},
    "busy_title": {"zh": "正在卸载", "en": "Uninstall in progress"},
    "busy_close": {"zh": "删除操作尚未结束，请勿关闭窗口。", "en": "Removal is still in progress. Do not close this window."},
}

# Existing core logic reports Chinese diagnostic strings. Keep its safety logic
# unchanged; translate errors only when showing them in the English interface.
ERROR_TRANSLATIONS = {
    "暂存目录身份发生变化，已停止删除。": "Staging folder identity changed; deletion stopped.",
    "目录包含重解析点，已停止删除。": "Folder contains a reparse point; deletion stopped.",
    "目标中包含链接或联接点，已停止删除。": "Target contains a symbolic link or junction; deletion stopped.",
    "快捷方式身份发生变化": "Shortcut identity changed",
    "快捷方式内容发生变化": "Shortcut content changed",
    "快捷方式大小或类型异常": "Shortcut file size or type is unexpected",
    "未选择目录。": "No folder selected.",
    "目标目录不存在。": "Target folder does not exist.",
    "不支持直接删除网络共享路径，请先在本地操作。": "Network shares cannot be removed directly. Use a local installation.",
    "拒绝删除磁盘根目录。": "Refusing to delete a drive root.",
    "拒绝删除系统 / 用户重要目录及其上层目录。": "Refusing to delete a protected system/user folder or its ancestor.",
    "无法确认磁盘类型，已拒绝删除。": "Could not identify the drive type; deletion refused.",
    "不支持从映射的网络磁盘删除 Flashpoint。": "Mapped network drives are not supported.",
    "无法验证当前磁盘类型，已拒绝删除。": "Could not verify the current drive type; deletion refused.",
    "目录路径包含符号链接或联接点，出于安全考虑不允许删除。": "Target path includes a symbolic link or junction; deletion refused.",
    "卸载器正在目标目录内运行，请先移至其他位置。": "The uninstaller is running inside the target folder. Move it elsewhere first.",
    "无法充分确认 Flashpoint 安装身份：需要启动器和管理器，或 FPSoftware + Data。": "Flashpoint installation could not be verified: requires a launcher and manager, or FPSoftware and Data.",
    "安装标记路径包含联接点，无法安全验证目标。": "An installation marker uses a junction; target verification failed.",
    "必须传入正在运行的卸载器路径，以保护目标目录。": "The running executable path is required for target protection.",
    "未完成卸载的目录身份已改变，拒绝重试。": "The partially removed directory has changed identity; retry refused.",
    "目录内容在确认后发生变化，请重新检查。": "The installation changed after confirmation. Inspect it again.",
    "正在移除所选 Flashpoint 目录……": "Removing the selected Flashpoint folder…",
    "无法安全创建临时删除目录。": "Could not safely create the temporary removal folder.",
    "移动后的目标目录与确认时不符，拒绝删除。": "The moved directory does not match the verified installation; deletion refused.",
    "安装目录已移除。": "Installation folder removed.",
    "无法建立互斥保护，已拒绝卸载。": "Could not establish exclusive removal protection; deletion refused.",
    "此安装目录已有另一卸载任务在执行。": "Another uninstall is already running for this folder.",
    "无法确认卸载互斥状态，已拒绝操作。": "Could not verify the uninstall lock; operation refused.",
    "快捷方式在检查后被替换": "Shortcut changed after inspection",
    "移动后快捷方式目标发生变化": "Shortcut target changed after moving",
    "暂存路径已存在，拒绝处理": "Staging path exists; operation refused",
    "恢复失败": "Restore failed",
}


def normalize_language(value: str | None) -> str:
    """Use Simplified Chinese for Chinese UI locales; English otherwise."""
    return "zh" if (value or "").lower().replace("-", "_").startswith("zh") else "en"


def detect_language() -> str:
    """Read Windows user UI language; do not persist private user settings."""
    if sys.platform == "win32":
        try:
            import ctypes
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            # LANG_CHINESE is primary language ID 0x04.
            return "zh" if langid & 0x3FF == 0x04 else "en"
        except (AttributeError, OSError):
            pass
    current, _encoding = locale.getlocale()
    return normalize_language(current or os.environ.get("LANG"))


def tr(key: str, language: str, **kwargs: object) -> str:
    return STRINGS[key][language].format(**kwargs)


def translate_backend(message: object, language: str) -> str:
    """Present existing core diagnostic strings in the selected UI language."""
    result = str(message)
    if language == "en":
        for chinese, english in ERROR_TRANSLATIONS.items():
            result = result.replace(chinese, english)
        # Translate the two diagnostic prefixes containing runtime paths.
        result = result.replace("无法确认路径是否为链接，已拒绝继续：",
                                "Could not verify the path for links; operation refused: ")
        result = result.replace("清理中断，剩余数据在 ", "Cleanup interrupted; remaining data at ")
        result = result.replace("；恢复原目录失败：", "; failed to restore original folder: ")
        result = result.replace("快捷方式清理异常：", "Shortcut cleanup error: ")
        result = result.replace("清理未完成：", "Removal incomplete: ")
        result = result.replace("剩余文件位于 ", "Remaining files are at ")
        result = result.replace("。请勿盲目重新选择目录。", ". Do not select another folder blindly.")
        result = result.replace("暂存目录已不存在；请检查安装数据是否已移除。",
                                "Staging folder is gone; verify whether installation data was removed.")
        result = result.replace("无法锁定待删除的目录，已拒绝继续：",
                                "Could not lock the removal directory; operation refused: ")
        result = result.replace("无法锁定快捷方式：", "Could not lock shortcut: ")
    return result
