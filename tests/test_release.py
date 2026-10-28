"""Additional Windows-compatible release regression tests using disposable test directories."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from flashpoint_uninstaller.core import SafetyError, inspect_installation, remove_installation
from flashpoint_uninstaller.shortcuts import cleanup_shortcuts, _inside


class ReleaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def install(self, name='Flashpoint 14 Infinity', manager=True, ultimate=False):
        root = self.base / name
        (root / 'Launcher').mkdir(parents=True)
        (root / 'Launcher/Flashpoint.exe').write_bytes(b'fixture')
        if manager:
            (root / 'Manager').mkdir()
            (root / 'Manager/FlashpointManager.exe').write_bytes(b'fixture')
        else:
            (root / 'Data/Games').mkdir(parents=True)
            (root / 'FPSoftware').mkdir()
        if ultimate:
            (root / 'Legacy/htdocs').mkdir(parents=True)
        return root

    def test_infinity_14_style(self):
        root = self.install()
        snapshot = inspect_installation(root)
        self.assertIn('Launcher/Flashpoint.exe', snapshot.markers)
        self.assertIn('Manager/FlashpointManager.exe', snapshot.markers)

    def test_ultimate_14_style_without_manager(self):
        root = self.install('Flashpoint Ultimate', manager=False, ultimate=True)
        snapshot = inspect_installation(root)
        self.assertIn('Legacy', snapshot.markers)

    def test_portable_style_without_manager(self):
        root = self.install('Flashpoint 10', manager=False)
        self.assertGreaterEqual(len(inspect_installation(root).markers), 2)

    def test_unrelated_software_refused(self):
        other = self.base / 'Unknown'
        (other / 'Data').mkdir(parents=True)
        (other / 'Launcher').mkdir()
        with self.assertRaises(SafetyError):
            inspect_installation(other)

    def test_backup_reminders_include_real_flashpoint_paths(self):
        root = self.install(ultimate=True)
        (root / 'Flash Save Backup').mkdir()
        (root / 'Data/Playlists').mkdir(parents=True)
        s = inspect_installation(root)
        self.assertIn('Flash Save Backup', s.backup_candidates)
        self.assertIn('Data/Playlists', s.backup_candidates)

    def test_delete_refuses_swapped_directory_with_same_markers(self):
        root = self.install()
        snapshot = inspect_installation(root)
        moved = self.base / 'old_install'
        root.rename(moved)
        replacement = self.install()
        with self.assertRaises(SafetyError):
            remove_installation(snapshot, remover=lambda _: self.fail('Must not delete replacement'))
        self.assertTrue((replacement / 'Launcher/Flashpoint.exe').exists())

    def test_delete_failure_does_not_touch_other_files(self):
        root = self.install()
        other = self.base / 'my_documents.txt'
        other.write_text('keep', encoding='utf-8')
        snapshot = inspect_installation(root)
        def fail(_path):
            raise PermissionError('simulated access denied')
        with self.assertRaises(PermissionError):
            remove_installation(snapshot, remover=fail)
        self.assertTrue(root.exists())
        self.assertEqual(other.read_text(encoding='utf-8'), 'keep')

    def test_snapshot_reports_missing_after_partial_failure(self):
        root = self.install()
        snapshot = inspect_installation(root)
        def partial(path):
            (path / 'Manager/FlashpointManager.exe').unlink()
            raise PermissionError('locked file')
        with self.assertRaises(PermissionError):
            remove_installation(snapshot, remover=partial)
        with self.assertRaises(SafetyError):
            inspect_installation(root)

    def test_same_parent_never_counts_as_shortcut_target(self):
        root = self.install()
        self.assertFalse(_inside(str(self.base / 'OtherApp' / 'Launcher.exe'), root))
        self.assertTrue(_inside(str(root / 'Launcher' / 'Flashpoint.exe'), root))

    def test_failed_shortcut_resolution_preserves_shortcut(self):
        root = self.install()
        desk = self.base / 'Desktop'
        desk.mkdir()
        short = desk / 'Flashpoint.lnk'
        short.write_bytes(b'fake shortcut')
        with patch('flashpoint_uninstaller.shortcuts.sys.platform', 'win32'), \
             patch('flashpoint_uninstaller.shortcuts.Path.home', return_value=self.base), \
             patch('flashpoint_uninstaller.shortcuts._shortcut_target', return_value=None):
            removed, errors = cleanup_shortcuts(root)
        self.assertEqual(removed, [])
        self.assertEqual(errors, [])
        self.assertTrue(short.exists())

    def test_shortcut_for_other_install_is_preserved(self):
        root = self.install()
        desk = self.base / 'Desktop'
        desk.mkdir()
        short = desk / 'Flashpoint.lnk'
        short.write_bytes(b'fixture')
        with patch('flashpoint_uninstaller.shortcuts.sys.platform', 'win32'), \
             patch('flashpoint_uninstaller.shortcuts.Path.home', return_value=self.base), \
             patch('flashpoint_uninstaller.shortcuts._shortcut_target', return_value=str(self.base / 'OtherFlashpoint/Launcher/Flashpoint.exe')):
            removed, _errors = cleanup_shortcuts(root)
        self.assertEqual(removed, [])
        self.assertTrue(short.exists())

    def test_shortcut_matching_selected_install_is_removed(self):
        root = self.install()
        desk = self.base / 'Desktop'
        desk.mkdir()
        short = desk / 'Flashpoint.lnk'
        short.write_bytes(b'fixture')
        with patch('flashpoint_uninstaller.shortcuts.sys.platform', 'win32'), \
             patch('flashpoint_uninstaller.shortcuts.Path.home', return_value=self.base), \
             patch('flashpoint_uninstaller.shortcuts._shortcut_target', return_value=str(root / 'Launcher/Flashpoint.exe')):
            removed, errors = cleanup_shortcuts(root)
        self.assertEqual(removed, [short])
        self.assertFalse(errors)
        self.assertFalse(short.exists())

    def test_shortcut_delete_error_is_reported(self):
        root = self.install()
        desk = self.base / 'Desktop'
        desk.mkdir()
        short = desk / 'Flashpoint.lnk'
        short.write_bytes(b'fixture')
        real_unlink = Path.unlink
        def denied(path, *args, **kwargs):
            if path == short:
                raise PermissionError('simulated blocked shortcut')
            return real_unlink(path, *args, **kwargs)
        with patch('flashpoint_uninstaller.shortcuts.sys.platform', 'win32'), \
             patch('flashpoint_uninstaller.shortcuts.Path.home', return_value=self.base), \
             patch('flashpoint_uninstaller.shortcuts._shortcut_target', return_value=str(root / 'Launcher/Flashpoint.exe')), \
             patch.object(Path, 'unlink', denied):
            removed, errors = cleanup_shortcuts(root)
        self.assertEqual(removed, [])
        self.assertEqual(len(errors), 1)
        self.assertTrue(short.exists())


if __name__ == '__main__':
    unittest.main()
