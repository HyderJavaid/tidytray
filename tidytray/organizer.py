"""Carry out a plan, and undo it, with every step journaled first."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from .fsops import describe_error, move_no_overwrite, unique_name
from .history import History, Operation, reconcile
from .planner import Plan
from .safety import unsafe_reason

ProgressCallback = Callable[[int, int, str], None]
CancelCheck = Callable[[], bool]

_MAX_NAME_RETRIES = 50


class UnsafeFolderError(Exception):
    pass


@dataclass
class OrganizeResult:
    operation_id: str
    moved: list[tuple[Path, Path]] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)
    cancelled: bool = False

    @property
    def renamed(self) -> int:
        return sum(1 for src, dst in self.moved if src.name != dst.name)


@dataclass
class UndoResult:
    operation_id: str
    restored: list[tuple[Path, Path]] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def renamed(self) -> int:
        """Files put back under a new name because the original name was taken."""
        return sum(1 for current, target in self.restored if current.name != target.name)


def _check_regular_file(path: Path) -> str | None:
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return "File no longer exists"
    except OSError as exc:
        return describe_error(exc)
    if stat.S_ISLNK(st.st_mode):
        return "File was replaced by a link"
    if not stat.S_ISREG(st.st_mode):
        return "No longer a regular file"
    return None


def _move_with_fresh_name(src: Path, dst: Path, on_intent: Callable[[Path], None]) -> Path:
    """Move ``src`` to ``dst`` or, if that name got taken, the next free name."""
    for _ in range(_MAX_NAME_RETRIES):
        if os.path.lexists(dst):
            dst = dst.parent / unique_name(dst.parent, dst.name)
        on_intent(dst)
        try:
            move_no_overwrite(src, dst)
            return dst
        except FileExistsError:
            continue  # Someone created that name just now; pick another.
    raise FileExistsError(f"Could not find a free name for {src.name}")


def execute_plan(
    plan: Plan,
    history: History,
    progress: ProgressCallback | None = None,
    should_cancel: CancelCheck | None = None,
) -> OrganizeResult:
    reason = unsafe_reason(plan.root)
    if reason:
        raise UnsafeFolderError(reason)

    history.ensure()
    journal = history.new_journal(plan.root, len(plan.moves))
    op_id = journal.path.stem.removeprefix("op-")
    result = OrganizeResult(operation_id=op_id)
    total = len(plan.moves)
    ready_dirs: set[Path] = set()

    for index, move in enumerate(plan.moves):
        if should_cancel and should_cancel():
            result.cancelled = True
            break
        if progress:
            progress(index, total, move.source.name)

        src = move.source
        problem = _check_regular_file(src)
        if problem:
            result.failed.append((src, problem))
            journal.append({"type": "failed", "src": str(src), "dst": str(move.destination), "error": problem})
            continue

        category_dir = move.destination.parent
        try:
            if category_dir not in ready_dirs:
                if os.path.islink(category_dir) or (os.path.lexists(category_dir) and not category_dir.is_dir()):
                    raise NotADirectoryError(f"'{category_dir.name}' is not a normal folder")
                if not os.path.lexists(category_dir):
                    os.mkdir(category_dir)
                    journal.append({"type": "mkdir", "path": str(category_dir)})
                ready_dirs.add(category_dir)

            def record_intent(dst: Path) -> None:
                journal.append({"type": "intent", "src": str(src), "dst": str(dst)})

            final = _move_with_fresh_name(src, move.destination, record_intent)
        except Exception as exc:  # noqa: BLE001 - report every failure per file
            error = str(exc) if isinstance(exc, NotADirectoryError) else describe_error(exc)
            result.failed.append((src, error))
            journal.append({"type": "failed", "src": str(src), "dst": str(move.destination), "error": error})
            continue

        journal.append({"type": "moved", "src": str(src), "dst": str(final)})
        result.moved.append((src, final))

    if progress:
        progress(total if not result.cancelled else len(result.moved) + len(result.failed), total, "")
    journal.append(
        {
            "type": "end",
            "status": "cancelled" if result.cancelled else "complete",
            "finished": datetime.now().isoformat(timespec="seconds"),
        }
    )
    return result


def undo_operation(
    history: History,
    operation: Operation | None = None,
    progress: ProgressCallback | None = None,
) -> UndoResult | None:
    """Put the files of ``operation`` (default: the last one) back where they were.

    Safe to run again after an interruption: already-restored files are skipped.
    If a file's original name is now taken, it is restored as ``name (N).ext``.
    """
    op = operation or history.last_undoable()
    if op is None or not op.undoable:
        return None

    journal = op.journal
    if not op.undo_started:
        journal.append({"type": "undo_begin", "started": datetime.now().isoformat(timespec="seconds")})
    result = UndoResult(operation_id=op.id)

    # A restore that was interrupted last time may already have happened.
    for current, target in list(op.restore_intents.items()):
        try:
            if reconcile(Path(current), Path(target)):
                journal.append({"type": "restored", "dst": current, "target": target})
                op.restored[current] = target
        except OSError:
            pass

    remaining = list(reversed(op.remaining_moves()))
    total = len(remaining)
    for index, move in enumerate(remaining):
        if progress:
            progress(index, total, move.destination.name)
        current = move.destination
        problem = _check_regular_file(current)
        if problem:
            result.failed.append((current, problem))
            journal.append({"type": "undo_failed", "dst": str(current), "error": problem})
            continue
        target_dir = move.source.parent
        if not target_dir.is_dir():
            result.failed.append((current, "The original folder no longer exists"))
            journal.append({"type": "undo_failed", "dst": str(current), "error": "Original folder missing"})
            continue

        def record_intent(target: Path) -> None:
            journal.append({"type": "restore_intent", "dst": str(current), "target": str(target)})

        try:
            final = _move_with_fresh_name(current, move.source, record_intent)
        except Exception as exc:  # noqa: BLE001
            result.failed.append((current, describe_error(exc)))
            journal.append({"type": "undo_failed", "dst": str(current), "error": describe_error(exc)})
            continue
        journal.append({"type": "restored", "dst": str(current), "target": str(final)})
        result.restored.append((current, final))

    # Remove category folders TidyTray created, but only if they are now empty.
    for directory in reversed(op.created_dirs):
        try:
            os.rmdir(directory)
        except OSError:
            pass

    if progress:
        progress(total, total, "")
    journal.append(
        {
            "type": "undo_end",
            "status": "partial" if result.failed else "complete",
            "finished": datetime.now().isoformat(timespec="seconds"),
        }
    )
    return result
