"""Local, append-only operation journal used for Undo and crash recovery.

Every organize run gets one JSON-lines file. A line is written (and flushed to
disk) *before* each move ("intent") and *after* it ("moved"), so if the app or
computer stops mid-run, the next launch can tell exactly which files moved.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .fsops import same_file
from .paths import history_dir

JOURNAL_VERSION = 1


class Journal:
    def __init__(self, path: Path):
        self.path = path

    @classmethod
    def create(cls, directory: Path, root: Path, planned: int) -> "Journal":
        directory.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        op_id = f"{now:%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"
        journal = cls(directory / f"op-{op_id}.jsonl")
        journal.append(
            {
                "type": "begin",
                "version": JOURNAL_VERSION,
                "id": op_id,
                "root": str(root),
                "started": now.isoformat(timespec="seconds"),
                "ts": time.time_ns(),  # precise ordering for runs in the same second
                "planned": planned,
            }
        )
        return journal

    def append(self, record: dict) -> None:
        line = (json.dumps(record) + "\n").encode("utf-8")
        with open(self.path, "a+b") as fh:
            # If a crash cut the previous line short, start on a fresh line.
            if fh.seek(0, os.SEEK_END) > 0:
                fh.seek(-1, os.SEEK_END)
                if fh.read(1) != b"\n":
                    line = b"\n" + line
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def records(self) -> list[dict]:
        out = []
        try:
            with open(self.path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue  # A line cut short by a crash; ignore it.
        except OSError:
            pass
        return out


@dataclass
class Move:
    source: Path
    destination: Path


@dataclass
class Operation:
    journal: Journal
    id: str = ""
    root: Path = Path()
    started: str = ""
    sequence: int = 0
    planned: int = 0
    moves: list[Move] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    created_dirs: list[Path] = field(default_factory=list)
    pending_intents: list[Move] = field(default_factory=list)
    status: str = "in_progress"  # complete | cancelled | interrupted | in_progress
    undo_started: bool = False
    undo_finished: bool = False
    restored: dict[str, str] = field(default_factory=dict)  # destination -> restored to
    restore_intents: dict[str, str] = field(default_factory=dict)

    @property
    def finished(self) -> bool:
        return self.status != "in_progress"

    @property
    def undone(self) -> bool:
        return self.undo_finished

    @property
    def undoable(self) -> bool:
        return self.finished and not self.undo_finished and len(self.remaining_moves()) > 0

    def remaining_moves(self) -> list[Move]:
        return [m for m in self.moves if str(m.destination) not in self.restored]

    @property
    def started_at(self) -> datetime | None:
        try:
            return datetime.fromisoformat(self.started)
        except ValueError:
            return None

    @classmethod
    def load(cls, journal: Journal) -> "Operation":
        op = cls(journal=journal)
        intents: dict[str, Move] = {}
        for rec in journal.records():
            kind = rec.get("type")
            if kind == "begin":
                op.id = rec.get("id", "")
                op.root = Path(rec.get("root", ""))
                op.started = rec.get("started", "")
                op.sequence = int(rec.get("ts", 0))
                op.planned = int(rec.get("planned", 0))
            elif kind == "mkdir":
                op.created_dirs.append(Path(rec["path"]))
            elif kind == "intent":
                intents[rec["src"]] = Move(Path(rec["src"]), Path(rec["dst"]))
            elif kind == "moved":
                intents.pop(rec["src"], None)
                op.moves.append(Move(Path(rec["src"]), Path(rec["dst"])))
            elif kind == "failed":
                intents.pop(rec["src"], None)
                op.failed.append((rec["src"], rec.get("error", "")))
            elif kind == "end":
                op.status = rec.get("status", "complete")
            elif kind == "undo_begin":
                op.undo_started = True
            elif kind == "restore_intent":
                op.restore_intents[rec["dst"]] = rec["target"]
            elif kind == "restored":
                op.restore_intents.pop(rec["dst"], None)
                op.restored[rec["dst"]] = rec["target"]
            elif kind == "undo_end":
                op.undo_finished = True
        op.pending_intents = list(intents.values())
        return op


def reconcile(current: Path, target: Path) -> bool:
    """After an interruption, decide whether ``current`` was moved to ``target``.

    Finishes a move that stopped between its two steps (both names pointing at
    the same file) by dropping the old name. Never removes distinct data.
    """
    current_exists = os.path.lexists(current)
    target_exists = os.path.lexists(target)
    if target_exists and not current_exists:
        return True
    if target_exists and current_exists and same_file(current, target):
        os.unlink(current)
        return True
    return False


class History:
    def __init__(self, directory: Path | None = None):
        self.directory = Path(directory) if directory else history_dir()

    def ensure(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)

    def new_journal(self, root: Path, planned: int) -> Journal:
        return Journal.create(self.directory, root, planned)

    def operations(self) -> list[Operation]:
        """All recorded operations, newest first."""
        if not self.directory.is_dir():
            return []
        ops = [Operation.load(Journal(p)) for p in self.directory.glob("op-*.jsonl")]
        ops = [op for op in ops if op.id]
        ops.sort(key=lambda op: (op.started, op.sequence, op.id), reverse=True)
        return ops

    def last_undoable(self) -> Operation | None:
        """The most recent operation that still has files to put back."""
        for op in self.operations():
            if op.moves and not op.undone:
                return op if op.undoable else None
        return None

    def recover_incomplete(self) -> list[Operation]:
        """Close out runs that were interrupted (crash, power loss, kill)."""
        recovered = []
        for op in self.operations():
            if op.finished:
                continue
            for move in op.pending_intents:
                try:
                    done = reconcile(move.source, move.destination)
                except OSError as exc:
                    done = False
                    op.journal.append({"type": "failed", "src": str(move.source), "dst": str(move.destination), "error": str(exc)})
                    continue
                if done:
                    op.journal.append({"type": "moved", "src": str(move.source), "dst": str(move.destination)})
                else:
                    op.journal.append(
                        {"type": "failed", "src": str(move.source), "dst": str(move.destination), "error": "Interrupted before the move"}
                    )
            op.journal.append({"type": "end", "status": "interrupted", "finished": datetime.now().isoformat(timespec="seconds")})
            recovered.append(Operation.load(op.journal))
        return recovered
