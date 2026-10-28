A redesigned standalone Windows utility for removing Flashpoint when the built-in manager is unavailable or inconvenient.

### Highlights

- Modern dark interface and custom application icon.
- Finds common installations or allows manual directory selection.
- Checks the launcher, installation markers, and target path before removal.
- Displays backup reminders and requires two explicit confirmations.
- Runs deletion in the background and reports file-lock or permission errors.
- Attempts to remove only known shortcuts verified to target the installation.

### How to use

Download and run `Flashpoint-Uninstaller.exe`. Review or select the Flashpoint installation root, click **Inspect Directory**, back up data you want to keep, and confirm permanent removal.

### Compatibility and limitations

- Windows 10/11 x64; standalone EXE, no Python installation required.
- Primarily targets standard Infinity / Ultimate layouts containing `Launcher/Flashpoint.exe`.
- No registry cleanup or automatic process termination. Data outside the selected directory is not intentionally removed, except verified Flashpoint shortcuts.
- Windows CI validated synthetic installation cases, executable building, and a startup smoke test. **Full real Flashpoint installations were not destructively tested.**
- Independent project; not affiliated with Flashpoint Archive.

### Important

**Removal is permanent.** Back up downloads, playlists, favorites, and game saves before proceeding.

**Security notice (October 28, 2026):** Post-release reviews identified unresolved path-validation and deletion-race risks in v2.0. Avoid using it with important data until the planned [v2.0.1 safety update](https://github.com/Blueteemo/Flashpoint-Uninstaller/pull/2) has been reviewed and released.