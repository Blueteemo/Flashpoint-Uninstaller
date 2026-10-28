<p align="center">
  <img src="assets/icon_v2.png" alt="Flashpoint Uninstaller icon" width="112">
</p>
<h1 align="center">Flashpoint Uninstaller</h1>
<p align="center">A lightweight, independent Flashpoint removal utility for Windows</p>
<p align="center"><a href="README.md">简体中文</a> · <strong>English</strong></p>

> **Windows 10 / 11 · 64-bit · Standalone EXE · No Python installation required**  
> This is an independent community project, not an official Flashpoint Archive tool. See the [official uninstall guidance](https://flashpointarchive.org/faq) as well.

## Download

**[Download latest release](https://github.com/Blueteemo/Flashpoint-Uninstaller/releases/latest)** · [All releases](https://github.com/Blueteemo/Flashpoint-Uninstaller/releases)

> **Before removing anything:** Verify the chosen directory is a Flashpoint installation and back up important data. v2.0.1 addresses identified deletion safety risks, but was not destructively tested against a complete real installation.

## Features

- Detects the Windows UI language and offers a manual 简体中文 / English switch.

- Finds common Flashpoint installation locations or lets you select a directory manually.
- Checks launcher and installation markers and applies some protected-path and link checks.
- Shows the target and backup reminders, then requires acknowledgement and final confirmation.
- Removes files in the background and reports permission or file-lock errors.
- After removal, attempts to clean known `Flashpoint.lnk` shortcuts verified to point into the selected installation.
- Does not terminate processes or clean the registry.

## How to use

1. Download and run `Flashpoint-Uninstaller.exe`.
2. Check the detected path or select the **Flashpoint installation root** using Browse, then inspect the directory.
3. Back up important files, acknowledge the warning, click **Uninstall Flashpoint**, and confirm the deletion.

**Removal is permanent and cannot be undone.** Downloads, playlists, favorites, and some saves may be stored in the installation directory. Other saves may be under Windows user directories and are not intentionally removed. See the [official save-data guide](https://flashpointarchive.org/datahub/Save_Data_Locations).

If files are locked or access is denied, close Flashpoint and related processes. Run as administrator only if required. Do not launch this utility from inside the installation being removed.

## Compatibility and validation

Primarily intended for Windows 10/11 x64 and Flashpoint Infinity / Ultimate installations with the standard `Launcher/Flashpoint.exe` layout. Unrecognized historical or incomplete installations may be rejected.

v2.0.1 passed 60 Windows CI functional and safety tests, including synthetic directory removal, adversarial junction cases, executable building, and startup. **It has not been destructively tested against a complete real Flashpoint installation. Automated tests do not guarantee absolute safety.**

## Run from source

Python 3.10 or later:

~~~powershell
python -m unittest discover -s tests -v
python launch_v2.py
~~~

MIT License · [Blueteemo](https://github.com/Blueteemo)