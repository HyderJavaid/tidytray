# TidyTray

TidyTray is a small desktop app for Windows and Linux that tidies a cluttered
Downloads folder. It sorts the files sitting directly in a folder into
**Images, Documents, Videos, Audio, Archives, Installers, Code and Other**,
shows you exactly what it will do first, and lets you undo it afterwards.

- Looks only at the folder you choose, and only at the files directly inside it. Subfolders are not entered or moved.
- Shows file counts and total sizes per category.
- Builds a plan you can review before anything changes. Nothing moves until you confirm.
- Lets you tick or untick individual files, or filter by category or name.
- Never overwrites a file. If `photo.jpg` already exists in `Images`, the incoming file becomes `photo (1).jpg`.
- Never deletes your files. The only thing it ever removes is an *empty* category folder it created itself, when you undo.
- Records every move (original path and new path) in a local history so **Undo last cleanup** can put everything back.
- Works offline. No accounts, no uploads, no background services, no administrator or root rights.

## Requirements

- Python 3.9 or newer (3.10+ recommended)
- PySide6 (installed by the steps below)

## Run it on Windows

1. Install Python from <https://www.python.org/downloads/windows/>. In the installer, tick **"Add python.exe to PATH"**.
2. Open **PowerShell** in the project folder (in File Explorer, Shift + right-click the folder, then "Open in Terminal" / "Open PowerShell window here").
3. Create a virtual environment and install the dependencies:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

   If PowerShell refuses to run `Activate.ps1`, run this once and try again:
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
   (In the classic Command Prompt use `.venv\Scripts\activate.bat` instead.)

4. Start TidyTray:

   ```powershell
   python run_tidytray.py
   ```

Next time, you only need step 3's `Activate.ps1` line and step 4.

## Run it on Linux

1. Make sure Python 3 and venv are installed. On Debian/Ubuntu: `sudo apt install python3 python3-venv`.
   On Fedora: `sudo dnf install python3`.
