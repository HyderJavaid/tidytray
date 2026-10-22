"""Standard dark and light themes (plus "follow the system"), and the style sheet."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication

from ..categories import ARCHIVES, AUDIO, CODE, DOCUMENTS, IMAGES, INSTALLERS, OTHER, VIDEOS
from ..paths import data_dir

SYSTEM, LIGHT, DARK = "system", "light", "dark"
MODES = (SYSTEM, LIGHT, DARK)

# Neutral grays with a standard blue accent, close to the stock Windows and
# GNOME/KDE dark and light looks.
PALETTES: dict[str, dict[str, str]] = {
    DARK: {
        "bg": "#1e1e1e",
        "sidebar": "#252525",
        "surface": "#2b2b2b",
        "surface_2": "#333333",
        "surface_3": "#3f3f3f",
        "border": "#3a3a3a",
        "text": "#ececec",
        "muted": "#a6a6a6",
        "disabled": "#6e6e6e",
        "accent": "#0a6fd1",
        "accent_hover": "#1f80dd",
        "accent_pressed": "#085fb3",
        "alt_row": "#2f2f2f",
        "selection": "#474747",
        "card_selected": "#353535",
        "banner": "#2b2b2b",
        "banner_border": "#4a4a4a",
        "warning": "#e5a50a",
        "warning_bg": "#3a3220",
        "warning_border": "#6b5a2a",
        "indicator_border": "#6a6a6a",
        "primary_disabled": "#3a3a3a",
        "primary_disabled_text": "#8a8a8a",
    },
    LIGHT: {
        "bg": "#f5f5f5",
        "sidebar": "#ebebeb",
        "surface": "#ffffff",
        "surface_2": "#f0f0f0",
        "surface_3": "#e2e2e2",
        "border": "#d4d4d4",
        "text": "#1c1c1c",
        "muted": "#5c5c5c",
        "disabled": "#a3a3a3",
        "accent": "#0a6fd1",
        "accent_hover": "#1f80dd",
        "accent_pressed": "#085fb3",
        "alt_row": "#f8f8f8",
        "selection": "#e3e3e3",
        "card_selected": "#f0f0f0",
        "banner": "#ffffff",
        "banner_border": "#cfcfcf",
        "warning": "#9a6700",
        "warning_bg": "#fff6dc",
        "warning_border": "#ecd18a",
        "indicator_border": "#8f8f8f",
        "primary_disabled": "#d2d2d2",
        "primary_disabled_text": "#f7f7f7",
    },
}

CATEGORY_COLORS: dict[str, dict[str, str]] = {
    DARK: {
        IMAGES: "#c084fc",
        DOCUMENTS: "#60a5fa",
        VIDEOS: "#f87171",
        AUDIO: "#34d399",
        ARCHIVES: "#fbbf24",
        INSTALLERS: "#fb923c",
        CODE: "#22d3ee",
        OTHER: "#a3a3a3",
    },
    LIGHT: {
        IMAGES: "#9333ea",
        DOCUMENTS: "#2563eb",
        VIDEOS: "#dc2626",
        AUDIO: "#059669",
        ARCHIVES: "#b45309",
        INSTALLERS: "#c2410c",
        CODE: "#0e7490",
        OTHER: "#6b6b6b",
    },
}

_active = DARK
_desktop_window_lightness: int | None = None  # the desktop's own palette, before we restyle


def active_scheme() -> str:
    """The scheme in use right now: ``"dark"`` or ``"light"``."""
    return _active


def color(name: str) -> str:
    return PALETTES[_active][name]


def category_color(category: str) -> str:
    return CATEGORY_COLORS[_active].get(category, color("muted"))


def system_scheme() -> str:
    """Ask the desktop whether it prefers dark or light (Qt 6.5+), else guess from its palette."""
    hints = QGuiApplication.styleHints()
    scheme = getattr(hints, "colorScheme", lambda: None)()
    if scheme == getattr(Qt.ColorScheme, "Dark", object()):
        return DARK
    if scheme == getattr(Qt.ColorScheme, "Light", object()):
        return LIGHT
    lightness = _desktop_window_lightness
    if lightness is None:
        lightness = QGuiApplication.palette().color(QPalette.Window).lightness()
    return DARK if lightness < 128 else LIGHT


def resolve(mode: str) -> str:
    return system_scheme() if mode not in (LIGHT, DARK) else mode


STYLE_TEMPLATE = """
* {{
    color: {text};
    outline: 0;
}}
QMainWindow, QWidget#Content, QStackedWidget, QWidget#Page {{
    background: {bg};
}}
QFrame#Sidebar {{
    background: {sidebar};
    border-right: 1px solid {border};
}}
QLabel#AppName {{
    font-size: 17pt;
    font-weight: 700;
}}
QLabel#Muted, QLabel#AppTagline, QLabel#PageSubtitle {{
    color: {muted};
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
    color: {muted};
    font-size: 9pt;
    padding: 10px;
    background: {surface};
    border: 1px solid {border};
    border-radius: 10px;
}}
QPushButton {{
    background: {surface_2};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {surface_3};
}}
QPushButton:disabled {{
    color: {disabled};
    background: {surface};
    border-color: {surface_2};
}}
QPushButton#PrimaryButton {{
    background: {accent};
    border: 1px solid {accent};
    color: white;
    padding: 10px 22px;
    font-size: 11pt;
}}
QPushButton#PrimaryButton:hover {{
    background: {accent_hover};
    border-color: {accent_hover};
}}
QPushButton#PrimaryButton:pressed {{
    background: {accent_pressed};
}}
QPushButton#PrimaryButton:disabled {{
    background: {primary_disabled};
    border-color: {primary_disabled};
    color: {primary_disabled_text};
}}
QPushButton#GhostButton {{
    background: transparent;
    border: 1px solid transparent;
    color: {muted};
    padding: 6px 10px;
}}
QPushButton#GhostButton:hover {{
    color: {text};
    background: {surface_2};
}}
QPushButton#NavButton {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 12px;
    text-align: left;
    font-weight: 500;
    color: {muted};
}}
QPushButton#NavButton:hover {{
    background: {surface};
    color: {text};
}}
QPushButton#NavButton:checked {{
    background: {surface_2};
    color: {text};
    font-weight: 600;
}}
QFrame#Card {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
}}
QFrame#Card:hover {{
    border-color: {surface_3};
    background: {surface_2};
}}
QFrame#Card[selected="true"] {{
    border: 1px solid {accent};
    background: {card_selected};
}}
QFrame#Card[empty="true"] QLabel {{
    color: {disabled};
}}
QLabel#CardCount {{
    font-size: 16pt;
    font-weight: 700;
}}
QLabel#CardTitle {{
    color: {muted};
    font-weight: 600;
}}
QFrame#Banner {{
    background: {banner};
    border: 1px solid {banner_border};
    border-radius: 12px;
}}
QFrame#WarningBanner {{
    background: {warning_bg};
    border: 1px solid {warning_border};
    border-radius: 10px;
}}
QFrame#Panel {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
}}
QLineEdit {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {accent};
}}
QLineEdit:focus {{
    border-color: {accent};
}}
QTableView, QTreeWidget {{
    background: {surface};
    alternate-background-color: {alt_row};
    border: 1px solid {border};
    border-radius: 12px;
    gridline-color: transparent;
    selection-background-color: {selection};
    selection-color: {text};
}}
QTableView::item, QTreeWidget::item {{
    padding: 6px 4px;
    border: none;
}}
QHeaderView::section {{
    background: {surface};
    color: {muted};
    border: none;
    border-bottom: 1px solid {border};
    padding: 8px 6px;
    font-weight: 600;
}}
QTableCornerButton::section {{
    background: {surface};
    border: none;
}}
QCheckBox::indicator, QTableView::indicator, QTreeWidget::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {indicator_border};
    background: {surface_2};
}}
QCheckBox::indicator:checked, QTableView::indicator:checked, QTreeWidget::indicator:checked {{
    background: {accent};
    border-color: {accent};
    image: url("@CHECK@");
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {surface_3};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {surface_3};
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
    background: {sidebar};
    color: {muted};
    border-top: 1px solid {border};
}}
QProgressBar {{
    background: {surface_2};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {accent};
    border-radius: 5px;
}}
QMessageBox, QProgressDialog, QDialog {{
    background: {surface};
}}
QToolTip {{
    background: {surface_2};
    color: {text};
    border: 1px solid {border};
    padding: 6px;
}}
QLabel#WarningText {{
    color: {warning};
}}
QLabel#SidebarCaption {{
    color: {muted};
    font-size: 9pt;
    font-weight: 600;
}}
QPushButton#SegmentButton {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 0;
    padding: 5px 0;
    font-weight: 500;
    color: {muted};
}}
QPushButton#SegmentButton[first="true"] {{
    border-top-left-radius: 7px;
    border-bottom-left-radius: 7px;
}}
QPushButton#SegmentButton[last="true"] {{
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
}}
QPushButton#SegmentButton:hover {{
    color: {text};
    background: {surface};
}}
QPushButton#SegmentButton:checked {{
    background: {surface_3};
    color: {text};
    font-weight: 600;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
