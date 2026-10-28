"""Conservatively remove only known Flashpoint shortcuts with verified targets."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


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
        try:
            shortcut.unlink()
            removed.append(shortcut)
        except OSError as exc:
            errors.append(f'{shortcut}: {exc}')
    return removed, errors
