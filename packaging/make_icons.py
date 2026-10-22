"""Render the app icon (drawn in code) to PNG and ICO files for packaging.

Run from the project root:  python packaging/make_icons.py
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QGuiApplication  # noqa: E402

from tidytray.ui.icons import app_pixmap  # noqa: E402


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841 - needed for painting
    out = ROOT / "packaging"
    app_pixmap(256).save(str(out / "tidytray.png"))
    # Qt's ICO writer stores one size per file, so use the largest common one.
    if not app_pixmap(256).save(str(out / "tidytray.ico"), "ICO"):
        raise SystemExit("Could not write tidytray.ico (Qt image format plugin missing)")
    print("Wrote", out / "tidytray.png", "and", out / "tidytray.ico")


if __name__ == "__main__":
    main()
