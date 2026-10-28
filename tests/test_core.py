from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
from flashpoint_uninstaller.core import SafetyError, inspect_installation, remove_installation
from flashpoint_uninstaller.shortcuts import _inside


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.target = self.base / 'Flashpoint'
        (self.target / 'Launcher').mkdir(parents=True)
        (self.target / 'Manager').mkdir()
        (self.target / 'Launcher' / 'Flashpoint.exe').write_bytes(b'mock')
        (self.target / 'Manager' / 'FlashpointManager.exe').write_bytes(b'mock')

    def test_valid_installation(self):
        state = inspect_installation(self.target)
        self.assertEqual(state.path, self.target)
        self.assertGreaterEqual(len(state.markers), 2)

    def test_no_marker_no_delete(self):
        (self.target / 'Launcher' / 'Flashpoint.exe').unlink()
        with self.assertRaises(SafetyError):
            inspect_installation(self.target)

    def test_cannot_delete_home(self):
        with self.assertRaises(SafetyError):
            inspect_installation(Path.home())

    def test_cannot_delete_drive_root(self):
        root = Path(self.target.anchor)
        with self.assertRaises(SafetyError):
            inspect_installation(root)

    def test_refuses_running_inside(self):
        with self.assertRaises(SafetyError):
            inspect_installation(self.target, running_from=self.target / 'launcher.exe')

    def test_change_of_markers_blocks_deletion(self):
        state = inspect_installation(self.target)
        (self.target / 'Manager' / 'FlashpointManager.exe').unlink()
        with self.assertRaises(SafetyError):
            remove_installation(state, remover=lambda _: self.fail('must not delete'))

    def test_empty_path_refused(self):
        with self.assertRaises(SafetyError):
            inspect_installation('')

    def test_remove_only_selected_directory(self):
        elsewhere = self.base / 'keep.txt'
        elsewhere.write_text('important')
        state = inspect_installation(self.target)
        remove_installation(state)
        self.assertFalse(self.target.exists())
        self.assertEqual(elsewhere.read_text(), 'important')

    def test_symlink_root_refused(self):
        alias = self.base / 'link'
        try:
            alias.symlink_to(self.target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('Symlink creation disallowed')
        with self.assertRaises(SafetyError):
            inspect_installation(alias)

    def test_symlink_marker_refused(self):
        (self.target / 'Manager' / 'FlashpointManager.exe').unlink()
        other = self.base / 'foreign.exe'
        other.write_bytes(b'not Flashpoint')
        try:
            (self.target / 'Manager' / 'FlashpointManager.exe').symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest('Symlink creation disallowed')
        with self.assertRaises(SafetyError):
            inspect_installation(self.target)

    def test_link_target_must_be_inside(self):
        self.assertTrue(_inside(str(self.target / 'Launcher' / 'Flashpoint.exe'), self.target))
        self.assertFalse(_inside(str(self.base / 'Flashpoint-other' / 'app.exe'), self.target))


if __name__ == '__main__':
    unittest.main()
