"""Windows-specific checks that UI-facing shortcut verification freezes content."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from flashpoint_uninstaller.shortcuts import _lock_shortcut_for_target_check


@unittest.skipUnless(sys.platform == 'win32', 'requires Windows sharing semantics')
class ShortcutHandleTests(unittest.TestCase):
    def test_write_and_rename_blocked_during_target_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            shortcut = Path(temp) / 'Flashpoint.lnk'
            shortcut.write_bytes(b'original target')
            st = shortcut.lstat()
            identity = (st.st_dev, st.st_ino)
            with _lock_shortcut_for_target_check(shortcut, identity):
                with self.assertRaises(OSError):
                    shortcut.write_bytes(b'unrelated target')
                with self.assertRaises(OSError):
                    shortcut.rename(shortcut.with_name('alternate.lnk'))
                self.assertEqual(shortcut.read_bytes(), b'original target')
            shortcut.write_bytes(b'modified only after release')
            self.assertEqual(shortcut.read_bytes(), b'modified only after release')


if __name__ == '__main__':
    unittest.main()