"""


def apply_theme(app: QApplication, mode: str = SYSTEM) -> str:
    """Apply ``mode`` ("system", "light" or "dark"); return the scheme used."""
    global _active, _desktop_window_lightness
    if _desktop_window_lightness is None:
        _desktop_window_lightness = app.palette().color(QPalette.Window).lightness()
    _active = resolve(mode)
    c = PALETTES[_active]
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(c["bg"]))
    palette.setColor(QPalette.WindowText, QColor(c["text"]))
    palette.setColor(QPalette.Base, QColor(c["surface"]))
    palette.setColor(QPalette.AlternateBase, QColor(c["alt_row"]))
    palette.setColor(QPalette.Text, QColor(c["text"]))
    palette.setColor(QPalette.Button, QColor(c["surface_2"]))
    palette.setColor(QPalette.ButtonText, QColor(c["text"]))
    palette.setColor(QPalette.Highlight, QColor(c["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor("white"))
    palette.setColor(QPalette.ToolTipBase, QColor(c["surface_2"]))
    palette.setColor(QPalette.ToolTipText, QColor(c["text"]))
    palette.setColor(QPalette.PlaceholderText, QColor(c["muted"]))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(c["disabled"]))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(c["disabled"]))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(c["disabled"]))
    app.setPalette(palette)

    font = app.font()
    if font.pointSizeF() < 10:
        font.setPointSizeF(10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    app.setStyleSheet(STYLE_TEMPLATE.format(**c).replace("@CHECK@", _checkmark_file()))
    return _active


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
