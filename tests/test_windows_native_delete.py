"""Windows native deletion stress and compatibility tests."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "win32", "Windows native API required")
class NativeRemovalTests(unittest.TestCase):
    def test_unicode_paths_and_multiple_enumeration_batches(self):
        from flashpoint_uninstaller.windows_delete import remove_tree

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            selected = base / "Flashpoint_日本語与中文"
            data = selected / "Data" / "小游戏"
            data.mkdir(parents=True)
            for index in range(300):
                (data / f"第{index:04d}号-曲名💠.bin").write_bytes(b"test")
            keep = base / "KEEP OUTSIDE.txt"
            keep.write_text("Do not remove", encoding="utf8")
            identity = selected.stat()
            removed = [0]
            remove_tree(selected, (identity.st_dev, identity.st_ino),
                        on_deleted=lambda: removed.__setitem__(0, removed[0] + 1))
            self.assertFalse(selected.exists())
            self.assertGreaterEqual(removed[0], 302)
            self.assertEqual(keep.read_text(encoding="utf8"), "Do not remove")

    def test_locked_file_fails_closed_and_can_be_resumed(self):
        import ctypes
        from ctypes import wintypes
        from flashpoint_uninstaller.windows_delete import remove_tree

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            selected = base / "Flashpoint"
            selected.mkdir()
            locked = selected / "locked.bin"
            locked.write_bytes(b"important")
            identity = selected.stat()
            kernel = ctypes.windll.kernel32
            kernel.CreateFileW.argtypes = (
                wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel.CloseHandle.restype = wintypes.BOOL
            # This reader explicitly does NOT share DELETE.
            handle = kernel.CreateFileW(str(locked), 0x80000000, 0x1, None, 3, 0, None)
            self.assertTrue(handle and handle != ctypes.c_void_p(-1).value)
            try:
                with self.assertRaises(OSError):
                    remove_tree(selected, (identity.st_dev, identity.st_ino))
                self.assertEqual(locked.read_bytes(), b"important")
            finally:
                kernel.CloseHandle(handle)
            remove_tree(selected, (identity.st_dev, identity.st_ino))
            self.assertFalse(selected.exists())

    def test_root_identity_mismatch_is_rejected_without_removal(self):
        from flashpoint_uninstaller.windows_delete import UnsafeEntry, remove_tree

        with tempfile.TemporaryDirectory() as tmp:
            selected = Path(tmp) / "Flashpoint"
            selected.mkdir()
            (selected / "data.bin").write_bytes(b"retain")
            inode = selected.stat().st_ino
            with self.assertRaises(UnsafeEntry):
                remove_tree(selected, (selected.stat().st_dev, inode + 1))
            self.assertEqual((selected / "data.bin").read_bytes(), b"retain")


if __name__ == "__main__":
    unittest.main()
