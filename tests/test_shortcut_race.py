"""Extra regression coverage for shortcut races (disposable fixtures only)."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from flashpoint_uninstaller.shortcuts import cleanup_shortcuts


class ShortcutRaceTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.base = Path(self.work.name)
        self.desktop = self.base / "Desktop"
        self.desktop.mkdir()
        self.shortcut = self.desktop / "Flashpoint.lnk"
        self.shortcut.write_bytes(b"fake shortcut")
        self.install = self.base / "Flashpoint"
        self.target = str(self.install / "Launcher" / "Flashpoint.exe")
        self.other = str(self.base / "OtherApp" / "launcher.exe")

    def options(self):
        from contextlib import ExitStack
        ctx = ExitStack()
        ctx.enter_context(patch("flashpoint_uninstaller.shortcuts.sys.platform", "win32"))
        ctx.enter_context(patch("flashpoint_uninstaller.shortcuts.Path.home", return_value=self.base))
        ctx.enter_context(patch.dict("flashpoint_uninstaller.shortcuts.os.environ",
                                     {"APPDATA": "", "PUBLIC": "", "ProgramData": ""}))
        return ctx

    def test_matching_shortcut_removed_after_second_check(self):
        with self.options(), patch("flashpoint_uninstaller.shortcuts._shortcut_target", return_value=self.target):
            removed, errors = cleanup_shortcuts(self.install)
        self.assertEqual(removed, [self.shortcut])
        self.assertEqual(errors, [])
        self.assertFalse(self.shortcut.exists())

    def test_changed_target_is_preserved(self):
        def resolver(path):
            return self.target if path == self.shortcut else self.other
        with self.options(), patch("flashpoint_uninstaller.shortcuts._shortcut_target", side_effect=resolver):
            removed, errors = cleanup_shortcuts(self.install)
        self.assertEqual(removed, [])
        self.assertTrue(errors)
        self.assertTrue(self.shortcut.exists())

    def test_delete_failure_restores_shortcut(self):
        def failing_delete(path, *args, **kwargs):
            raise PermissionError("simulated locked shortcut")
        with self.options(), \
             patch("flashpoint_uninstaller.shortcuts._shortcut_target", return_value=self.target), \
             patch("flashpoint_uninstaller.shortcuts._delete_locked_shortcut", side_effect=failing_delete):
            removed, errors = cleanup_shortcuts(self.install)
        self.assertEqual(removed, [])
        self.assertTrue(errors)
        self.assertTrue(self.shortcut.exists())


if __name__ == "__main__":
    unittest.main()
