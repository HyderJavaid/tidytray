"""Build a proposed organization plan. Planning never changes any file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .categories import CATEGORIES
from .fsops import unique_name
from .scanner import FileEntry, SkippedEntry


@dataclass(frozen=True)
class PlannedMove:
    source: Path
    destination: Path
    category: str
    size: int

    @property
    def renamed(self) -> bool:
        return self.source.name != self.destination.name


@dataclass
class Plan:
    root: Path
    moves: list[PlannedMove] = field(default_factory=list)
    skipped: list[SkippedEntry] = field(default_factory=list)

    @property
    def folders(self) -> list[str]:
        used = {m.category for m in self.moves}
        return [c for c in CATEGORIES if c in used]

    @property
    def total_size(self) -> int:
        return sum(m.size for m in self.moves)

    @property
    def renamed_count(self) -> int:
        return sum(1 for m in self.moves if m.renamed)


def _existing_names(directory: Path) -> set[str]:
    try:
        return {name.casefold() for name in os.listdir(directory)}
    except OSError:
        return set()


def build_plan(root: Path, entries: Iterable[FileEntry]) -> Plan:
    """Propose a destination for each selected file inside ``root/<Category>``.

    Name clashes, with existing files or within the plan, get ``name (N).ext``.
    """
    root = Path(root)
    plan = Plan(root=root)
    claimed: dict[str, set[str]] = {}
    blocked: dict[str, str | None] = {}

    for entry in entries:
        category_dir = root / entry.category
        if entry.category not in blocked:
            reason = None
            if os.path.islink(category_dir):
                reason = f"'{entry.category}' is a link to another place, so files won't be moved into it"
            elif os.path.lexists(category_dir) and not category_dir.is_dir():
                reason = f"A file named '{entry.category}' is in the way of the category folder"
            blocked[entry.category] = reason
            claimed[entry.category] = _existing_names(category_dir) if reason is None else set()

        reason = blocked[entry.category]
        if reason:
            plan.skipped.append(SkippedEntry(entry.path, reason))
            continue

        taken = claimed[entry.category]
        name = unique_name(category_dir, entry.name, taken)
        taken.add(name.casefold())
        plan.moves.append(PlannedMove(entry.path, category_dir / name, entry.category, entry.size))

    return plan
