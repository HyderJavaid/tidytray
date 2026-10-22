"""The TidyTray main window: sidebar, overview, review plan and history."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFontMetrics, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QStackedWidget,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import __copyright__, __version__
from ..categories import CATEGORIES
from ..formatting import human_size, plural
from ..history import History, Operation
from ..organizer import OrganizeResult, UndoResult, execute_plan, undo_operation
from ..paths import default_folder
from ..planner import Plan, build_plan
from ..safety import unsafe_reason
from ..scanner import ScanResult, scan_folder
from .icons import app_pixmap, category_icon, category_pixmap, nav_icon
from .models import FileFilterProxy, FileTableModel
from .. import settings
from .theme import DARK, LIGHT, SYSTEM, apply_theme, color
from .widgets import CategoryCard, EmptyState, PageHeader, label
from .workers import Task

PAGE_OVERVIEW, PAGE_PLAN, PAGE_HISTORY = range(3)

STATUS_TEXT = {
    "complete": "Completed",
    "cancelled": "Stopped early",
    "interrupted": "Interrupted, recovered",
    "in_progress": "In progress",
}


def _list_details(rows: list[tuple[Path, str]], limit: int = 200) -> str:
    lines = [f"{path.name}: {reason}" for path, reason in rows[:limit]]
    if len(rows) > limit:
        lines.append(f"…and {len(rows) - limit} more")
    return "\n".join(lines)


class MainWindow(QMainWindow):
    def __init__(self, history: History | None = None, theme_mode: str | None = None):
        super().__init__()
        self.history = history or History()
        mode = theme_mode or settings.load().get("theme", SYSTEM)
        self.theme_mode = mode if mode in (SYSTEM, LIGHT, DARK) else SYSTEM
        self.scan_result: ScanResult | None = None
        self.plan: Plan | None = None
        self.task: Task | None = None
        self.pool = QThreadPool.globalInstance()
        self._category_filter: str | None = None
        self._next_status: str | None = None

        self.setWindowTitle("TidyTray")
        self.setMinimumSize(1080, 720)
        self.resize(1240, 800)

        self.model = FileTableModel(self)
        self.proxy = FileFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.model.selectionChanged.connect(self._update_selection_summary)

        root = QWidget()
        root.setObjectName("Content")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_overview_page())
        self.pages.addWidget(self._build_plan_page())
        self.pages.addWidget(self._build_history_page())
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage("Ready. Nothing changes until you confirm.")

        QShortcut(QKeySequence.Open, self, activated=self.choose_folder)
        QShortcut(QKeySequence.Refresh, self, activated=self.rescan)
        QShortcut(QKeySequence.Undo, self, activated=self.undo_last)
        QShortcut(QKeySequence.HelpContents, self, activated=self.show_about)

        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._on_system_scheme_changed)

        self.set_theme(self.theme_mode, save=False)
        self.show_page(PAGE_OVERVIEW)
        self.refresh_history()
        self._update_overview()
        self._update_plan_page()

    # ------------------------------------------------------------------ UI
    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(236)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(4)

        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(app_pixmap(36))
        brand.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("TidyTray", "AppName"))
        names.addWidget(label("Downloads, sorted safely", "AppTagline"))
        brand.addLayout(names, 1)
        layout.addLayout(brand)
        layout.addSpacing(24)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: list[QPushButton] = []
        for index, (text, icon) in enumerate((("Overview", "overview"), ("Review plan", "plan"), ("History", "history"))):
            btn = QPushButton(f"  {text}")
            btn.setObjectName("NavButton")
            btn.setIcon(nav_icon(icon, "text"))
            btn.setProperty("iconKind", icon)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, i=index: self.show_page(i))
            self.nav_group.addButton(btn, index)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch(1)
        layout.addWidget(label("APPEARANCE", "SidebarCaption"))
        layout.addSpacing(4)
        segments = QHBoxLayout()
        segments.setSpacing(0)
        self.theme_group = QButtonGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_buttons: dict[str, QPushButton] = {}
        for i, (mode, text) in enumerate(((SYSTEM, "System"), (LIGHT, "Light"), (DARK, "Dark"))):
            btn = QPushButton(text)
            btn.setObjectName("SegmentButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("first", i == 0)
            btn.setProperty("last", i == 2)
            btn.setToolTip("Follow your system's dark or light setting" if mode == SYSTEM else f"Always use the {text.lower()} theme")
            btn.clicked.connect(lambda _=False, m=mode: self.set_theme(m))
            self.theme_group.addButton(btn)
            self.theme_buttons[mode] = btn
            segments.addWidget(btn)
        layout.addLayout(segments)
        layout.addSpacing(16)
        self.undo_button = QPushButton("  Undo last cleanup")
        self.undo_button.setProperty("iconKind", "undo")
        self.undo_button.setCursor(Qt.PointingHandCursor)
        self.undo_button.clicked.connect(self.undo_last)
        layout.addWidget(self.undo_button)
        layout.addSpacing(12)
        note = label(
            "Private by design. TidyTray works offline, never deletes files, and keeps its history on this computer.",
            "PrivacyNote",
            wrap=True,
        )
        layout.addWidget(note)
        return sidebar

    def _page(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(18)
        return page, layout

    def _build_overview_page(self) -> QWidget:
        page, layout = self._page()
        self.overview_header = PageHeader("Overview", "No folder selected")
        self.choose_button = QPushButton("  Choose folder…")
        self.choose_button.setProperty("iconKind", "folder")
        self.choose_button.clicked.connect(self.choose_folder)
        self.rescan_button = QPushButton("  Rescan")
        self.rescan_button.setObjectName("GhostButton")
        self.rescan_button.setProperty("iconKind", "refresh")
        self.rescan_button.setProperty("iconRole", "muted")
        self.rescan_button.clicked.connect(self.rescan)
        self.overview_header.actions.addWidget(self.rescan_button)
        self.overview_header.actions.addWidget(self.choose_button)
        layout.addWidget(self.overview_header)

        self.overview_stack = QStackedWidget()
        layout.addWidget(self.overview_stack, 1)

        empty = EmptyState(
            lambda: app_pixmap(72),
            "Choose a folder to tidy",
            "TidyTray looks only at the files directly inside the folder you pick. "
            "It shows you a plan first, and nothing moves until you confirm.",
        )
        pick = QPushButton("Choose folder…")
        pick.clicked.connect(self.choose_folder)
        empty.add_button(pick)
        downloads = default_folder()
        if downloads:
            use = QPushButton(f"Use {downloads.name}")
            use.setObjectName("PrimaryButton")
            use.setToolTip(str(downloads))
            use.clicked.connect(lambda: self.load_folder(downloads))
            empty.add_button(use)
        self.overview_stack.addWidget(empty)

        content = QWidget()
        c = QVBoxLayout(content)
        c.setContentsMargins(0, 0, 0, 0)
        c.setSpacing(16)

        stats_row = QHBoxLayout()
        self.stats_label = label("", "SectionTitle")
        stats_row.addWidget(self.stats_label)
        self.skipped_button = QPushButton()
        self.skipped_button.setObjectName("GhostButton")
        self.skipped_button.setCursor(Qt.PointingHandCursor)
        self.skipped_button.clicked.connect(self._show_skipped)
        stats_row.addWidget(self.skipped_button)
        stats_row.addStretch(1)
        c.addLayout(stats_row)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.cards: dict[str, CategoryCard] = {}
        for i, category in enumerate(CATEGORIES):
            card = CategoryCard(category)
            card.clicked.connect(self._toggle_category_filter)
            self.cards[category] = card
            grid.addWidget(card, i // 4, i % 4)
        c.addLayout(grid)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by name…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(280)
        self.search.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search)
        self.filter_chip = QPushButton()
        self.filter_chip.setObjectName("GhostButton")
        self.filter_chip.setToolTip("Show all categories")
        self.filter_chip.clicked.connect(lambda: self._set_category_filter(None))
        toolbar.addWidget(self.filter_chip)
        toolbar.addStretch(1)
        select_all = QPushButton("Select all")
        select_all.setObjectName("GhostButton")
        select_all.clicked.connect(lambda: self._set_visible_checked(True))
        select_none = QPushButton("Select none")
        select_none.setObjectName("GhostButton")
        select_none.clicked.connect(lambda: self._set_visible_checked(False))
        toolbar.addWidget(select_all)
        toolbar.addWidget(select_none)
        c.addLayout(toolbar)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.AscendingOrder)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setIconSize(category_pixmap(CATEGORIES[0], 20).size())
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col, width in ((1, 120), (2, 100), (3, 150)):
            header.setSectionResizeMode(col, QHeaderView.Fixed)
            header.resizeSection(col, width)
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.doubleClicked.connect(self._toggle_row)
        space = QShortcut(QKeySequence(Qt.Key_Space), self.table, activated=self._toggle_selected_rows)
        space.setContext(Qt.WidgetShortcut)
        self.table_stack = QStackedWidget()
        self.table_stack.addWidget(self.table)
        self.table_stack.addWidget(
            EmptyState(
                lambda: category_pixmap("Other", 56),
                "All tidy",
                "There are no loose files directly inside this folder. Files already in subfolders are left as they are.",
            )
        )
        c.addWidget(self.table_stack, 1)

        bottom = QHBoxLayout()
        self.selection_label = label("", "Muted")
        bottom.addWidget(self.selection_label)
        bottom.addStretch(1)
        self.review_button = QPushButton("Review cleanup plan")
        self.review_button.setObjectName("PrimaryButton")
        self.review_button.setCursor(Qt.PointingHandCursor)
        self.review_button.clicked.connect(self.review_plan)
        bottom.addWidget(self.review_button)
        c.addLayout(bottom)

        self.overview_stack.addWidget(content)
        return page

    def _build_plan_page(self) -> QWidget:
        page, layout = self._page()
        layout.addWidget(PageHeader("Review plan", "Nothing has changed yet. Check where each file will go."))
        self.plan_stack = QStackedWidget()
        layout.addWidget(self.plan_stack, 1)

        empty = EmptyState(
            lambda: category_pixmap("Other", 72),
            "No plan yet",
            "Choose a folder, tick the files you want to tidy, then press “Review cleanup plan”.",
        )
        back = QPushButton("Go to Overview")
        back.clicked.connect(lambda: self.show_page(PAGE_OVERVIEW))
        empty.add_button(back)
        self.plan_stack.addWidget(empty)

        content = QWidget()
        c = QVBoxLayout(content)
        c.setContentsMargins(0, 0, 0, 0)
        c.setSpacing(14)

        banner = QFrame()
        banner.setObjectName("Banner")
        b = QVBoxLayout(banner)
        b.setContentsMargins(18, 14, 18, 14)
        b.setSpacing(4)
        self.plan_headline = label("", "SectionTitle", wrap=True)
        self.plan_detail = label("", "Muted", wrap=True)
        b.addWidget(self.plan_headline)
        b.addWidget(self.plan_detail)
        c.addWidget(banner)

        self.plan_tree = QTreeWidget()
        self.plan_tree.setColumnCount(3)
        self.plan_tree.setHeaderLabels(["File", "Will move to", "Size"])
        self.plan_tree.setAlternatingRowColors(True)
        self.plan_tree.setRootIsDecorated(True)
        self.plan_tree.setUniformRowHeights(True)
        self.plan_tree.setSelectionMode(QAbstractItemView.NoSelection)
        th = self.plan_tree.header()
        th.setSectionResizeMode(0, QHeaderView.Stretch)
        th.setSectionResizeMode(1, QHeaderView.Stretch)
        th.setSectionResizeMode(2, QHeaderView.Fixed)
        th.resizeSection(2, 100)
        self.plan_tree.headerItem().setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
        c.addWidget(self.plan_tree, 1)

        self.plan_warning = QFrame()
        self.plan_warning.setObjectName("WarningBanner")
        w = QHBoxLayout(self.plan_warning)
        w.setContentsMargins(14, 10, 14, 10)
        self.plan_warning_label = label("", wrap=True)
        self.plan_warning_label.setObjectName("WarningText")
        w.addWidget(self.plan_warning_label, 1)
        details = QPushButton("Details")
        details.setObjectName("GhostButton")
        details.clicked.connect(self._show_plan_skipped)
        w.addWidget(details)
        c.addWidget(self.plan_warning)

        bottom = QHBoxLayout()
        back = QPushButton("Back to selection")
        back.clicked.connect(lambda: self.show_page(PAGE_OVERVIEW))
        bottom.addWidget(back)
        bottom.addStretch(1)
        self.organize_button = QPushButton("Organize files")
        self.organize_button.setObjectName("PrimaryButton")
        self.organize_button.setCursor(Qt.PointingHandCursor)
        self.organize_button.clicked.connect(self.organize)
        bottom.addWidget(self.organize_button)
        c.addLayout(bottom)

        self.plan_stack.addWidget(content)
        return page

    def _build_history_page(self) -> QWidget:
        page, layout = self._page()
        header = PageHeader("History", "Every cleanup is recorded on this computer so it can be undone.")
        open_dir = QPushButton("Open history folder")
        open_dir.setObjectName("GhostButton")
        open_dir.clicked.connect(self._open_history_folder)
        header.actions.addWidget(open_dir)
        about = QPushButton("About")
        about.setObjectName("GhostButton")
        about.clicked.connect(self.show_about)
        header.actions.addWidget(about)
        layout.addWidget(header)

        self.history_stack = QStackedWidget()
        layout.addWidget(self.history_stack, 1)
        self.history_stack.addWidget(
            EmptyState(lambda: nav_icon("history", "muted", 72).pixmap(72, 72), "No cleanups yet", "When you organize a folder, it will be listed here.")
        )

        content = QWidget()
        c = QVBoxLayout(content)
        c.setContentsMargins(0, 0, 0, 0)
        c.setSpacing(14)
        self.history_tree = QTreeWidget()
        self.history_tree.setColumnCount(4)
        self.history_tree.setHeaderLabels(["When", "Folder", "Files moved", "Status"])
        self.history_tree.setRootIsDecorated(False)
        self.history_tree.setAlternatingRowColors(True)
        self.history_tree.setSelectionMode(QAbstractItemView.NoSelection)
        hh = self.history_tree.header()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.resizeSection(0, 170)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        hh.resizeSection(2, 110)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        hh.resizeSection(3, 190)
        c.addWidget(self.history_tree, 1)
        bottom = QHBoxLayout()
        self.history_hint = label("", "Muted", wrap=True)
        bottom.addWidget(self.history_hint, 1)
        self.history_undo_button = QPushButton("Undo last cleanup")
        self.history_undo_button.setObjectName("PrimaryButton")
        self.history_undo_button.clicked.connect(self.undo_last)
        bottom.addWidget(self.history_undo_button)
        c.addLayout(bottom)
        self.history_stack.addWidget(content)
        return page

    # ----------------------------------------------------------- dialogs
    # Kept as methods so tests can replace them without showing real dialogs.
    def ask(self, title: str, text: str, informative: str, confirm: str) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(title)
        box.setText(text)
        box.setInformativeText(informative)
        ok = box.addButton(confirm, QMessageBox.AcceptRole)
        cancel = box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        return box.clickedButton() is ok

    def inform(self, title: str, text: str, informative: str = "", details: str = "", level: str = "info") -> None:
        box = QMessageBox(self)
        box.setIcon({"info": QMessageBox.Information, "warning": QMessageBox.Warning, "error": QMessageBox.Critical}[level])
        box.setWindowTitle(title)
        box.setText(text)
        if informative:
            box.setInformativeText(informative)
        if details:
            box.setDetailedText(details)
        box.exec()

    # ---------------------------------------------------------------- theme
    def set_theme(self, mode: str, save: bool = True) -> None:
        """Switch between "system", "light" and "dark" and remember the choice."""
        self.theme_mode = mode
        self.theme_buttons[mode].setChecked(True)
        apply_theme(QApplication.instance(), mode)
        if save:
            settings.save(theme=mode)
        self._retheme()

    def _on_system_scheme_changed(self, *_args) -> None:
        if self.theme_mode == SYSTEM:
            self.set_theme(SYSTEM, save=False)

    def _retheme(self) -> None:
        """Redraw everything that is painted in code rather than styled."""
        for button in self.findChildren(QPushButton):
            kind = button.property("iconKind")
            if kind:
                button.setIcon(nav_icon(kind, button.property("iconRole") or "text"))
        for card in self.cards.values():
            card.refresh_icon()
        for empty in self.findChildren(EmptyState):
            empty.refresh_icon()
        if self._category_filter:
            self.filter_chip.setIcon(category_icon(self._category_filter))
        self.model.layoutChanged.emit()
        self._update_plan_page()
        self.refresh_history()

    # ------------------------------------------------------------ navigation
    def show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        if index == PAGE_HISTORY:
            self.refresh_history()

    @property
    def busy(self) -> bool:
        return self.task is not None

    def _set_busy(self, busy: bool) -> None:
        for widget in (self.choose_button, self.rescan_button, self.review_button, self.organize_button, self.undo_button, self.history_undo_button):
            widget.setEnabled(not busy)
        if not busy:
            self._update_selection_summary()
            self._update_plan_page()
            self._update_undo_buttons()

    def _run(self, fn, on_done, on_error, progress_title: str | None = None, cancellable: bool = False) -> None:
        task = Task(fn)
        self.task = task
        self._set_busy(True)
        dialog = None
        if progress_title:
            dialog = QProgressDialog(progress_title, "Stop after this file" if cancellable else None, 0, 0, self)
            dialog.setWindowTitle("TidyTray")
            dialog.setWindowModality(Qt.WindowModal)
            dialog.setMinimumDuration(300)
            dialog.setAutoClose(False)
            dialog.setAutoReset(False)
            dialog.setMinimumWidth(420)
            if cancellable:
                dialog.canceled.connect(task.cancel)

            def show_progress(done: int, total: int, name: str) -> None:
                dialog.setMaximum(max(total, 1))
                dialog.setValue(min(done, max(total, 1)))
                if name:
                    dialog.setLabelText(f"{progress_title}\n{done + 1} of {total}: {name}")

            task.signals.progress.connect(show_progress)

        def finish(handler, payload):
            if dialog:
                dialog.close()
                dialog.deleteLater()
            self.task = None
            self._set_busy(False)
            handler(payload)

        task.signals.finished.connect(lambda result: finish(on_done, result))
        task.signals.failed.connect(lambda message: finish(on_error, message))
        self.pool.start(task)

    # -------------------------------------------------------------- scanning
    def choose_folder(self) -> None:
        if self.busy:
            return
        start = self.scan_result.root if self.scan_result else (default_folder() or Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Choose a folder to tidy", str(start))
        if chosen:
            self.load_folder(Path(chosen))

    def rescan(self) -> None:
        if self.scan_result and not self.busy:
            self.load_folder(self.scan_result.root)

    def load_folder(self, folder: Path) -> None:
        if self.busy:
            return
        reason = unsafe_reason(folder)
        if reason:
            self.inform("Folder not allowed", "TidyTray can't organize this folder.", reason, level="warning")
            return
        self.statusBar().showMessage(f"Scanning {folder}…")

        def scan(progress, should_cancel):
            return scan_folder(folder)

        self._run(scan, self._on_scanned, self._on_scan_failed)

    def _on_scanned(self, result: ScanResult) -> None:
        self.scan_result = result
        self.plan = None
        self.model.set_files(result.files)
        self._set_category_filter(None)
        self.search.clear()
        self._update_overview()
        self._update_plan_page()
        message = self._next_status or f"Scanned {result.root.name}: {plural(len(result.files), 'file')}. Nothing was changed."
        self._next_status = None
        self.statusBar().showMessage(message, 10000)

    def _on_scan_failed(self, message: str) -> None:
        self.statusBar().showMessage("Scan failed.", 5000)
        self.inform("Couldn't scan folder", "The folder couldn't be scanned.", message, level="error")

    def _update_overview(self) -> None:
        result = self.scan_result
        if result is None:
            self.overview_header.subtitle.setText("No folder selected")
            self.overview_stack.setCurrentIndex(0)
            self.rescan_button.setVisible(False)
            return
        self.rescan_button.setVisible(True)
        metrics = QFontMetrics(self.overview_header.subtitle.font())
        self.overview_header.subtitle.setText(metrics.elidedText(str(result.root), Qt.ElideMiddle, 560))
        self.overview_header.subtitle.setToolTip(str(result.root))
        self.overview_stack.setCurrentIndex(1)
        self.table_stack.setCurrentIndex(0 if result.files else 1)

        for category, (count, size) in result.summary().items():
            self.cards[category].set_stats(count, size)
        self.stats_label.setText(
            f"{plural(len(result.files), 'file')} · {human_size(result.total_size)}"
            if result.files
            else "No files to organize here"
        )
        skipped = len(result.skipped)
        self.skipped_button.setVisible(skipped > 0)
        self.skipped_button.setText(f"{plural(skipped, 'item')} left alone (links, hidden files, unfinished downloads)…")
        self._update_selection_summary()

    def _show_skipped(self) -> None:
        if self.scan_result and self.scan_result.skipped:
            rows = [(s.path, s.reason) for s in self.scan_result.skipped]
            self.inform(
                "Items left alone",
                f"TidyTray will not touch these {plural(len(rows), 'item')}.",
                "Symbolic links, hidden or system files, unreadable files and downloads still in progress are always skipped.",
                _list_details(rows),
            )

    # ----------------------------------------------------- table selection
    def _toggle_category_filter(self, category: str) -> None:
        self._set_category_filter(None if self._category_filter == category else category)

    def _set_category_filter(self, category: str | None) -> None:
        self._category_filter = category
        self.proxy.set_category(category)
        for name, card in self.cards.items():
            card.set_selected(name == category)
        self.filter_chip.setVisible(category is not None)
        if category:
            self.filter_chip.setText(f"Showing {category} only  ✕")
            self.filter_chip.setIcon(category_icon(category))

    def _on_search(self, text: str) -> None:
        self.proxy.set_text(text)

    def _set_visible_checked(self, checked: bool) -> None:
        self.model.set_checked_rows(self.proxy.visible_source_rows(), checked)

    def _toggle_row(self, proxy_index) -> None:
        source = self.proxy.mapToSource(proxy_index.siblingAtColumn(0))
        current = self.model.data(source, Qt.CheckStateRole) == Qt.Checked
        self.model.setData(source, Qt.Unchecked if current else Qt.Checked, Qt.CheckStateRole)

    def _toggle_selected_rows(self) -> None:
        rows = [self.proxy.mapToSource(i).row() for i in self.table.selectionModel().selectedRows()]
        if rows:
            all_checked = all(self.model._checked[r] for r in rows)
            self.model.set_checked_rows(rows, not all_checked)

    def _update_selection_summary(self) -> None:
        selected = self.model.selected_files()
        total = len(self.model.files())
        size = sum(f.size for f in selected)
        self.selection_label.setText(f"{len(selected)} of {plural(total, 'file')} selected · {human_size(size)}")
        self.review_button.setEnabled(bool(selected) and not self.busy)
        self.review_button.setText(f"Review cleanup plan ({len(selected)})" if selected else "Review cleanup plan")

    # ------------------------------------------------------------- planning
    def review_plan(self) -> None:
        if not self.scan_result or self.busy:
            return
        selected = self.model.selected_files()
        if not selected:
            self.statusBar().showMessage("Tick at least one file first.", 5000)
            return
        self.plan = build_plan(self.scan_result.root, selected)
        self._update_plan_page()
        self.show_page(PAGE_PLAN)

    def _update_plan_page(self) -> None:
        plan = self.plan
        if plan is None or (not plan.moves and not plan.skipped):
            self.plan_stack.setCurrentIndex(0)
            return
        self.plan_stack.setCurrentIndex(1)
        folders = plan.folders
        self.plan_headline.setText(
            f"{plural(len(plan.moves), 'file')} ({human_size(plan.total_size)}) will be moved into "
            f"{plural(len(folders), 'folder')} inside “{plan.root.name}”."
        )
        detail = "Nothing will be deleted or replaced, and you can undo this from History."
        if plan.renamed_count:
            detail = (
                f"{plural(plan.renamed_count, 'file')} will get a number added to the name because a file "
                f"with the same name is already there. " + detail
            )
        self.plan_detail.setText(detail)

        self.plan_tree.clear()
        by_category: dict[str, list] = {}
        for move in plan.moves:
            by_category.setdefault(move.category, []).append(move)
        warn = QColor(color("warning"))
        for category in folders:
            moves = by_category[category]
            parent = QTreeWidgetItem([category, f"{category}/", f"{plural(len(moves), 'file')}"])
            parent.setIcon(0, category_icon(category))
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)
            parent.setForeground(1, QColor(color("muted")))
            parent.setForeground(2, QColor(color("muted")))
            parent.setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
            for move in moves:
                child = QTreeWidgetItem([move.source.name, f"{category}/{move.destination.name}", human_size(move.size)])
                child.setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
                child.setToolTip(0, str(move.source))
                child.setToolTip(1, str(move.destination))
                if move.renamed:
                    child.setForeground(1, warn)
                    child.setToolTip(1, f"{move.destination}\nRenamed so the existing file is not replaced.")
                parent.addChild(child)
            self.plan_tree.addTopLevelItem(parent)
        self.plan_tree.expandAll()

        self.plan_warning.setVisible(bool(plan.skipped))
        if plan.skipped:
            self.plan_warning_label.setText(f"{plural(len(plan.skipped), 'selected file')} can't be moved and will be left where they are.")
        self.organize_button.setEnabled(bool(plan.moves) and not self.busy)
        self.organize_button.setText(f"Organize {plural(len(plan.moves), 'file')}")

    def _show_plan_skipped(self) -> None:
        if self.plan and self.plan.skipped:
            self.inform("Files left in place", "These files will not be moved:", details=_list_details([(s.path, s.reason) for s in self.plan.skipped]))

    # ------------------------------------------------------------- organize
    def organize(self) -> None:
        plan = self.plan
        if not plan or not plan.moves or self.busy:
            return
        reason = unsafe_reason(plan.root)
        if reason:
            self.inform("Folder not allowed", "TidyTray can't organize this folder.", reason, level="warning")
            return
        confirmed = self.ask(
            "Organize files?",
            f"Move {plural(len(plan.moves), 'file')} ({human_size(plan.total_size)}) into category folders inside “{plan.root.name}”?",
            "Existing files are never replaced and nothing is deleted. You can undo this afterwards with “Undo last cleanup”.",
            f"Move {plural(len(plan.moves), 'file')}",
        )
        if not confirmed:
            self.statusBar().showMessage("Cancelled. No files were changed.", 5000)
            return

        def work(progress, should_cancel):
            return execute_plan(plan, self.history, progress=progress, should_cancel=should_cancel)

        self._run(work, self._on_organized, self._on_task_failed, "Organizing files…", cancellable=True)

    def _on_organized(self, result: OrganizeResult) -> None:
        self.plan = None
        moved = len(result.moved)
        text = f"Moved {plural(moved, 'file')}."
        if result.cancelled:
            text = f"Stopped early. {plural(moved, 'file')} had already been moved."
        info = []
        if result.renamed:
            info.append(f"{plural(result.renamed, 'file')} got a number added to the name to avoid replacing an existing file.")
        if result.failed:
            info.append(f"{plural(len(result.failed), 'file')} could not be moved and were left in place (see details).")
        if moved:
            info.append("You can put everything back with “Undo last cleanup”.")
        self.inform(
            "Cleanup finished" if not result.failed else "Cleanup finished with problems",
            text,
            " ".join(info),
            _list_details(result.failed),
            level="warning" if result.failed else "info",
        )
        self._next_status = text
        self.statusBar().showMessage(text, 10000)
        self.refresh_history()
        self.show_page(PAGE_OVERVIEW)
        self.rescan()

    def _on_task_failed(self, message: str) -> None:
        self.refresh_history()
        self.inform("Something went wrong", "The operation stopped.", message, level="error")
        self.rescan()

    # ----------------------------------------------------------------- undo
    def _update_undo_buttons(self) -> None:
        op = self.history.last_undoable()
        enabled = op is not None and not self.busy
        for button in (self.undo_button, self.history_undo_button):
            button.setEnabled(enabled)
        tip = (
            f"Put back {plural(len(op.remaining_moves()), 'file')} moved in {op.root.name} ({op.started.replace('T', ' ')[:16]})"
            if op
            else "Nothing to undo"
        )
        self.undo_button.setToolTip(tip)
        self.history_undo_button.setToolTip(tip)

    def undo_last(self) -> None:
        if self.busy:
            return
        op = self.history.last_undoable()
        if op is None:
            self.inform("Nothing to undo", "There is no cleanup to undo.")
            return
        count = len(op.remaining_moves())
        confirmed = self.ask(
            "Undo last cleanup?",
            f"Put {plural(count, 'file')} back where they were in “{op.root.name}”?",
            "If a file with the same name has appeared there since, the returning file gets a number added "
            "(for example “photo (1).jpg”) so nothing is replaced. Category folders TidyTray created are removed only if empty.",
            "Undo cleanup",
        )
        if not confirmed:
            return

        def work(progress, should_cancel):
            return undo_operation(self.history, op, progress=progress)

        self._run(work, lambda result: self._on_undone(op, result), self._on_task_failed, "Putting files back…")

    def _on_undone(self, op: Operation, result: UndoResult | None) -> None:
        if result is None:
            self.inform("Nothing to undo", "That cleanup has already been undone.")
        else:
            text = f"Put back {plural(len(result.restored), 'file')}."
            info = []
            if result.renamed:
                info.append(f"{plural(result.renamed, 'file')} came back with a number added because the original name was taken.")
            if result.failed:
                info.append(f"{plural(len(result.failed), 'file')} could not be put back (see details).")
            self.inform(
                "Undo finished" if not result.failed else "Undo finished with problems",
                text,
                " ".join(info),
                _list_details(result.failed),
                level="warning" if result.failed else "info",
            )
            self.statusBar().showMessage(text, 10000)
        self.refresh_history()
        if self.scan_result and self.scan_result.root == op.root:
            self._next_status = self.statusBar().currentMessage() or None
            self.rescan()

    # -------------------------------------------------------------- history
    def refresh_history(self) -> None:
        ops = self.history.operations()
        self.history_tree.clear()
        undoable = self.history.last_undoable()
        for op in ops:
            if op.undone:
                status = "Undone" if len(op.restored) >= len(op.moves) else "Undone (some files missing)"
            elif op.undo_started:
                status = "Undo interrupted, can resume"
            else:
                status = STATUS_TEXT.get(op.status, op.status)
            when = op.started_at.strftime("%Y-%m-%d %H:%M") if op.started_at else op.started
            item = QTreeWidgetItem([when, str(op.root), str(len(op.moves)), status])
            item.setToolTip(1, str(op.root))
            item.setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
            if undoable is not None and op.id == undoable.id:
                item.setText(3, f"{status} · can undo")
            if op.undone:
                for col in range(4):
                    item.setForeground(col, QColor(color("muted")))
            self.history_tree.addTopLevelItem(item)
        self.history_stack.setCurrentIndex(1 if ops else 0)
        self.history_hint.setText(f"History is stored only on this computer, in {self.history.directory}")
        self._update_undo_buttons()

    @staticmethod
    def about_text() -> str:
        return (
            f"<h3>TidyTray {__version__}</h3>"
            "<p>Safely organize a cluttered Downloads folder.</p>"
            f"<p>{__copyright__}</p>"
            "<p>TidyTray is free software: you can redistribute it and/or modify it under the terms of the "
            "<a href='https://www.gnu.org/licenses/gpl-3.0.html'>GNU General Public License</a>, version 3 "
            "or (at your option) any later version. It comes with ABSOLUTELY NO WARRANTY.</p>"
            "<p>Source code: <a href='https://github.com/naOomeow/tidytray'>github.com/naOomeow/tidytray</a><br>"
            "Built with Qt for Python (PySide6), used under the GNU LGPL v3.</p>"
        )

    def show_about(self) -> None:
        QMessageBox.about(self, "About TidyTray", self.about_text())

    def _open_history_folder(self) -> None:
        self.history.ensure()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.history.directory)))

    def recover_interrupted(self) -> None:
        """Called at startup: finish bookkeeping for runs that were cut short."""
        try:
            recovered = self.history.recover_incomplete()
        except OSError as exc:
            self.inform("History problem", "TidyTray couldn't read its history.", str(exc), level="warning")
            return
        if recovered:
            moved = sum(len(op.moves) for op in recovered)
            self.inform(
                "Previous cleanup was interrupted",
                "TidyTray was closed while it was organizing files.",
                f"{plural(moved, 'file')} had already been moved. They are recorded in History and you can put them back with “Undo last cleanup”.",
                level="warning",
            )
            self.refresh_history()

    # ------------------------------------------------------------- closing
    def closeEvent(self, event):
        if self.task is not None:
            if not self.ask(
                "Cleanup in progress",
                "TidyTray is still moving files.",
                "Close after the current file finishes? Everything moved so far stays recorded and can be undone.",
                "Stop and close",
            ):
                event.ignore()
                return
            self.task.cancel()
            self.pool.waitForDone()
        event.accept()
