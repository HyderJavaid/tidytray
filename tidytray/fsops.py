"""Low-level filesystem helpers that never overwrite or delete user data."""

from __future__ import annotations

import errno
import os
from pathlib import Path

from .categories import compound_suffix

# Errors that mean "this filesystem can't make hard links here" rather than a
# real problem with the move. FAT/exFAT drives and some network shares do this.
_NO_HARDLINK_ERRNOS = {
    getattr(errno, name)
    for name in ("EPERM", "EACCES", "EXDEV", "EMLINK", "ENOSYS", "ENOTSUP", "EOPNOTSUPP")
    if hasattr(errno, name)
}


def split_name(name: str) -> tuple[str, str]:
    """Split ``archive.tar.gz`` into ``("archive", ".tar.gz")``."""
    suffix = compound_suffix(name)
    if suffix and len(suffix) < len(name):
        return name[: -len(suffix)], suffix
    return name, ""


def unique_name(directory: Path, name: str, taken: set[str] | None = None) -> str:
    """Return ``name`` or ``name (N)`` so nothing in ``directory`` is reused.

    ``taken`` holds case-folded names already claimed by the current plan. Names
    are compared case-insensitively so plans stay safe on Windows filesystems.
    """
    taken = taken or set()
    stem, suffix = split_name(name)
    candidate = name
    counter = 1
    while candidate.casefold() in taken or os.path.lexists(directory / candidate):
        candidate = f"{stem} ({counter}){suffix}"
        counter += 1
    return candidate


def move_no_overwrite(src: Path, dst: Path) -> None:
    """Move ``src`` to ``dst``; raise ``FileExistsError`` if ``dst`` exists.

    Never copies-and-deletes, so a failure can't leave a half-written file.
    """
    if os.name == "nt":
        # On Windows os.rename refuses to replace an existing file.
        os.rename(src, dst)
        return

    # On POSIX os.rename silently replaces the target, so link first: creating a
    # hard link fails atomically if the name is taken. Then drop the old name.
    try:
        os.link(src, dst, follow_symlinks=False)
    except FileExistsError:
        raise
    except OSError as exc:
        if exc.errno not in _NO_HARDLINK_ERRNOS:
            raise
        if os.path.lexists(dst):
            raise FileExistsError(errno.EEXIST, "Destination already exists", str(dst)) from exc
        os.rename(src, dst)
        return

    try:
        os.unlink(src)
    except OSError:
        # Couldn't drop the old name; remove the new one so the file is exactly
        # where it was. Both names point at the same data, so nothing is lost.
        os.unlink(dst)
        raise


def same_file(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def describe_error(exc: BaseException) -> str:
    if isinstance(exc, PermissionError):
        return "Permission denied"
    if isinstance(exc, FileNotFoundError):
        return "File no longer exists"
    if isinstance(exc, FileExistsError):
        return "A file with that name already exists"
    if isinstance(exc, OSError) and exc.strerror:
        return exc.strerror
    return str(exc) or exc.__class__.__name__
