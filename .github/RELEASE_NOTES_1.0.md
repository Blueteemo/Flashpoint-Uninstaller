The original single-file Windows utility for removing Flashpoint from the default `C:\Flashpoint` folder. This is the historical first release, preserved as it was originally shipped.

### Highlights

- Standalone executable; no separate installer required.
- Requests administrator permission through Windows UAC.
- Permanently deletes the entire `C:\Flashpoint` directory after confirmation.
- Attempts to remove Flashpoint-named shortcuts from the current user's Desktop and Start Menu.
- Simple one-button removal interface.

### How to use

Run `Flashpoint-Uninstaller.exe`, approve UAC, review the confirmation, and click the red removal button.

### Compatibility and limitations

- Intended for Windows 10/11, with a **fixed** target of `C:\Flashpoint`; other installation locations are not supported.
- This version does not independently verify that the target directory is a Flashpoint installation.
- Shortcut cleanup is limited in scope, and files stored outside the target directory are not cleaned.
- The historical executable has not been rebuilt or modified.

### Important

**Deletion is permanent.** Back up games, saves, playlists, favorites, and any other files under the target folder. For newer functionality, see the [latest release](https://github.com/Blueteemo/Flashpoint-Uninstaller/releases).