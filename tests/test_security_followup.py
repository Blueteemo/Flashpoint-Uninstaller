"""Regression tests for findings raised after the 2.0.0 release."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from flashpoint_uninstaller.core import SafetyError, inspect_installation, remove_installation
from flashpoint_uninstaller.shortcuts import _shortcut_target


class FollowupSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "Flashpoint"
        (self.root / "Launcher").mkdir(parents=True)
        (self.root / "Manager").mkdir()
        (self.root / "Launcher" / "Flashpoint.exe").write_bytes(b"launcher")
        (self.root / "Manager" / "FlashpointManager.exe").write_bytes(b"manager")

    def test_data_is_not_a_strong_installation_marker(self):
        (self.root / "Manager" / "FlashpointManager.exe").unlink()
        (self.root / "Data").mkdir()
        with self.assertRaises(SafetyError):
            inspect_installation(self.root)

    def test_critical_ancestor_is_rejected(self):
        with patch.dict(os.environ, {"USERPROFILE": str(self.root / "Important")}, clear=False):
            with self.assertRaises(SafetyError):
                inspect_installation(self.root)

    def test_unreadable_parent_fails_closed(self):
        real_lstat = Path.lstat
        victim = self.base
        def reject(path, *args, **kwargs):
            if path == victim:
                raise PermissionError("cannot inspect parent")
            return real_lstat(path, *args, **kwargs)
        with patch.object(Path, "lstat", reject):
            with self.assertRaises(SafetyError):
                inspect_installation(self.root)

    def test_remove_requires_running_executable_path(self):
        snapshot = inspect_installation(self.root)
        with self.assertRaises(SafetyError):
            remove_installation(snapshot)
        self.assertTrue(self.root.exists())

    def test_partial_failure_can_retry_only_same_directory(self):
        snapshot = inspect_installation(self.root)
        def partial(path):
            (path / "Manager" / "FlashpointManager.exe").unlink()
            raise PermissionError("simulated locked file")
        with self.assertRaises(PermissionError):
            remove_installation(snapshot, running_from=Path(__file__), remover=partial)
        with self.assertRaises(SafetyError):
            inspect_installation(self.root)
        remove_installation(snapshot, running_from=Path(__file__), allow_partial=True)
        self.assertFalse(self.root.exists())

    def test_retry_rejects_replaced_path(self):
        snapshot = inspect_installation(self.root)
        alternate = self.base / "previous"
        self.root.rename(alternate)
        (self.root / "Launcher").mkdir(parents=True)
        (self.root / "Manager").mkdir()
        (self.root / "Launcher" / "Flashpoint.exe").write_bytes(b"fake")
        with self.assertRaises(SafetyError):
            remove_installation(snapshot, running_from=Path(__file__), allow_partial=True)
        self.assertTrue((self.root / "Launcher/Flashpoint.exe").exists())

    def test_quarantine_identity_checked_after_atomic_move(self):
        snapshot = inspect_installation(self.root)
        original_rename = os.rename
        previous = self.base / "old"
        unrelated = self.base / "unrelated"
        (unrelated / "Private").mkdir(parents=True)
        (unrelated / "Private" / "important.txt").write_text("keep")
        invoked = False
        def switched(src, dst):
            nonlocal invoked
            if not invoked:
                invoked = True
                original_rename(self.root, previous)
                original_rename(unrelated, self.root)
            return original_rename(src, dst)
        with patch("flashpoint_uninstaller.core.os.rename", side_effect=switched):
            with self.assertRaises(SafetyError):
                remove_installation(snapshot, running_from=Path(__file__))
        self.assertEqual((self.root / "Private/important.txt").read_text(), "keep")
        self.assertTrue((previous / "Manager/FlashpointManager.exe").exists())

    def test_shortcut_unicode_failure_is_nonfatal(self):
        with patch("flashpoint_uninstaller.shortcuts.subprocess.run",
                   side_effect=UnicodeDecodeError("utf-8", b"\\xff", 0, 1, "invalid")):
            self.assertIsNone(_shortcut_target(self.base / "Flashpoint.lnk"))


if __name__ == "__main__":
    unittest.main()
