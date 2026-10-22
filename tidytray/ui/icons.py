"""Icons drawn in code, so they look the same on every system and need no files."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

from ..categories import ARCHIVES, AUDIO, CODE, DOCUMENTS, IMAGES, INSTALLERS, VIDEOS
from .theme import active_scheme, category_color, color


def _canvas(size: int) -> tuple[QPixmap, QPainter]:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(size / 24.0, size / 24.0)  # draw on a 24x24 grid
    return pixmap, painter


def _pen(color: QColor, width: float = 1.8) -> QPen:
    pen = QPen(color, width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _draw_glyph(p: QPainter, category: str, color: QColor) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.NoBrush)
    if category == IMAGES:
        p.drawRoundedRect(QRectF(5, 6, 14, 12), 2, 2)
        p.setBrush(color)
        p.drawEllipse(QPointF(15.2, 9.6), 1.3, 1.3)
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(5.5, 16.5), QPointF(9.5, 12), QPointF(12.5, 15), QPointF(14.5, 13), QPointF(18.5, 17)]))
    elif category == DOCUMENTS:
        path = QPainterPath(QPointF(7, 4.5))
        path.lineTo(14, 4.5)
        path.lineTo(17.5, 8)
        path.lineTo(17.5, 19.5)
        path.lineTo(7, 19.5)
        path.closeSubpath()
        p.drawPath(path)
        p.drawPolyline(QPolygonF([QPointF(13.5, 4.8), QPointF(13.5, 8.5), QPointF(17.2, 8.5)]))
        for y in (12, 14.8):
            p.drawLine(QPointF(9.5, y), QPointF(15, y))
        p.drawLine(QPointF(9.5, 17.3), QPointF(12.5, 17.3))
    elif category == VIDEOS:
        p.drawRoundedRect(QRectF(4.5, 6.5, 15, 11), 2.5, 2.5)
        p.setBrush(color)
        p.drawPolygon(QPolygonF([QPointF(10.5, 9.5), QPointF(14.5, 12), QPointF(10.5, 14.5)]))
    elif category == AUDIO:
        p.drawLine(QPointF(10, 16.5), QPointF(10, 6.5))
        p.drawLine(QPointF(10, 6.5), QPointF(17, 5))
        p.drawLine(QPointF(17, 5), QPointF(17, 15))
        p.setBrush(color)
        p.drawEllipse(QPointF(8.2, 16.8), 2, 1.7)
        p.drawEllipse(QPointF(15.2, 15.3), 2, 1.7)
    elif category == ARCHIVES:
        p.drawRoundedRect(QRectF(5, 8, 14, 11), 1.5, 1.5)
        p.drawRoundedRect(QRectF(4, 5, 16, 3.2), 1.2, 1.2)
        p.drawLine(QPointF(10.5, 11.5), QPointF(13.5, 11.5))
    elif category == INSTALLERS:
        p.drawLine(QPointF(12, 4.5), QPointF(12, 14))
        p.drawPolyline(QPolygonF([QPointF(8.5, 10.5), QPointF(12, 14), QPointF(15.5, 10.5)]))
        p.drawPolyline(QPolygonF([QPointF(5, 14.5), QPointF(5, 18.5), QPointF(19, 18.5), QPointF(19, 14.5)]))
    elif category == CODE:
        p.drawPolyline(QPolygonF([QPointF(8.5, 8), QPointF(4.8, 12), QPointF(8.5, 16)]))
        p.drawPolyline(QPolygonF([QPointF(15.5, 8), QPointF(19.2, 12), QPointF(15.5, 16)]))
        p.drawLine(QPointF(13.3, 6.5), QPointF(10.7, 17.5))
    else:
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        for x in (7.5, 12, 16.5):
            p.drawEllipse(QPointF(x, 12), 1.6, 1.6)


def category_pixmap(category: str, size: int = 32) -> QPixmap:
    return _category_pixmap(category, size, active_scheme())


@lru_cache(maxsize=None)
def _category_pixmap(category: str, size: int, scheme: str) -> QPixmap:
    glyph = QColor(category_color(category))
    pixmap, p = _canvas(size)
    tint = QColor(glyph)
    tint.setAlpha(40)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(tint))
    p.drawRoundedRect(QRectF(0.5, 0.5, 23, 23), 6.5, 6.5)
    _draw_glyph(p, category, glyph)
    p.end()
    return pixmap


def category_icon(category: str) -> QIcon:
    return _category_icon(category, active_scheme())


@lru_cache(maxsize=None)
def _category_icon(category: str, scheme: str) -> QIcon:
    icon = QIcon()
    for size in (16, 20, 24, 32, 48):
        icon.addPixmap(category_pixmap(category, size))
    return icon


def nav_icon(kind: str, role: str = "muted", size: int = 20) -> QIcon:
    """A line icon drawn in the current theme's ``role`` color ("text" or "muted")."""
    pixmap, p = _canvas(size)
    c = QColor(color(role))
    p.setPen(_pen(c, 1.9))
    if kind == "overview":
        for x, y in ((4.5, 4.5), (13, 4.5), (4.5, 13), (13, 13)):
            p.drawRoundedRect(QRectF(x, y, 6.5, 6.5), 1.6, 1.6)
    elif kind == "plan":
        for y in (6.5, 12, 17.5):
            p.drawLine(QPointF(9, y), QPointF(19.5, y))
            p.drawPoint(QPointF(5, y))
    elif kind == "history":
        p.drawEllipse(QPointF(12, 12), 8, 8)
        p.drawPolyline(QPolygonF([QPointF(12, 7.5), QPointF(12, 12), QPointF(15, 14)]))
    elif kind == "undo":
        p.drawPolyline(QPolygonF([QPointF(8.5, 5.5), QPointF(4.5, 9.5), QPointF(8.5, 13.5)]))
        path = QPainterPath(QPointF(4.5, 9.5))
        path.lineTo(14, 9.5)
        path.cubicTo(QPointF(21, 9.5), QPointF(21, 19), QPointF(14, 19))
        path.lineTo(9, 19)
        p.drawPath(path)
    elif kind == "folder":
        path = QPainterPath(QPointF(3.5, 7))
        path.lineTo(3.5, 18.5)
        path.lineTo(20.5, 18.5)
        path.lineTo(20.5, 8.5)
        path.lineTo(11.5, 8.5)
        path.lineTo(9.5, 5.5)
        path.lineTo(3.5, 5.5)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "refresh":
        path = QPainterPath()
        path.arcMoveTo(QRectF(5, 5, 14, 14), 60)
        path.arcTo(QRectF(5, 5, 14, 14), 60, 280)
        p.drawPath(path)
        p.drawPolyline(QPolygonF([QPointF(15.5, 3.5), QPointF(15.8, 6.6), QPointF(18.8, 6.2)]))
    elif kind == "lock":
        p.drawRoundedRect(QRectF(5.5, 10.5, 13, 9.5), 2, 2)
        path = QPainterPath(QPointF(8.5, 10.5))
        path.lineTo(8.5, 8)
        path.arcTo(QRectF(8.5, 4.5, 7, 7), 180, -180)
        path.lineTo(15.5, 10.5)
        p.drawPath(path)
    p.end()
    return QIcon(pixmap)


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(app_pixmap(size))
    return icon


@lru_cache(maxsize=None)
def app_pixmap(size: int = 64) -> QPixmap:
    pixmap, p = _canvas(size)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color("accent")))
    p.drawRoundedRect(QRectF(1, 1, 22, 22), 6, 6)
    white = QColor("white")
    p.setPen(_pen(white, 1.9))
    # A tray with three neat stacks above it.
    p.drawPolyline(QPolygonF([QPointF(5, 13), QPointF(5, 18), QPointF(19, 18), QPointF(19, 13)]))
    p.drawLine(QPointF(9.5, 15), QPointF(14.5, 15))
    p.setPen(Qt.NoPen)
    for x, h, alpha in ((7, 6, 230), (11, 8, 255), (15, 5, 200)):
        c = QColor(white)
        c.setAlpha(alpha)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(x, 12 - h, 2.6, h), 1, 1)
    p.end()
    return pixmap

