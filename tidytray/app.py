"""Application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from . import __version__
from .ui.icons import app_icon
from .ui.main_window import MainWindow
from .ui.theme import apply_theme


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName("TidyTray")
    app.setApplicationDisplayName("TidyTray")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("tidytray")
    app.setWindowIcon(app_icon())
    apply_theme(app)

    window = MainWindow()
    window.show()
    QTimer.singleShot(0, window.recover_interrupted)
    # Optional: a folder passed on the command line is scanned (never changed).
    if len(argv) > 1 and Path(argv[1]).is_dir():
        QTimer.singleShot(0, lambda: window.load_folder(Path(argv[1])))
    return app.exec()
