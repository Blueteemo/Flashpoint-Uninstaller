"""Conservatively remove only known Flashpoint shortcuts with verified targets."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import uuid


def _inside(target: str, parent: Path) -> bool:
    if not target:
        return False
    try:
        left = os.path.normcase(os.path.abspath(target.strip().strip('"')))
        right = os.path.normcase(os.path.abspath(parent))
        return os.path.commonpath((left, right)) == right
    except (ValueError, OSError):
        return False


def _shortcut_target(path: Path) -> str | None:
    # Windows Script Host only resolves shortcuts; it never executes them.
    # Pass the file as an escaped PowerShell single-quoted literal, not through a shell.
    ps_path = str(path).replace("'", "''")
    code = ("[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); "
            + f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{ps_path}'); [Console]::Out.Write($s.TargetPath)")
    try:
        proc = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', code],
            check=True, capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=12,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        return proc.stdout.strip()
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return None


def cleanup_shortcuts(installation: Path) -> tuple[list[Path], list[str]]:
    """Run only AFTER the installation itself was successfully removed.

    Unknown, renamed, and .url links are deliberately left untouched.
    """
    if sys.platform != 'win32':
        return [], []
    env = os.environ
    dirs = [
        Path.home() / 'Desktop',
        Path(env['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs' if env.get('APPDATA') else None,
        Path(env['PUBLIC']) / 'Desktop' if env.get('PUBLIC') else None,
        Path(env['ProgramData']) / 'Microsoft/Windows/Start Menu/Programs' if env.get('ProgramData') else None,
    ]
    removed: list[Path] = []
    errors: list[str] = []
    for directory in dirs:
        if directory is None:
            continue
        shortcut = directory / 'Flashpoint.lnk'
        if not shortcut.is_file() or shortcut.is_symlink():
            continue
        target = _shortcut_target(shortcut)
        if not target or not _inside(target, installation):
            continue
        # Move to an unpredictable sibling first, then verify the same
        # filesystem object and the target again. A swapped shortcut at the
        # original path must never be unlinked based on stale information.
        original = shortcut.lstat()
        if getattr(original, 'st_file_attributes', 0) & 0x400:
            continue
        staged = shortcut.with_name('.Flashpoint-remove-' + uuid.uuid4().hex + '.lnk')
        if staged.exists():
            errors.append(f'{shortcut}: 暂存路径已存在，拒绝处理')
            continue
        try:
            shortcut.rename(staged)
            moved = staged.lstat()
            if (moved.st_dev, moved.st_ino) != (original.st_dev, original.st_ino):
                raise RuntimeError('快捷方式在检查后被替换')
            target_again = _shortcut_target(staged)
            if not target_again or not _inside(target_again, installation):
                raise RuntimeError('移动后快捷方式目标发生变化')
            staged.unlink()
            removed.append(shortcut)
        except (OSError, RuntimeError) as exc:
            # Best effort restore; never erase a file we cannot revalidate.
            if staged.exists() and not shortcut.exists():
                try:
                    staged.rename(shortcut)
                except OSError as restore:
                    errors.append(f'{staged}: 恢复失败：{restore}')
            errors.append(f'{shortcut}: {exc}')
    return removed, errors
