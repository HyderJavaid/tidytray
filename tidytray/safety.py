"""Guards that keep TidyTray away from folders it should never reorganize."""

from __future__ import annotations

import os
from pathlib import Path

from .paths import data_dir

_POSIX_SYSTEM_DIRS = (
    "/bin", "/boot", "/dev", "/etc", "/lib", "/lib32", "/lib64", "/libx32",
    "/opt", "/proc", "/sbin", "/snap", "/srv", "/sys", "/usr", "/var",
)


def _windows_system_dirs() -> list[Path]:
    dirs = []
    for var in ("SystemRoot", "windir", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "ProgramData"):
        value = os.environ.get(var)
        if value:
            dirs.append(Path(value))
    return dirs


def _resolved(path: Path) -> Path:
    try:
        return path.resolve()
    except (OSError, RuntimeError):
        return path.absolute()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def unsafe_reason(folder: Path | str) -> str | None:
    """Return why ``folder`` must not be organized, or ``None`` if it's fine."""
    folder = _resolved(Path(folder).expanduser())

    if folder == Path(folder.anchor):
        return "TidyTray won't organize the top level of a drive."
    home = _resolved(Path.home())
    if folder == home:
        return "TidyTray won't organize your whole home folder. Pick a folder inside it, such as Downloads."

    system_dirs = _windows_system_dirs() if os.name == "nt" else [Path(p) for p in _POSIX_SYSTEM_DIRS]
    # Some distributions keep home folders under /var (e.g. /var/home/<user>).
    inside_home = _is_within(folder, home)
    for system_dir in system_dirs if not inside_home else ():
        system_dir = _resolved(system_dir)
        if _is_within(folder, system_dir):
            return f"{folder} is a system folder. TidyTray only organizes your own folders."

    app_dir = _resolved(data_dir())
    if _is_within(folder, app_dir):
        return "That folder holds TidyTray's own history."
    return None
