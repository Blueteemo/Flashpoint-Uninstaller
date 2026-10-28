"""Windows regression for in-place junction conversion during directory traversal."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == 'win32', 'Windows reparse API only')
class InPlaceReparseTests(unittest.TestCase):
    def test_existing_open_directory_cannot_become_junction(self):
        import ctypes
        from ctypes import wintypes
        import struct
        from flashpoint_uninstaller.core import _hold_directory

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / 'checked_empty'
            candidate.mkdir()
            outside = root / 'outside'
            outside.mkdir()
            (outside / 'keep.txt').write_text('important', encoding='utf8')

            kernel = ctypes.windll.kernel32
            kernel.CreateFileW.argtypes = (
                wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel.CloseHandle.restype = wintypes.BOOL
            kernel.DeviceIoControl.argtypes = (
                wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                ctypes.c_void_p, wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p)
            kernel.DeviceIoControl.restype = wintypes.BOOL

            # Mount-point reparse data (substitute and print names, UTF-16LE).
            substitute = ('\\\\??\\' + str(outside)).encode('utf-16-le')
            print_name = str(outside).encode('utf-16-le')
            path_bytes = substitute + b'\x00\x00' + print_name + b'\x00\x00'
            payload = struct.pack('<HHHH', 0, len(substitute),
                                  len(substitute) + 2, len(print_name)) + path_bytes
            blob = struct.pack('<IHH', 0xA0000003, len(payload), 0) + payload
            buffer = ctypes.create_string_buffer(blob)
            handle = None
            try:
                with _hold_directory(candidate):
                    # FILE_WRITE_ATTRIBUTES, SHARE_READ|WRITE|DELETE
                    handle = kernel.CreateFileW(
                        str(candidate), 0x100, 0x7, None, 3,
                        0x02000000 | 0x00200000, None)
                    if not handle or handle == ctypes.c_void_p(-1).value:
                        handle = None
                    if handle is not None:
                        returned = wintypes.DWORD(0)
                        applied = kernel.DeviceIoControl(
                            handle, 0x000900A4, buffer, len(blob), None, 0,
                            ctypes.byref(returned), None)
                        self.assertFalse(applied,
                            'A checked directory was converted into a junction while locked')
            finally:
                if handle is not None:
                    kernel.CloseHandle(handle)
                # If the assertion failed, remove only the junction itself.
                if candidate.is_junction():
                    candidate.rmdir()
            # Positive control: confirm the request is a *valid* in-place
            # junction conversion when the tested lock is no longer held.
            unlocked = kernel.CreateFileW(
                str(candidate), 0x100, 0x7, None, 3, 0x02000000 | 0x00200000, None)
            if not unlocked or unlocked == ctypes.c_void_p(-1).value:
                self.skipTest('Windows runner does not grant reparse modification access')
            try:
                returned = wintypes.DWORD(0)
                success = kernel.DeviceIoControl(
                    unlocked, 0x000900A4, buffer, len(blob), None, 0,
                    ctypes.byref(returned), None)
                if not success:
                    self.skipTest('Windows runner rejected unlocked FSCTL_SET_REPARSE_POINT')
            finally:
                kernel.CloseHandle(unlocked)
                if candidate.is_junction():
                    candidate.rmdir()
            self.assertEqual((outside / 'keep.txt').read_text(encoding='utf8'), 'important')


if __name__ == '__main__':
    unittest.main()
