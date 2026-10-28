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



def _delete_locked_shortcut(path: Path, identity: tuple[int, int], snapshot: bytes) -> None:
    """Delete a checked file by its locked Windows handle (not by pathname)."""
    if os.name != 'nt':
        path.unlink()  # Portable test fixtures, not production Windows path.
        return
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.windll.kernel32
    kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.ReadFile.argtypes = (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p)
    kernel.ReadFile.restype = wintypes.BOOL
    kernel.SetFileInformationByHandle.argtypes = (wintypes.HANDLE, ctypes.c_int,
                                                  ctypes.c_void_p, wintypes.DWORD)
    kernel.SetFileInformationByHandle.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL

    # DELETE | FILE_READ_DATA | FILE_READ_ATTRIBUTES; share READ, not WRITE or DELETE.
    handle = kernel.CreateFileW(str(path), 0x10081, 0x1, None, 3, 0x00200000, None)
    if not handle or handle == ctypes.c_void_p(-1).value:
        raise OSError(f'无法锁定快捷方式：{path}')
    try:
        current = path.lstat()
        if ((current.st_dev, current.st_ino) != identity
                or getattr(current, 'st_file_attributes', 0) & 0x400):
            raise RuntimeError('快捷方式身份发生变化')
        contents = bytearray()
        while len(contents) <= len(snapshot):
            buf = ctypes.create_string_buffer(min(65536, len(snapshot) - len(contents) + 1))
            read = wintypes.DWORD()
            if not kernel.ReadFile(handle, buf, len(buf), ctypes.byref(read), None):
                raise ctypes.WinError()
            if not read.value:
                break
            contents.extend(buf.raw[:read.value])
        if contents != snapshot:
            raise RuntimeError('快捷方式内容发生变化')

        class Disposition(ctypes.Structure):
            _fields_ = [('DeleteFile', wintypes.BOOL)]
        request = Disposition(True)
        if not kernel.SetFileInformationByHandle(handle, 4, ctypes.byref(request), ctypes.sizeof(request)):
            raise ctypes.WinError()
    finally:
        kernel.CloseHandle(handle)


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
            if not staged.is_file() or staged.stat().st_size > 1048576:
                raise RuntimeError('快捷方式大小或类型异常')
            snapshot = staged.read_bytes()
            target_again = _shortcut_target(staged)
            if not target_again or not _inside(target_again, installation):
                raise RuntimeError('移动后快捷方式目标发生变化')
            _delete_locked_shortcut(staged, (moved.st_dev, moved.st_ino), snapshot)
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
