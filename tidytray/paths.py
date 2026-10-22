"""Where TidyTray keeps its local data (operation history only)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "TidyTray"


def data_dir() -> Path:
    """Per-user data folder. Never requires administrator rights."""
    override = os.environ.get("TIDYTRAY_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_DIR_NAME
        return Path.home() / "AppData" / "Local" / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_DIR_NAME.lower()


def history_dir() -> Path:
    return data_dir() / "history"


def default_folder() -> Path | None:
    """The user's Downloads folder if it exists. Nothing else is scanned by default."""
    candidates = []
    xdg = os.environ.get("XDG_DOWNLOAD_DIR")
    if xdg:
        candidates.append(Path(xdg.replace("$HOME", str(Path.home()))))
    candidates.append(Path.home() / "Downloads")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None
