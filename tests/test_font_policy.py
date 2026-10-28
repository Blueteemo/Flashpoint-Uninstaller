"""Prevent Chinese/English UI font fallback from diverging again."""
from __future__ import annotations

import sys
import unittest

from flashpoint_uninstaller.font_policy import select_ui_font


class FontPolicyTests(unittest.TestCase):
    def test_chinese_uses_microsoft_yahei_ui_on_windows(self):
        installed = ['Segoe UI', 'Microsoft YaHei', 'Microsoft YaHei UI']
        self.assertEqual(select_ui_font('zh', installed, 'win32'), 'Microsoft YaHei UI')
        self.assertEqual(select_ui_font('en', installed, 'win32'), 'Segoe UI')

    def test_cjk_fallback_when_ui_variant_missing(self):
        installed = ['Segoe UI', 'Microsoft YaHei']
        self.assertEqual(select_ui_font('zh', installed, 'win32'), 'Microsoft YaHei')

    def test_windows_fonts_are_not_falsely_assumed_available(self):
        installed = ['Segoe UI']
        self.assertEqual(select_ui_font('zh', installed, 'win32'), 'Segoe UI')
        self.assertEqual(select_ui_font('en', installed, 'win32'), 'Segoe UI')

    def test_nonwindows_prefers_a_real_cjk_font(self):
        installed = ['DejaVu Sans', 'Noto Sans CJK SC']
        self.assertEqual(select_ui_font('zh', installed, 'linux'), 'Noto Sans CJK SC')
        self.assertEqual(select_ui_font('en', installed, 'linux'), 'DejaVu Sans')

    def test_case_insensitive_font_lookup(self):
        self.assertEqual(select_ui_font('zh', ['microsoft yahei ui'], 'win32'),
                         'microsoft yahei ui')

    def test_no_font_available_uses_named_tk_default(self):
        self.assertEqual(select_ui_font('zh', [], 'win32'), 'TkDefaultFont')

    @unittest.skipUnless(sys.platform == 'win32', 'Windows UI font integration')
    def test_detected_windows_fonts_are_installed(self):
        import tkinter as tk
        from tkinter import font as tkfont
        window = tk.Tk()
        window.withdraw()
        try:
            available = tkfont.families(window)
            for language in ('zh', 'en'):
                selected = select_ui_font(language, available, 'win32')
                self.assertTrue(selected == 'TkDefaultFont' or
                                selected.casefold() in {f.casefold() for f in available})
            selector = select_ui_font('zh', available, 'win32')
            text_font = tkfont.Font(root=window, family=selector, size=10)
            self.assertTrue(text_font.actual('family'))
            chooser = tk.ttk.Combobox(window) if hasattr(tk, 'ttk') else None
            if chooser is not None:
                chooser.configure(font=text_font)
        finally:
            window.destroy()


if __name__ == '__main__':
    unittest.main()
