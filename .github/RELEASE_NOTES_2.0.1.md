A security and reliability update to Flashpoint Uninstaller, with a bilingual Chinese/English Windows interface.

### Highlights

- Adds Simplified Chinese and English UI text for inspection, warnings, confirmation, progress, and errors.
- Automatically chooses the Windows UI language and provides a manual language switch.
- Strengthens protected-path checks, installation identification, and directory identity verification.
- Improves interrupted-removal recovery, concurrent removal handling, and shortcut safety.
- Handles Unicode shortcut paths and related cleanup errors more reliably.

### How to use

Run `Flashpoint-Uninstaller.exe`, switch language if needed, inspect the selected installation directory, back up important data, and confirm permanent removal.

### Compatibility and limitations

- Windows 10/11 x64, standalone EXE; Python is not required.
- Designed for conventional Flashpoint Infinity / Ultimate installation layouts.
- The selected installation folder is permanently removed, including any downloads, playlists, favorites, and saves inside it.
- Other saves stored outside the installation folder are not intentionally removed.
- Validated with 60 Windows automated tests, including adversarial junction cases, Unicode paths, large directories, exclusive file locks, EXE building, and a startup smoke test. These tests do not constitute destructive certification on a complete real Flashpoint installation.

### Important

**Back up your data before removing an installation.** This update addresses the previously reported deletion safety issues. Always verify the installation path before removing files; deletion cannot be undone.