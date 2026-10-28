"""Challenge an already-open child HANDLE with an in-place junction conversion."""
from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(sys.platform == "win32", "Windows-only attack fixture")
class MidTraversalReparseTests(unittest.TestCase):
    def test_reparse_conversion_after_open_cannot_delete_outside(self):
        import ctypes
        from ctypes import wintypes
        import struct
        from flashpoint_uninstaller import windows_delete

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            installation = base / "installation"
            candidate = installation / "empty_child"
            candidate.mkdir(parents=True)
            outside = base / "outside"
            outside.mkdir()
            secret = outside / "personal.txt"
            secret.write_text("PRESERVE", encoding="utf8")
            original = installation.stat()
            kernel = ctypes.windll.kernel32
            kernel.CreateFileW.argtypes = (
                wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel.CloseHandle.restype = wintypes.BOOL
            kernel.DeviceIoControl.argtypes = (
                wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p,
                wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p)
            kernel.DeviceIoControl.restype = wintypes.BOOL
            substitute = ("\\??\\" + str(outside)).encode("utf-16-le")
            printable = str(outside).encode("utf-16-le")
            names = substitute + b"\0\0" + printable + b"\0\0"
            packed = (struct.pack("<HHHH", 0, len(substitute),
                                  len(substitute) + 2, len(printable)) + names)
            data = struct.pack("<IHH", 0xA0000003, len(packed), 0) + packed
            buffer = ctypes.create_string_buffer(data)

            original_scan = windows_delete._scan_batch
            scan_count = [0]
            injected = [False]

            def mutate_after_open(ntdll, held_directory, limit=256):
                scan_count[0] += 1
                if scan_count[0] == 2:
                    handle = kernel.CreateFileW(
                        str(candidate), 0x100, 0x7, None, 3,
                        0x02000000 | 0x00200000, None)
                    self.assertTrue(handle and handle != ctypes.c_void_p(-1).value)
                    try:
                        result = wintypes.DWORD()
                        injected[0] = bool(kernel.DeviceIoControl(
                            handle, 0x000900A4, buffer, len(data), None, 0,
                            ctypes.byref(result), None))
                    finally:
                        kernel.CloseHandle(handle)
                return original_scan(ntdll, held_directory, limit)

            try:
                with patch.object(windows_delete, "_scan_batch", side_effect=mutate_after_open):
                    try:
                        windows_delete.remove_tree(
                            installation, (original.st_dev, original.st_ino))
                    except OSError:
                        pass  # Failing closed is acceptable.
                self.assertTrue(injected[0], "The adversarial in-place conversion did not occur.")
                self.assertEqual(secret.read_text(encoding="utf8"), "PRESERVE",
                                 "Native deletion crossed the converted junction.")
            finally:
                if candidate.is_junction():
                    candidate.rmdir()  # Unlink junction itself, not the target.


if __name__ == "__main__":
    unittest.main()