2. In a terminal, from the project folder:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python run_tidytray.py
   ```

   You can also pass a folder to scan straight away (it is only scanned, never changed):
   `python run_tidytray.py ~/Downloads`

If Qt complains about a missing library such as `libEGL.so.1` or the `xcb`
platform plugin, install the usual Qt runtime packages:

- Debian/Ubuntu: `sudo apt install libegl1 libgl1 libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 libfontconfig1 libdbus-1-3`
- Fedora: `sudo dnf install mesa-libEGL libxkbcommon-x11 xcb-util-cursor`

## How to use it

1. **Choose a folder.** Click **Use Downloads** or **Choose folder…**. TidyTray lists the files directly inside it. The cards show how many files and how much space each category takes. Click a card to show only that category.
2. **Pick files.** Everything is ticked at first. Untick anything you want left alone, or use **Select all / Select none** (they apply to the files currently shown). Double-click a row, or select rows and press Space, to toggle them.
3. **Review the plan.** Press **Review cleanup plan**. You'll see where every file will go. Names shown in amber get a number added because that name is already taken.
4. **Organize.** Press **Organize N files** and confirm. A progress window appears; **Stop after this file** stops cleanly at any time.
5. **Undo.** **Undo last cleanup** (sidebar, History page, or Ctrl+Z) puts the files from the most recent cleanup back. Press it again to undo the cleanup before that.

Keyboard shortcuts: Ctrl+O choose folder, F5 rescan, Ctrl+Z undo last cleanup, F1 about.

**Appearance:** the switch at the bottom of the sidebar picks **System** (follow your desktop's dark/light setting, the default), **Light** or **Dark**. Your choice is remembered in `settings.json` next to the history folder.

## Safety details

| Situation | What TidyTray does |
| --- | --- |
| A file with the same name already exists in the destination | Picks a free name like `report (1).pdf`. The check is atomic: on Linux the move is a hard link (which fails if the name is taken) followed by removing the old name; on Windows `rename` refuses to replace files. |
| A new file appears at the original location before you undo | The returning file is restored as `name (1).ext`; the new file is untouched. |
| Symbolic links / shortcuts to elsewhere | Listed as skipped; never followed or moved. |
| A category folder (e.g. `Images`) is itself a link or a file | Files for that category are left in place and you are told why. |
| Hidden or system files, unfinished downloads (`.crdownload`, `.part`, `.tmp`, …) | Skipped. |
| Permission denied, file vanished, disk errors | That file is reported and left where it was; the rest continue. |
| App closed, killed or the computer loses power mid-cleanup | Each move is written to the history *before* and *after* it happens (and flushed to disk). On next launch TidyTray works out which files moved and makes that cleanup undoable. Undo is resumable in the same way. |
| You pick your home folder, a drive root (`C:\`, `/`) or a system folder | TidyTray refuses to organize it. |
| Moving between drives | Never needed (category folders are inside the chosen folder). TidyTray never copies-then-deletes. |

### Where the history lives

One small JSON-lines file per cleanup, kept only on your computer:

- Windows: `%LOCALAPPDATA%\TidyTray\history\`
- Linux: `~/.local/share/tidytray/history/` (or `$XDG_DATA_HOME/tidytray/history/`)

The History page has an **Open history folder** button. Set the `TIDYTRAY_DATA_DIR`
environment variable to keep the data somewhere else.

## Running the tests

The tests only use temporary folders and disposable files; they never touch your real Downloads.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

The window tests run without a screen. On a Linux machine without a display, run
`QT_QPA_PLATFORM=offscreen python -m pytest`. In PowerShell:
`$env:QT_QPA_PLATFORM="offscreen"; python -m pytest`.

A few tests are skipped where they can't apply:

- The permission-error tests are skipped on Windows and when run as root (root ignores file permissions).
- The symbolic-link tests are skipped on Windows unless Developer Mode is on (or the terminal is run as administrator), because Windows only lets those users create symlinks.

GitHub Actions (`.github/workflows/tests.yml`) runs the suite on both Ubuntu and Windows for every push.

## Manual test checklist (Windows or Linux)

Use a throwaway folder, not your real Downloads:

1. Create a folder such as `C:\Users\<you>\TidyTrayTest` or `~/TidyTrayTest` and put in a few files: `a.jpg`, `b.pdf`, `c.zip`, `setup.exe`, `notes.txt`, `song.mp3`, and an unfinished-download name like `movie.mp4.crdownload`.
2. Inside it, create a folder `Images` containing a file `a.jpg` (to force a name clash).
3. Start TidyTray, **Choose folder…**, pick the test folder. Check the counts on the cards and that "1 item left alone" mentions the `.crdownload` file.
4. Untick `notes.txt`, press **Review cleanup plan**. Confirm `a.jpg` will go to `Images/a (1).jpg` (in amber) and that nothing in the folder has changed yet.
5. Press **Organize**, then **Cancel** in the confirmation. Confirm nothing changed. Press **Organize** again and confirm.
6. Check the folder in Explorer / your file manager: files are in category folders, `notes.txt` and the `.crdownload` are untouched, and the original `Images/a.jpg` is unchanged.
7. Create a new file named `b.pdf` in the test folder, then press **Undo last cleanup**. All files return; the moved `b.pdf` comes back as `b (1).pdf`; empty category folders are removed; `Images` (which you created) stays.
8. Windows only: create a shortcut or (with Developer Mode) a symlink in the folder and confirm it's listed as skipped.
9. Interruption: put a few hundred files in the folder (for example by copying one file many times), start organizing and kill the app from Task Manager / `kill -9` while it runs. Restart TidyTray. It should say the previous cleanup was interrupted, and **Undo last cleanup** should put every moved file back.

## Downloads (no Python needed)

Ready-made packages are on the [Releases page](https://github.com/naOomeow/tidytray/releases):

| File | What it is |
| --- | --- |
| `TidyTray-<version>-windows-setup.exe` | Windows installer. Installs for your user only (no administrator rights), adds a Start menu entry, uninstall from *Settings → Apps*. |
| `TidyTray-<version>-windows-x64-portable.zip` | Windows portable. Unzip anywhere, run `TidyTray\TidyTray.exe`. |
| `tidytray_<version>_amd64.deb` | Linux installer for Debian/Ubuntu/Mint: `sudo apt install ./tidytray_<version>_amd64.deb`, then open TidyTray from the app menu or run `tidytray`. |
| `TidyTray-<version>-linux-x86_64-portable.tar.gz` | Linux portable. `tar -xzf` it anywhere and run `TidyTray/TidyTray`. |

The apps aren't code-signed, so Windows SmartScreen may warn the first time: choose *More info → Run anyway*.
The portable builds still keep history and settings in your user data folder (see "Where the history lives").

## Building the packages yourself

The GitHub Actions workflow `.github/workflows/release.yml` builds all four files, runs the tests first, starts
each built app to check it launches, and silently installs and uninstalls the Windows installer. Push a tag
(`git tag v1.0.1 && git push origin v1.0.1`) or run the **release** workflow from the Actions tab to publish a
release. Bump `__version__` in `tidytray/__init__.py` first.

To build locally, you need [PyInstaller](https://pyinstaller.org); build on the OS you are targeting.

**Linux** (needs `dpkg-deb`, present on Debian/Ubuntu):

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt pyinstaller
bash packaging/build_linux.sh
```

**Windows** (the installer step needs [Inno Setup 6](https://jrsoftware.org/isdl.php), e.g. `winget install JRSoftware.InnoSetup`):

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt pyinstaller
.\packaging\build_windows.ps1
```

Both put their output in `dist/`. `packaging/make_icons.py` regenerates `tidytray.png` / `tidytray.ico` from the icon drawn in code.

## Project layout

```
run_tidytray.py          Start the app
LICENSE                  GNU GPL v3.0
THIRD_PARTY_NOTICES.md   Licenses of bundled components
CHANGELOG.md             Release notes
tidytray/
  categories.py          Extension → category rules
  scanner.py             Read the immediate contents of one folder
  planner.py             Propose destinations; resolve name clashes (changes nothing)
  fsops.py               No-overwrite move, unique names
  organizer.py           Execute a plan and undo it
  history.py             Local append-only journal, crash recovery
  safety.py              Refuse system folders, drive roots and the home folder
  paths.py               Per-user data folder
  settings.py            Remembered preferences (theme)
  ui/                    PySide6 window, light/dark themes, icons drawn in code
tests/                   pytest suite (temporary folders only)
packaging/               Build scripts, Inno Setup script, icons, Linux .desktop file
```

To change which extensions go where, edit the lists in `tidytray/categories.py`.

## License

TidyTray is free and open-source software, licensed under the
[GNU General Public License v3.0 or later](LICENSE) (GPL-3.0-or-later).
Copyright (c) 2026 naOomeow.

You can use, study, share and change it. If you distribute it, or a modified
version, you must do so under the same license and make the source code
available. The packaged builds also include Qt for Python (PySide6, LGPL v3)
and other components listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Every package contains both files, the Windows installer shows the license
before installing, and the app's **About** button (History page, or F1) shows
the version and license.
