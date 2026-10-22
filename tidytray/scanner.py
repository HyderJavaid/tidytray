"""Scan the immediate contents of a single folder (never recursive)."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

from .categories import CATEGORIES, classify, is_partial_download


@dataclass(frozen=True)
class FileEntry:
    path: Path
    category: str
    size: int
    modified: float

    @property
    def name(self) -> str:
        return self.path.name


@dataclass(frozen=True)
class SkippedEntry:
    path: Path
    reason: str


@dataclass
class ScanResult:
    root: Path
    files: list[FileEntry] = field(default_factory=list)
    skipped: list[SkippedEntry] = field(default_factory=list)

    def by_category(self) -> dict[str, list[FileEntry]]:
        groups: dict[str, list[FileEntry]] = {c: [] for c in CATEGORIES}
        for entry in self.files:
            groups[entry.category].append(entry)
        return groups

    def summary(self) -> dict[str, tuple[int, int]]:
        """Map each category to ``(file_count, total_bytes)``."""
        return {
            category: (len(entries), sum(e.size for e in entries))
            for category, entries in self.by_category().items()
        }

    @property
    def total_size(self) -> int:
        return sum(e.size for e in self.files)


class ScanError(Exception):
    """Raised when the folder itself cannot be scanned."""


def _is_hidden(entry: os.DirEntry, st: os.stat_result) -> bool:
    if entry.name.startswith("."):
        return True
    # Windows hidden/system attributes (attribute is absent on other systems).
    attrs = getattr(st, "st_file_attributes", 0)
    return bool(attrs & (getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0) | getattr(stat, "FILE_ATTRIBUTE_SYSTEM", 0)))


def scan_folder(root: Path | str) -> ScanResult:
    """Classify the regular files directly inside ``root``.

    Subfolders are not entered. Symbolic links, shortcuts to elsewhere, hidden
    files and in-progress downloads are reported as skipped and never touched.
    """
    root = Path(root).expanduser()
    try:
        root = root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ScanError(f"The folder could not be opened: {exc}") from exc
    if not root.is_dir():
        raise ScanError(f"{root} is not a folder.")

    result = ScanResult(root=root)
    try:
        iterator = os.scandir(root)
    except PermissionError as exc:
        raise ScanError(f"You don't have permission to read {root}.") from exc
    except OSError as exc:
        raise ScanError(f"The folder could not be read: {exc.strerror or exc}") from exc

    with iterator:
        for entry in iterator:
            path = root / entry.name
            try:
                if entry.is_symlink() or (hasattr(entry, "is_junction") and entry.is_junction()):
                    result.skipped.append(SkippedEntry(path, "Symbolic link (left untouched)"))
                    continue
                st = entry.stat(follow_symlinks=False)
            except PermissionError:
                result.skipped.append(SkippedEntry(path, "Permission denied"))
                continue
            except OSError as exc:
                result.skipped.append(SkippedEntry(path, f"Could not read: {exc.strerror or exc}"))
                continue

            if stat.S_ISDIR(st.st_mode):
                continue  # Folders are not organized and not entered.
            if not stat.S_ISREG(st.st_mode):
                result.skipped.append(SkippedEntry(path, "Not a regular file"))
                continue
            if _is_hidden(entry, st):
                result.skipped.append(SkippedEntry(path, "Hidden or system file"))
                continue
            if is_partial_download(entry.name):
                result.skipped.append(SkippedEntry(path, "Download still in progress"))
                continue

            result.files.append(
                FileEntry(path=path, category=classify(entry.name), size=st.st_size, modified=st.st_mtime)
            )

    result.files.sort(key=lambda e: e.name.casefold())
    result.skipped.sort(key=lambda e: e.path.name.casefold())
    return result
