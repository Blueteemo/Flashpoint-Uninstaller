"""Regression checks for UI language selection, translations and safety warnings."""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from flashpoint_uninstaller.i18n import (
    ERROR_TRANSLATIONS, LANGUAGE_NAMES, STRINGS,
    detect_language, normalize_language, tr, translate_backend,
)


class LanguageTests(TestCase):
    def test_strings_complete_in_both_languages(self):
        self.assertEqual(set(LANGUAGE_NAMES), {'zh', 'en'})
        for key, translations in STRINGS.items():
            with self.subTest(key=key):
                self.assertEqual(set(translations), {'zh', 'en'})
                self.assertTrue(translations['zh'])
                self.assertTrue(translations['en'])

    def test_locale_rules(self):
        self.assertEqual(normalize_language('zh_CN'), 'zh')
        self.assertEqual(normalize_language('zh-TW'), 'zh')
        self.assertEqual(normalize_language('en_US'), 'en')
        self.assertEqual(normalize_language('ja_JP'), 'en')
        self.assertEqual(normalize_language(None), 'en')

    def test_windows_user_ui_language_detection(self):
        # Test primary Windows language ID independent of Python locale.
        with patch('flashpoint_uninstaller.i18n.sys.platform', 'win32'), \
             patch('ctypes.windll', create=True) as windll:
            windll.kernel32.GetUserDefaultUILanguage.return_value = 0x0804
            self.assertEqual(detect_language(), 'zh')
            windll.kernel32.GetUserDefaultUILanguage.return_value = 0x0409
            self.assertEqual(detect_language(), 'en')

    def test_non_windows_locale_detection(self):
        with patch('flashpoint_uninstaller.i18n.sys.platform', 'linux'), \
             patch('flashpoint_uninstaller.i18n.locale.getlocale', return_value=('zh_CN', 'UTF-8')):
            self.assertEqual(detect_language(), 'zh')
        with patch('flashpoint_uninstaller.i18n.sys.platform', 'linux'), \
             patch('flashpoint_uninstaller.i18n.locale.getlocale', return_value=('en_US', 'UTF-8')):
            self.assertEqual(detect_language(), 'en')

    def test_confirmation_contains_path_in_both_languages(self):
        for language in ('zh', 'en'):
            with self.subTest(language=language):
                message = tr('confirm_body', language, path=r'C:\Games\Flashpoint')
                self.assertIn(r'C:\Games\Flashpoint', message)
                self.assertTrue(message.endswith('?') or message.endswith('？'))

    def test_dynamic_messages(self):
        for language in ('zh', 'en'):
            with self.subTest(language=language):
                self.assertIn('3', tr('done_details', language, count=3))
                self.assertIn('2', tr('shortcuts_failed', language, count=2))
                self.assertTrue(tr('browse_title', language))

    def test_backend_diagnostics_covered(self):
        for source, english in ERROR_TRANSLATIONS.items():
            with self.subTest(source=source):
                self.assertIn(english, translate_backend(source, 'en'))
                self.assertEqual(source, translate_backend(source, 'zh'))

    def test_backend_dynamic_error_prefixes(self):
        message = '无法确认路径是否为链接，已拒绝继续：C:\\Flashpoint (denied)'
        english = translate_backend(message, 'en')
        self.assertTrue(english.startswith('Could not verify the path for links; operation refused: '))
        self.assertIn(message.split('：', 1)[1], english)
        self.assertIn('(denied)', english)
        message = '清理中断，剩余数据在 X；恢复原目录失败：permission denied'
        translated = translate_backend(message, 'en')
        self.assertIn('Cleanup interrupted; remaining data at X', translated)
        self.assertIn('failed to restore original folder: permission denied', translated)
        self.assertNotIn('清理中断', translated)

    def test_non_destructive_language_switch(self):
        # Translating UI text does not call the deletion implementation.
        with patch('flashpoint_uninstaller.core.remove_installation') as remover:
            tr('uninstall', 'zh')
            tr('uninstall', 'en')
            translate_backend('安装目录已移除。', 'en')
            remover.assert_not_called()
