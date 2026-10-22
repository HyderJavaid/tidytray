"""Run slow filesystem work off the UI thread so the window stays responsive."""

from __future__ import annotations

import threading
import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class TaskSignals(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)


class Task(QRunnable):
    """Calls ``fn(progress=..., should_cancel=...)`` on a worker thread."""

    def __init__(self, fn: Callable[..., Any]):
        super().__init__()
        self.fn = fn
        self.signals = TaskSignals()
        self._cancel = threading.Event()
        self.setAutoDelete(False)

    def cancel(self) -> None:
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            result = self.fn(progress=self.signals.progress.emit, should_cancel=self.is_cancelled)
        except Exception as exc:  # noqa: BLE001 - surface every error to the user
            traceback.print_exc()
            self.signals.failed.emit(str(exc) or exc.__class__.__name__)
        else:
            self.signals.finished.emit(result)
