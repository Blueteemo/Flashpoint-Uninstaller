"""Fail-closed deletion regression tests for Windows and portable CI fixtures."""
from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from flashpoint_uninstaller.core import (
    PartialRemovalError, SafetyError, _hold_directory,
    inspect_installation, remove_installation,
)


class SafeDeletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'Flashpoint'
        (self.root / 'Launcher').mkdir(parents=True)
        (self.root / 'Manager').mkdir()
        (self.root / 'Launcher/Flashpoint.exe').write_bytes(b'launcher')
        (self.root / 'Manager/FlashpointManager.exe').write_bytes(b'manager')

    def test_preflight_failure_does_not_become_partial_removal(self):
        snapshot = inspect_installation(self.root)
        (self.root / 'Manager/FlashpointManager.exe').unlink()
        with self.assertRaises(SafetyError) as caught:
            remove_installation(snapshot, running_from=Path(__file__))
        self.assertNotIsInstance(caught.exception, PartialRemovalError)
        self.assertTrue(self.root.exists())

    def test_error_before_first_unlink_is_not_partial(self):
        snapshot = inspect_installation(self.root)
        with patch.object(Path, 'unlink', side_effect=PermissionError('blocked')):
            with self.assertRaises(SafetyError) as caught:
                remove_installation(snapshot, running_from=Path(__file__))
        self.assertNotIsInstance(caught.exception, PartialRemovalError)
        self.assertTrue(self.root.exists())

    def test_error_after_successful_delete_is_partial_and_restorable(self):
        snapshot = inspect_installation(self.root)
        real_unlink = Path.unlink
        counter = [0]

        def fail_on_second(path, *args, **kwargs):
            counter[0] += 1
            if counter[0] == 2:
                raise PermissionError('simulated file lock')
            return real_unlink(path, *args, **kwargs)

        with patch.object(Path, 'unlink', fail_on_second):
            with self.assertRaises(PartialRemovalError) as caught:
                remove_installation(snapshot, running_from=Path(__file__))
        self.assertIn(str(self.root), str(caught.exception))
        self.assertTrue(self.root.exists())
        self.assertGreaterEqual(counter[0], 2)

    def test_new_installation_at_old_path_does_not_hide_staging(self):
        snapshot = inspect_installation(self.root)
        real_unlink = Path.unlink
        changed = [False]

        def introduce_other_install(path, *args, **kwargs):
            if not changed[0]:
                changed[0] = True
                real_unlink(path, *args, **kwargs)
                self.root.mkdir()
                (self.root / 'important.txt').write_text('keep me')
                raise PermissionError('simulated interrupted removal')
            return real_unlink(path, *args, **kwargs)

        with patch.object(Path, 'unlink', introduce_other_install):
            with self.assertRaises(PartialRemovalError) as caught:
                remove_installation(snapshot, running_from=Path(__file__))
        self.assertEqual((self.root / 'important.txt').read_text(), 'keep me')
        message = str(caught.exception)
        self.assertIn('.Flashpoint-removing-', message)
        self.assertTrue(any(p.name.startswith('.Flashpoint-removing-')
                            for p in self.base.iterdir()))

    def test_successful_removal_leaves_no_staging(self):
        snapshot = inspect_installation(self.root)
        remove_installation(snapshot, running_from=Path(__file__))
        self.assertFalse(self.root.exists())
        self.assertFalse(any(p.name.startswith('.Flashpoint-removing-')
                             for p in self.base.iterdir()))


@unittest.skipUnless(sys.platform == 'win32', 'Windows directory handle semantics')
class WindowsDirectoryLockTests(unittest.TestCase):
    def test_rename_blocked_while_handle_is_open(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'locked'
            path.mkdir()
            with _hold_directory(path):
                with self.assertRaises(OSError):
                    path.rename(path.with_name('replaced'))
                self.assertTrue(path.exists())
            path.rename(path.with_name('replaced'))
            self.assertTrue((Path(temp) / 'replaced').exists())


if __name__ == '__main__':
    unittest.main()
