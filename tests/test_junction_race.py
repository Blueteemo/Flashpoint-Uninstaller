"""Do not cross an injected junction during HANDLE-relative Windows deletion."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(sys.platform == "win32", "Windows reparse API only")
class InPlaceReparseTests(unittest.TestCase):
    def test_junction_injection_is_detected_without_touching_outside(self):
        import ctypes
        from ctypes import wintypes
        import struct
        from flashpoint_uninstaller import windows_delete

        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            root = parent / "selected_installation"
            root.mkdir()
            candidate = root / "checked_empty"
            candidate.mkdir()
            outside = parent / "outside"
            outside.mkdir()
            evidence = outside / "keep.txt"
            evidence.write_text("important", encoding="utf8")
            identity = root.stat()
            kernel = ctypes.windll.kernel32
            kernel.CreateFileW.argtypes = (
                wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel.CloseHandle.restype = wintypes.BOOL
            kernel.DeviceIoControl.argtypes = (
                wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                ctypes.c_void_p)
            kernel.DeviceIoControl.restype = wintypes.BOOL

            substitute = ("\\??\\" + str(outside)).encode("utf-16-le")
            print_name = str(outside).encode("utf-16-le")
            names = substitute + b"\x00\x00" + print_name + b"\x00\x00"
            payload = (struct.pack("<HHHH", 0, len(substitute),
                                   len(substitute) + 2, len(print_name)) + names)
            data = struct.pack("<IHH", 0xA0000003, len(payload), 0) + payload
            buffer = ctypes.create_string_buffer(data)

            original_open = windows_delete._open_child
            injected = [False]

            def inject_before_handle_open(ntdll, parent_handle, name):
                if name == "checked_empty" and not injected[0]:
                    injected[0] = True
                    handle = kernel.CreateFileW(
                        str(candidate), 0x100, 0x7, None, 3,
                        0x02000000 | 0x00200000, None)
                    self.assertTrue(handle and handle != ctypes.c_void_p(-1).value)
                    try:
                        returned = wintypes.DWORD(0)
                        success = kernel.DeviceIoControl(
                            handle, 0x000900A4, buffer, len(data), None, 0,
                            ctypes.byref(returned), None)
                        self.assertTrue(success, "Adversarial junction conversion must really happen")
                    finally:
                        kernel.CloseHandle(handle)
                return original_open(ntdll, parent_handle, name)

            try:
                with patch.object(windows_delete, "_open_child", side_effect=inject_before_handle_open):
                    with self.assertRaises(windows_delete.UnsafeEntry):
                        windows_delete.remove_tree(
                            root, (identity.st_dev, identity.st_ino))
                self.assertTrue(injected[0])
                self.assertEqual(evidence.read_text(encoding="utf8"), "important")
            finally:
                if candidate.is_junction():
                    candidate.rmdir()  # Delete the junction object only, never its target.


if __name__ == "__main__":
    unittest.main()
