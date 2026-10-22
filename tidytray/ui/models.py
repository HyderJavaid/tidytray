"""Table model for scanned files, with a checkbox per row."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, Signal

from ..formatting import human_size, short_date
from ..scanner import FileEntry
from .icons import category_icon

SORT_ROLE = Qt.UserRole + 1


class FileTableModel(QAbstractTableModel):
    COLUMNS = ("Name", "Category", "Size", "Modified")
    selectionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[FileEntry] = []
        self._checked: list[bool] = []

    # -- data -------------------------------------------------------------
    def set_files(self, files: list[FileEntry]) -> None:
        self.beginResetModel()
        self._files = list(files)
        self._checked = [True] * len(self._files)
        self.endResetModel()
        self.selectionChanged.emit()

    def files(self) -> list[FileEntry]:
        return list(self._files)

    def selected_files(self) -> list[FileEntry]:
        return [f for f, checked in zip(self._files, self._checked) if checked]

    def set_checked_rows(self, rows: list[int], checked: bool) -> None:
        for row in rows:
            self._checked[row] = checked
        if rows:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self._files) - 1, 0), [Qt.CheckStateRole])
        self.selectionChanged.emit()

    # -- Qt model API -----------------------------------------------------
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._files)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section]
        if orientation == Qt.Horizontal and role == Qt.TextAlignmentRole and section == 2:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def flags(self, index):
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 0:
            base |= Qt.ItemIsUserCheckable
        return base

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        entry = self._files[index.row()]
        col = index.column()
        if role == Qt.DisplayRole:
            return (entry.name, entry.category, human_size(entry.size), short_date(entry.modified))[col]
        if role == SORT_ROLE:
            return (entry.name.casefold(), entry.category, entry.size, entry.modified)[col]
        if role == Qt.CheckStateRole and col == 0:
            return Qt.Checked if self._checked[index.row()] else Qt.Unchecked
        if role == Qt.DecorationRole and col == 0:
            return category_icon(entry.category)
        if role == Qt.ToolTipRole and col == 0:
            return str(entry.path)
        if role == Qt.TextAlignmentRole and col == 2:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.CheckStateRole and index.column() == 0:
            self._checked[index.row()] = Qt.CheckState(value) == Qt.Checked
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            self.selectionChanged.emit()
            return True
        return False


class FileFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._category: str | None = None
        self._text = ""
        self.setSortRole(SORT_ROLE)

    def _refilter(self, change) -> None:
        if hasattr(self, "beginFilterChange"):  # Qt 6.10+
            self.beginFilterChange()
            change()
            self.endFilterChange()
        else:
            change()
            self.invalidateFilter()

    def set_category(self, category: str | None) -> None:
        self._refilter(lambda: setattr(self, "_category", category))

    def set_text(self, text: str) -> None:
        self._refilter(lambda: setattr(self, "_text", text.casefold().strip()))

    def filterAcceptsRow(self, source_row, source_parent):
        model: FileTableModel = self.sourceModel()
        entry = model._files[source_row]
        if self._category and entry.category != self._category:
            return False
        if self._text and self._text not in entry.name.casefold():
            return False
        return True

    def visible_source_rows(self) -> list[int]:
        return [self.mapToSource(self.index(r, 0)).row() for r in range(self.rowCount())]
