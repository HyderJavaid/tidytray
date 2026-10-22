"""Reusable building blocks: category cards, empty states, page headers."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..formatting import human_size, plural
from .icons import category_pixmap


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    for child in widget.findChildren(QWidget):
        child.style().unpolish(child)
        child.style().polish(child)


def label(text: str = "", object_name: str | None = None, wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    if object_name:
        lbl.setObjectName(object_name)
    lbl.setWordWrap(wrap)
    return lbl


class CategoryCard(QFrame):
    clicked = Signal(str)

    def __init__(self, category: str, parent=None):
        super().__init__(parent)
        self.category = category
        self.setObjectName("Card")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(96)
        self.setToolTip(f"Show only {category.lower()} in the table")

        self.icon = icon = QLabel()
        icon.setFixedSize(30, 30)
        self.refresh_icon()
        title = label(category, "CardTitle")
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(icon)
        top.addWidget(title, 1)

        self.count_label = label("0", "CardCount")
        self.size_label = label("", "Muted")
        bottom = QHBoxLayout()
        bottom.addWidget(self.count_label)
        bottom.addStretch(1)
        bottom.addWidget(self.size_label, 0, Qt.AlignBottom)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        layout.addLayout(top)
        layout.addLayout(bottom)
        self.set_stats(0, 0)

    def refresh_icon(self) -> None:
        self.icon.setPixmap(category_pixmap(self.category, 30))

    def set_stats(self, count: int, size: int) -> None:
        self.count_label.setText(str(count))
        self.size_label.setText(human_size(size) if count else "empty")
        self.setProperty("empty", count == 0)
        self.setAccessibleName(f"{self.category}: {plural(count, 'file')}, {human_size(size)}")
        repolish(self)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        repolish(self)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self.category)
        super().mouseReleaseEvent(event)


class EmptyState(QWidget):
    """A friendly centered message with optional action buttons."""

    def __init__(self, pixmap: Callable[[], QPixmap], title: str, body: str, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        self.icon = QLabel()
        self.icon.setAlignment(Qt.AlignCenter)
        self.refresh_icon()
        layout.addWidget(self.icon)
        layout.addSpacing(12)
        t = label(title, "SectionTitle")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size: 15pt;")
        layout.addWidget(t)
        self.body = label(body, "Muted", wrap=True)
        self.body.setAlignment(Qt.AlignCenter)
        self.body.setMaximumWidth(460)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.body)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addSpacing(16)
        self.buttons = QHBoxLayout()
        self.buttons.setSpacing(10)
        self.buttons.addStretch(1)
        self.buttons.addStretch(1)
        layout.addLayout(self.buttons)
        layout.addStretch(2)

    def refresh_icon(self) -> None:
        """Redraw the picture in the current theme's colors."""
        self.icon.setPixmap(self._pixmap())

    def add_button(self, button: QPushButton) -> QPushButton:
        self.buttons.insertWidget(self.buttons.count() - 1, button)
        return button


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        text = QVBoxLayout()
        text.setSpacing(2)
        self.title = label(title, "PageTitle")
        self.subtitle = label(subtitle, "PageSubtitle")
        self.subtitle.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text.addWidget(self.title)
        text.addWidget(self.subtitle)
        layout.addLayout(text, 1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        layout.addLayout(self.actions)
