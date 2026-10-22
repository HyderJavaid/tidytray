"""Dark theme: colors and the application style sheet."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication

from ..paths import data_dir
from ..categories import ARCHIVES, AUDIO, CODE, DOCUMENTS, IMAGES, INSTALLERS, OTHER, VIDEOS

BG = "#0f1218"
SIDEBAR = "#141922"
SURFACE = "#1a202a"
SURFACE_2 = "#222936"
SURFACE_3 = "#2a3242"
BORDER = "#2a3140"
TEXT = "#e7eaf0"
MUTED = "#8c96a8"
ACCENT = "#5b8cff"
ACCENT_HOVER = "#759fff"
ACCENT_PRESSED = "#4876e6"
SUCCESS = "#3ecf8e"
WARNING = "#f5b84a"
DANGER = "#f2667a"

CATEGORY_COLORS = {
    IMAGES: "#c084fc",
    DOCUMENTS: "#60a5fa",
    VIDEOS: "#f87171",
    AUDIO: "#34d399",
    ARCHIVES: "#fbbf24",
    INSTALLERS: "#fb923c",
    CODE: "#22d3ee",
    OTHER: "#94a3b8",
}

STYLE_SHEET = f"""
* {{
    color: {TEXT};
    outline: 0;
}}
QMainWindow, QWidget#Content, QStackedWidget, QWidget#Page {{
    background: {BG};
}}
QFrame#Sidebar {{
    background: {SIDEBAR};
    border-right: 1px solid {BORDER};
}}
QLabel#AppName {{
    font-size: 17pt;
    font-weight: 700;
}}
QLabel#Muted, QLabel#AppTagline, QLabel#PageSubtitle {{
    color: {MUTED};
}}
QLabel#PageTitle {{
    font-size: 19pt;
    font-weight: 700;
}}
QLabel#SectionTitle {{
    font-size: 12pt;
    font-weight: 600;
}}
QLabel#PrivacyNote {{
    color: {MUTED};
    font-size: 9pt;
    padding: 10px;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QPushButton {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {SURFACE_3};
}}
QPushButton:disabled {{
    color: #5c6577;
    background: {SURFACE};
    border-color: {SURFACE_2};
}}
QPushButton#PrimaryButton {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: white;
    padding: 10px 22px;
    font-size: 11pt;
}}
QPushButton#PrimaryButton:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton#PrimaryButton:pressed {{
    background: {ACCENT_PRESSED};
}}
QPushButton#PrimaryButton:disabled {{
    background: #2c3a5e;
    border-color: #2c3a5e;
    color: #8a96b5;
}}
QPushButton#GhostButton {{
    background: transparent;
    border: 1px solid transparent;
    color: {MUTED};
    padding: 6px 10px;
}}
QPushButton#GhostButton:hover {{
    color: {TEXT};
    background: {SURFACE_2};
}}
QPushButton#NavButton {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 12px;
    text-align: left;
    font-weight: 500;
    color: {MUTED};
}}
QPushButton#NavButton:hover {{
    background: {SURFACE};
    color: {TEXT};
}}
QPushButton#NavButton:checked {{
    background: {SURFACE_2};
    color: {TEXT};
    font-weight: 600;
}}
QFrame#Card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#Card:hover {{
    border-color: {SURFACE_3};
    background: {SURFACE_2};
}}
QFrame#Card[selected="true"] {{
    border: 1px solid {ACCENT};
    background: #1c2638;
}}
QFrame#Card[empty="true"] QLabel {{
    color: #5c6577;
}}
QLabel#CardCount {{
    font-size: 16pt;
    font-weight: 700;
}}
QLabel#CardTitle {{
    color: {MUTED};
    font-weight: 600;
}}
QFrame#Banner {{
    background: #17223a;
    border: 1px solid #2b3f6b;
    border-radius: 12px;
}}
QFrame#WarningBanner {{
    background: #2a2316;
    border: 1px solid #5a4620;
    border-radius: 10px;
}}
QFrame#Panel {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QLineEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}
QTableView, QTreeWidget {{
    background: {SURFACE};
    alternate-background-color: #1d2430;
    border: 1px solid {BORDER};
    border-radius: 12px;
    gridline-color: transparent;
    selection-background-color: #26334d;
    selection-color: {TEXT};
}}
QTableView::item, QTreeWidget::item {{
    padding: 6px 4px;
    border: none;
}}
QHeaderView::section {{
    background: {SURFACE};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 6px;
    font-weight: 600;
}}
QTableCornerButton::section {{
    background: {SURFACE};
    border: none;
}}
QCheckBox::indicator, QTableView::indicator, QTreeWidget::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #4a5468;
    background: {SURFACE_2};
}}
QCheckBox::indicator:checked, QTableView::indicator:checked, QTreeWidget::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url("@CHECK@");
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {SURFACE_3};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {SURFACE_3};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
    border: none;
    width: 0;
    height: 0;
}}
QStatusBar {{
    background: {SIDEBAR};
    color: {MUTED};
    border-top: 1px solid {BORDER};
}}
QProgressBar {{
    background: {SURFACE_2};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 5px;
}}
QMessageBox, QProgressDialog, QDialog {{
    background: {SURFACE};
}}
QToolTip {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 6px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor(SURFACE))
    palette.setColor(QPalette.AlternateBase, QColor("#1d2430"))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.Button, QColor(SURFACE_2))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("white"))
    palette.setColor(QPalette.ToolTipBase, QColor(SURFACE_2))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.PlaceholderText, QColor(MUTED))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#5c6577"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#5c6577"))
    app.setPalette(palette)

    font = app.font()
    if font.pointSizeF() < 10:
        font.setPointSizeF(10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    app.setStyleSheet(STYLE_SHEET.replace("@CHECK@", _checkmark_file()))


def _checkmark_file() -> str:
    """Style sheets can only load images from files, so draw the tick into TidyTray's data folder."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("white"), 4.2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline(QPolygonF([QPointF(8, 16.5), QPointF(13.5, 22), QPointF(24, 10)]))
    painter.end()
    try:
        folder = data_dir() / "ui"
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        folder = Path(tempfile.mkdtemp(prefix="tidytray-"))
    path = folder / "check.png"
    pixmap.save(str(path))
    return path.as_posix()
