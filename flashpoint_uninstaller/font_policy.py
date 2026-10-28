"""Select installed UI fonts without bundling or redistributing font files.

Windows Chinese UI uses Microsoft YaHei UI, while English uses Segoe UI.
The language selector always uses a CJK-capable font because its options are
bilingual regardless of the currently selected application language.
"""
from __future__ import annotations

from collections.abc import Iterable


def select_ui_font(language: str, installed_families: Iterable[str],
                   platform: str = "win32") -> str:
    installed = {name.casefold(): name for name in installed_families}
    if platform == "win32":
        candidates = (
            ("Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI")
            if language == "zh" else
            ("Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei")
        )
    elif language == "zh":
        candidates = (
            "Noto Sans CJK SC", "Noto Sans SC", "WenQuanYi Micro Hei",
            "Microsoft YaHei UI", "Microsoft YaHei", "DejaVu Sans",
        )
    else:
        candidates = ("DejaVu Sans", "Liberation Sans", "Segoe UI")
    for candidate in candidates:
        if candidate.casefold() in installed:
            return installed[candidate.casefold()]
    # A named built-in Tk font is available on every Tk installation.
    return "TkDefaultFont"
