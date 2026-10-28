<p align="center">
  <img src="assets/icon_v2.png" alt="Flashpoint Uninstaller 2.0 icon" width="112">
</p>

# Flashpoint Uninstaller 2.0 — development preview

A standalone, lightweight Windows tool for removing a Flashpoint Archive installation when the built-in manager is unavailable or inconvenient.

> **Development version (2.0.0rc1). Not a final release.** The existing [v1.0 release](https://github.com/Blueteemo/Flashpoint-Uninstaller/releases/tag/v1.0) is preserved unchanged.

## What is new

- Detects installations in common locations and supports manual directory selection.
- Requires independent Flashpoint launcher and directory markers before removal.
- Protects volume roots, Windows/user system directories, symbolic links/junctions and the running executable's directory.
- Displays the exact deletion target and common locations containing data worth backing up.
- Requires both an acknowledgement checkbox and a second confirmation dialog.
- Uses a background thread to keep the UI responsive for large installations.
- Only removes a known `Flashpoint.lnk` shortcut if it points into the selected installation; unrelated shortcuts are left alone.
- No registry cleaning, automatic termination of processes, or removal of data outside the selected installation directory.

## Important

**Deletion is permanent.** Your downloads, playlists, favorites, and some save data can reside inside the selected Flashpoint directory. Back up what you need first. Other game saves may live elsewhere and are outside the scope of this tool.

Flashpoint itself is portable. The [official FAQ](https://flashpointarchive.org/faq) explains that you can delete its folder or use the uninstall option in Flashpoint Manager. This independent tool is intended for situations where that workflow is inaccessible or inconvenient; it is not affiliated with the Flashpoint Archive team.

## Development and validation

```shell
python -m unittest discover -s tests -v
python launch_v2.py
```

GitHub Actions tests the safety checks on Windows and builds a 64-bit standalone preview executable with PyInstaller. The workflow validates synthetic test installations only; **it does not certify removal of every real Flashpoint variant.** Preview builds are uploaded as workflow artifacts, not published as stable Releases.

## Version history

- **2.0.0rc1:** in-progress redesign; new safety checks and UI.
- **1.0:** original single-file uninstaller, preserved as released.

MIT License. By Blueteemo.
