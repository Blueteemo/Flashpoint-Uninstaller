"""Windows-only, handle-relative recursive removal.

Each child is opened by *one component* relative to a held parent HANDLE.
FILE_OPEN_REPARSE_POINT makes a junction the opened object, never its target.
All queries, recursion and deletion use those handles; a path swap cannot
redirect deletion outside the confirmed root.

This module is intentionally separate from installation identification.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
from typing import Callable


READ_ATTR = 0x80
LIST_DIRECTORY = 0x0001
DELETE = 0x00010000
SYNCHRONIZE = 0x00100000
SHARE_READ = 0x0001
FILE_OPEN = 1
FILE_SYNCHRONOUS_IO_NONALERT = 0x20
FILE_OPEN_REPARSE_POINT = 0x00200000
FILE_ATTRIBUTE_DIRECTORY = 0x10
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FLAG_BACKUP_SEMANTICS = 0x02000000
FLAG_OPEN_REPARSE_POINT = 0x00200000
STATUS_NO_MORE_FILES = 0x80000006


class UnsafeEntry(OSError):
    """Refuse ambiguous or reparse-backed data instead of traversing it."""


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.USHORT),
        ("MaximumLength", wintypes.USHORT),
        ("Buffer", wintypes.LPWSTR),
    ]


class OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.ULONG),
        ("RootDirectory", wintypes.HANDLE),
        ("ObjectName", ctypes.POINTER(UNICODE_STRING)),
        ("Attributes", wintypes.ULONG),
        ("SecurityDescriptor", ctypes.c_void_p),
        ("SecurityQualityOfService", ctypes.c_void_p),
    ]


class IO_STATUS_BLOCK(ctypes.Structure):
    _fields_ = [("Status", ctypes.c_void_p),
                ("Information", ctypes.c_size_t)]


class FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
    _fields_ = [("FileAttributes", wintypes.DWORD),
                ("ReparseTag", wintypes.DWORD)]


class FILE_ID_INFO(ctypes.Structure):
    _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong),
                ("FileId", ctypes.c_ubyte * 16)]


def _api():
    if os.name != "nt":
        raise OSError("Handle-relative deletion is only available on Windows.")
    kernel = ctypes.windll.kernel32
    ntdll = ctypes.windll.ntdll
    kernel.CreateFileW.argtypes = (
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    )
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.GetFileInformationByHandleEx.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    )
    kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
    kernel.SetFileInformationByHandle.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    )
    kernel.SetFileInformationByHandle.restype = wintypes.BOOL
    ntdll.NtCreateFile.argtypes = (
        ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
        ctypes.POINTER(OBJECT_ATTRIBUTES), ctypes.POINTER(IO_STATUS_BLOCK),
        ctypes.c_void_p, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG,
        wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG,
    )
    ntdll.NtCreateFile.restype = ctypes.c_long
    ntdll.NtQueryDirectoryFile.argtypes = (
        wintypes.HANDLE, wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.POINTER(IO_STATUS_BLOCK), ctypes.c_void_p, wintypes.ULONG,
        ctypes.c_int, wintypes.BOOLEAN, ctypes.c_void_p, wintypes.BOOLEAN,
    )
    ntdll.NtQueryDirectoryFile.restype = ctypes.c_long
    return kernel, ntdll


def _valid(handle) -> bool:
    return bool(handle) and handle != ctypes.c_void_p(-1).value


def _close(kernel, handle) -> None:
    if _valid(handle):
        kernel.CloseHandle(handle)


def _attributes(kernel, handle) -> int:
    record = FILE_ATTRIBUTE_TAG_INFO()
    if not kernel.GetFileInformationByHandleEx(
            handle, 9, ctypes.byref(record), ctypes.sizeof(record)):
        raise ctypes.WinError()
    if record.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT:
        raise UnsafeEntry("Refusing to follow a reparse point inside the installation.")
    return record.FileAttributes


def _check_root_identity(kernel, handle, inode: int) -> None:
    file_id = FILE_ID_INFO()
    if not kernel.GetFileInformationByHandleEx(
            handle, 18, ctypes.byref(file_id), ctypes.sizeof(file_id)):
        raise ctypes.WinError()
    observed = int.from_bytes(bytes(file_id.FileId), "little")
    # Python's st_ino may be represented by a legacy 64-bit file index on
    # older Windows builds, or by the newer 128-bit file ID.
    if not inode or inode not in (observed, observed & ((1 << 64) - 1)):
        raise UnsafeEntry("Staging directory identity differs from the inspected installation.")


def _open_root(kernel, path: Path):
    access = LIST_DIRECTORY | READ_ATTR | DELETE | SYNCHRONIZE
    handle = kernel.CreateFileW(
        str(path), access, SHARE_READ, None, 3,
        FLAG_BACKUP_SEMANTICS | FLAG_OPEN_REPARSE_POINT, None,
    )
    if not _valid(handle):
        raise ctypes.WinError()
    return handle


def _open_child(ntdll, parent, name: str):
    if not name or name in (".", "..") or any(ch in name for ch in ("/", "\\", ":", "\x00")):
        raise UnsafeEntry("Invalid directory entry in an installation.")
    # UNICODE_STRING.Length counts UTF-16 *bytes*, not Python code points.
    # Non-BMP characters (e.g. emoji in game filenames) use surrogate pairs.
    utf16_length = len(name.encode("utf-16-le"))
    if utf16_length >= 0xfffe:
        raise UnsafeEntry("Directory entry name exceeds Windows UNICODE_STRING limits.")
    name_buffer = ctypes.create_unicode_buffer(name)
    unicode_name = UNICODE_STRING(
        Length=utf16_length,
        MaximumLength=utf16_length + 2,
        Buffer=ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    attrs = OBJECT_ATTRIBUTES(
        Length=ctypes.sizeof(OBJECT_ATTRIBUTES),
        RootDirectory=parent,
        ObjectName=ctypes.pointer(unicode_name),
        Attributes=0x40,  # OBJ_CASE_INSENSITIVE
        SecurityDescriptor=None,
        SecurityQualityOfService=None,
    )
    result = wintypes.HANDLE()
    ios = IO_STATUS_BLOCK()
    access = LIST_DIRECTORY | READ_ATTR | DELETE | SYNCHRONIZE
    code = ntdll.NtCreateFile(
        ctypes.byref(result), access, ctypes.byref(attrs), ctypes.byref(ios),
        None, 0, SHARE_READ, FILE_OPEN,
        FILE_SYNCHRONOUS_IO_NONALERT | FILE_OPEN_REPARSE_POINT,
        None, 0,
    )
    if code != 0 or not _valid(result.value):
        raise UnsafeEntry(f"Cannot open verified child entry {name!r}: NTSTATUS 0x{code & 0xffffffff:08X}")
    return result.value


def _scan_batch(ntdll, handle, limit: int = 256) -> list[str]:
    """Enumerate directly on the directory handle, never via a pathname."""
    names: list[str] = []
    buffer = ctypes.create_string_buffer(65536)
    ios = IO_STATUS_BLOCK()
    for index in range(limit):
        code = ntdll.NtQueryDirectoryFile(
            handle, None, None, None, ctypes.byref(ios),
            buffer, len(buffer), 12, True, None, index == 0,
        )
        unsigned = code & 0xffffffff
        if unsigned == STATUS_NO_MORE_FILES:
            break
        if code != 0:
            raise UnsafeEntry(f"Cannot safely enumerate installation: NTSTATUS 0x{unsigned:08X}")
        if ios.Information < 12:
            raise UnsafeEntry("Directory enumeration returned truncated data.")
        name_len = int.from_bytes(buffer.raw[8:12], "little")
        if name_len % 2 or name_len > ios.Information - 12:
            raise UnsafeEntry("Directory entry has an invalid name length.")
        name = buffer.raw[12:12 + name_len].decode("utf-16-le", errors="strict")
        if name not in (".", ".."):
            names.append(name)
    return names


class _DISPOSITION(ctypes.Structure):
    _fields_ = [("DeleteFile", wintypes.BOOL)]


def _mark_for_deletion(kernel, handle) -> None:
    request = _DISPOSITION(True)
    if not kernel.SetFileInformationByHandle(
            handle, 4, ctypes.byref(request), ctypes.sizeof(request)):
        raise ctypes.WinError()


def remove_tree(
    root: Path,
    expected_identity: tuple[int, int],
    on_deleted: Callable[[], None] | None = None,
) -> None:
    """Delete only objects opened relative to the verified staging HANDLE.

    If anything changes unexpectedly or becomes a reparse point, stop. The
    caller owns restoration of partially removed data and the user warning.
    """
    kernel, ntdll = _api()
    handle = _open_root(kernel, root)
    try:
        _attributes(kernel, handle)
        _check_root_identity(kernel, handle, expected_identity[1])

        def visit(directory, depth: int = 0) -> None:
            if depth > 256:
                raise UnsafeEntry("Installation nesting exceeds safe traversal depth.")
            while True:
                batch = _scan_batch(ntdll, directory)
                if not batch:
                    return
                for name in batch:
                    child = _open_child(ntdll, directory, name)
                    try:
                        flags = _attributes(kernel, child)
                        if flags & FILE_ATTRIBUTE_DIRECTORY:
                            visit(child, depth + 1)
                        # This deletion targets the HELD child object, not a
                        # pathname that could have been redirected.
                        _mark_for_deletion(kernel, child)
                    finally:
                        _close(kernel, child)
                    if on_deleted is not None:
                        on_deleted()

        visit(handle)
        _mark_for_deletion(kernel, handle)
    finally:
        _close(kernel, handle)
    if on_deleted is not None:
        on_deleted()
