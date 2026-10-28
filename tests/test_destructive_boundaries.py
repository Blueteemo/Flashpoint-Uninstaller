"""Fail-closed deletion tests covering the actual platform deletion backend."""
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
from flashpoint_uninstaller import windows_delete


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

    def _injected_removal(self, before_mark):
        """Inject a failure at the real destructive boundary on either platform."""
        if os.name == 'nt':
            original = windows_delete._mark_for_deletion

            def wrapped(kernel, handle):
                before_mark()
                return original(kernel, handle)
            return patch.object(windows_delete, '_mark_for_deletion', wrapped)
        original = Path.unlink

        def wrapped(path, *args, **kwargs):
            before_mark()
            return original(path, *args, **kwargs)
        return patch.object(Path, 'unlink', wrapped)

    def test_preflight_failure_does_not_become_partial_removal(self):
        snapshot = inspect_installation(self.root)
        (self.root / 'Manager/FlashpointManager.exe').unlink()
        with self.assertRaises(SafetyError) as caught:
            remove_installation(snapshot, running_from=Path(__file__))
        self.assertNotIsInstance(caught.exception, PartialRemovalError)
        self.assertTrue(self.root.exists())

    def test_error_before_first_removal_is_not_partial(self):
        snapshot = inspect_installation(self.root)

        def blocked():
            raise PermissionError('simulated locked file')

        with self._injected_removal(blocked):
            with self.assertRaises(SafetyError) as caught:
                remove_installation(snapshot, running_from=Path(__file__))
        self.assertNotIsInstance(caught.exception, PartialRemovalError)
        self.assertTrue(self.root.exists())

    def test_error_after_one_removal_is_partial_and_restorable(self):
        snapshot = inspect_installation(self.root)
        count = [0]

        def blocked_on_second():
            count[0] += 1
            if count[0] == 2:
                raise PermissionError('simulated file lock')

        with self._injected_removal(blocked_on_second):
            with self.assertRaises(PartialRemovalError) as caught:
                remove_installation(snapshot, running_from=Path(__file__))
        self.assertIn(str(self.root), str(caught.exception))
        self.assertTrue(self.root.exists())
        self.assertGreaterEqual(count[0], 2)

    def test_new_installation_at_old_path_does_not_hide_staging(self):
        snapshot = inspect_installation(self.root)
        count = [0]

        def create_conflict_then_interrupt():
            count[0] += 1
            if count[0] == 1:
                self.root.mkdir()
                (self.root / 'important.txt').write_text('keep me')
            if count[0] == 2:
                raise PermissionError('simulated interrupted removal')

        with self._injected_removal(create_conflict_then_interrupt):
            with self.assertRaises(PartialRemovalError) as caught:
                remove_installation(snapshot, running_from=Path(__file__))
        self.assertEqual((self.root / 'important.txt').read_text(), 'keep me')
        self.assertIn('.Flashpoint-removing-', str(caught.exception))
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
