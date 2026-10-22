# Third-party notices

TidyTray itself is free software under the GNU General Public License v3.0 or later ([LICENSE](LICENSE)); its source code is at <https://github.com/naOomeow/tidytray>. The ready-made
packages (installer, portable zip/tar.gz, .deb) also bundle the following
software, each under its own license:

| Component | License | Source |
| --- | --- | --- |
| Qt for Python (PySide6, shiboken6) and the Qt 6 libraries | GNU LGPL v3 | <https://code.qt.io/cgit/pyside/pyside-setup.git/>, <https://code.qt.io/> |
| Python runtime | Python Software Foundation License | <https://www.python.org/> |
| PyInstaller bootloader | GPL v2 with the PyInstaller bootloader exception (allows distributing bundled apps under any license) | <https://github.com/pyinstaller/pyinstaller> |

## Qt / PySide6 (LGPL v3)

Qt and PySide6 are used unmodified and are shipped as separate shared libraries
inside the `_internal` folder of the app, so you may replace them with your own
compatible build. The full license texts are available at
<https://www.gnu.org/licenses/lgpl-3.0.html> and
<https://www.gnu.org/licenses/gpl-3.0.html>, and the exact source code of the
versions used can be obtained from the Qt project links above (the version is
listed in `requirements.txt` / shown by `pip show PySide6`).
