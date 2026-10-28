## Flashpoint Uninstaller 2.0

A safety-focused redesign of the original portable Flashpoint removal utility.

### Highlights
- New dark interface and original application icon.
- Discover common Flashpoint installation directories or select one manually.
- Validate the target and block protected directories and reparse points before deletion.
- Review backup reminders and confirm twice before permanent removal.
- Prevent removal when the confirmed installation directory has been replaced.
- Run file removal in a background thread and report failures instead of silently ignoring them.
- Only clean up known shortcuts whose target belongs to the selected installation.

### Compatibility & limitations
- Windows 10/11, x64, standalone executable; Python is not required.
- Aims at conventional Flashpoint Infinity/Ultimate layouts with `Launcher/Flashpoint.exe`.
- The executable was built and smoke-tested in Windows GitHub Actions; tests use synthetic installation directories. **Real, full Flashpoint installations were not destructively tested.**
- No registry cleanup, automatic termination of running processes, or deletion of user data outside the chosen folder.
- Back up games, playlists and saves first. Removal is permanent and cannot be undone.
- The project is independent and not affiliated with Flashpoint Archive.

The original **v1.0** release and its download URL are preserved unchanged.
