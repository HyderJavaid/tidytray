"""End-to-end checks of the window, run without a display (offscreen)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtCore import QThreadPool, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from conftest import make  # noqa: E402
from tidytray.ui.main_window import PAGE_PLAN, MainWindow  # noqa: E402
from tidytray.ui.theme import apply_theme  # noqa: E402


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    apply_theme(instance)
    return instance


@pytest.fixture
def window(app, history):
    w = MainWindow(history=history)
    w.asked = []
    w.messages = []
    w.answer = True

    def ask(title, text, informative, confirm):
        w.asked.append(title)
        return w.answer

    w.ask = ask
    w.inform = lambda title, text, informative="", details="", level="info": w.messages.append((title, text, details, level))
    w.show()
    yield w
    w.close()
    w.deleteLater()


def settle(app):
    for _ in range(5):
        QThreadPool.globalInstance().waitForDone()
        app.processEvents()


def test_starts_with_empty_state(window):
    assert window.overview_stack.currentIndex() == 0
    assert window.plan_stack.currentIndex() == 0
    assert not window.undo_button.isEnabled()


def test_full_flow_scan_select_preview_organize_undo(app, window, downloads):
    make(downloads, "a.jpg", "A")
    make(downloads, "b.pdf", "B")
    make(downloads, "c.zip", "C")
    window.load_folder(downloads)
    settle(app)
    assert window.overview_stack.currentIndex() == 1
    assert window.cards["Images"].count_label.text() == "1"

    # Untick the zip.
    row = next(i for i, f in enumerate(window.model.files()) if f.name == "c.zip")
    window.model.setData(window.model.index(row, 0), Qt.Unchecked, Qt.CheckStateRole)
    assert len(window.model.selected_files()) == 2

    window.review_plan()
    assert window.pages.currentIndex() == PAGE_PLAN
    assert len(window.plan.moves) == 2
    assert not (downloads / "Images").exists(), "preview must not change anything"

    # Declining the confirmation changes nothing.
    window.answer = False
    window.organize()
    settle(app)
    assert (downloads / "a.jpg").exists()

    window.answer = True
    window.organize()
    settle(app)
    assert (downloads / "Images" / "a.jpg").exists()
    assert (downloads / "Documents" / "b.pdf").exists()
    assert (downloads / "c.zip").exists()
    assert window.messages[-1][0] == "Cleanup finished"
    assert window.undo_button.isEnabled()
    assert [f.name for f in window.model.files()] == ["c.zip"]  # rescanned

    window.undo_last()
    settle(app)
    assert (downloads / "a.jpg").read_text() == "A"
    assert (downloads / "b.pdf").read_text() == "B"
    assert not (downloads / "Images").exists()
    assert window.messages[-1][0] == "Undo finished"
    assert not window.undo_button.isEnabled()


def test_category_filter_and_select_visible(app, window, downloads):
    make(downloads, "a.jpg")
    make(downloads, "b.jpg")
    make(downloads, "c.pdf")
    window.load_folder(downloads)
    settle(app)
    window._toggle_category_filter("Images")
    assert window.proxy.rowCount() == 2
    window._set_visible_checked(False)
    assert [f.name for f in window.model.selected_files()] == ["c.pdf"]
    window._toggle_category_filter("Images")
    assert window.proxy.rowCount() == 3


def test_refuses_home_folder(app, window):
    from pathlib import Path

    window.load_folder(Path.home())
    settle(app)
    assert window.messages and window.messages[-1][0] == "Folder not allowed"
    assert window.scan_result is None


def test_scan_error_is_shown(app, window, tmp_path):
    window.load_folder(tmp_path / "missing")
    settle(app)
    assert window.messages[-1][0] == "Couldn't scan folder"


def test_startup_recovery_message(app, window, downloads, history):
    src = make(downloads, "a.jpg")
    journal = history.new_journal(downloads, 1)
    (downloads / "Images").mkdir()
    dst = downloads / "Images" / "a.jpg"
    journal.append({"type": "intent", "src": str(src), "dst": str(dst)})
    os.replace(src, dst)
    window.recover_interrupted()
    assert window.messages[-1][0] == "Previous cleanup was interrupted"
    assert window.undo_button.isEnabled()


def test_theme_switch_light_dark_system_and_remembered(app, window, downloads, isolated_data_dir):
    from tidytray import settings
    from tidytray.ui import theme

    make(downloads, "a.jpg")
    window.load_folder(downloads)
    settle(app)
    window.set_theme(theme.LIGHT)
    assert theme.active_scheme() == theme.LIGHT
    assert app.palette().color(app.palette().ColorRole.Window).lightness() > 200
    assert settings.load()["theme"] == theme.LIGHT
    window.set_theme(theme.DARK)
    assert theme.active_scheme() == theme.DARK
    assert app.palette().color(app.palette().ColorRole.Window).lightness() < 60
    window.set_theme(theme.SYSTEM)
    assert theme.active_scheme() in (theme.LIGHT, theme.DARK)
    assert settings.load()["theme"] == theme.SYSTEM

    window.set_theme(theme.DARK)
    second = MainWindow(history=window.history)
    try:
        assert second.theme_mode == theme.DARK
        assert second.theme_buttons[theme.DARK].isChecked()
    finally:
        second.close()
        second.deleteLater()
