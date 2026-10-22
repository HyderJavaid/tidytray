import json
import os
import sys

import pytest

from conftest import can_symlink, make
from tidytray.fsops import move_no_overwrite, unique_name
from tidytray.history import History
from tidytray.organizer import UnsafeFolderError, execute_plan, undo_operation
from tidytray.planner import build_plan
from tidytray.scanner import scan_folder


def snapshot(folder):
    """Map relative path -> content for every file under ``folder``."""
    out = {}
    for path in folder.rglob("*"):
        if path.is_file():
            out[path.relative_to(folder).as_posix()] = path.read_bytes()
    return out


def plan_all(folder):
    result = scan_folder(folder)
    return build_plan(result.root, result.files)


def test_plan_does_not_touch_files(downloads):
    make(downloads, "a.jpg")
    make(downloads, "b.pdf")
    before = snapshot(downloads)
    plan = plan_all(downloads)
    assert len(plan.moves) == 2
    assert snapshot(downloads) == before
    assert not (downloads / "Images").exists()


def test_plan_resolves_conflicts_with_existing_and_planned_names(downloads):
    (downloads / "Images").mkdir()
    make(downloads / "Images", "photo.jpg", "old")
    make(downloads, "photo.jpg", "new")
    case_sensitive = not (downloads / "PHOTO.JPG").exists()
    if case_sensitive:
        make(downloads, "Photo.JPG", "new2")  # would clash on Windows disks
    plan = plan_all(downloads)
    names = [m.destination.name for m in plan.moves]
    expected = 2 if case_sensitive else 1
    assert len({n.casefold() for n in names}) == expected
    assert all(n.casefold() != "photo.jpg" for n in names)
    assert plan.renamed_count == expected


def test_unique_name_keeps_compound_extension(tmp_path):
    make(tmp_path, "src.tar.gz")
    assert unique_name(tmp_path, "src.tar.gz") == "src (1).tar.gz"
    assert unique_name(tmp_path, "new.tar.gz") == "new.tar.gz"


def test_organize_moves_selected_files_only(downloads, history):
    make(downloads, "a.jpg", "A")
    make(downloads, "b.pdf", "B")
    make(downloads, "c.mp3", "C")
    scan = scan_folder(downloads)
    selected = [f for f in scan.files if f.name != "c.mp3"]
    plan = build_plan(scan.root, selected)
    result = execute_plan(plan, history)
    assert len(result.moved) == 2 and not result.failed
    assert snapshot(downloads) == {"Images/a.jpg": b"A", "Documents/b.pdf": b"B", "c.mp3": b"C"}


def test_organize_never_overwrites_file_created_after_planning(downloads, history):
    make(downloads, "a.jpg", "mine")
    plan = plan_all(downloads)
    (downloads / "Images").mkdir()
    make(downloads / "Images", "a.jpg", "appeared later")
    result = execute_plan(plan, history)
    assert not result.failed
    assert (downloads / "Images" / "a.jpg").read_text() == "appeared later"
    assert (downloads / "Images" / "a (1).jpg").read_text() == "mine"


def test_move_no_overwrite_refuses_existing(tmp_path):
    src = make(tmp_path, "s.txt", "src")
    dst = make(tmp_path, "d.txt", "dst")
    with pytest.raises(FileExistsError):
        move_no_overwrite(src, dst)
    assert src.read_text() == "src" and dst.read_text() == "dst"


def test_organize_reports_missing_file(downloads, history):
    a = make(downloads, "a.jpg")
    make(downloads, "b.jpg")
    plan = plan_all(downloads)
    a.unlink()
    result = execute_plan(plan, history)
    assert len(result.moved) == 1
    assert result.failed[0][0].name == "a.jpg"
    assert "no longer exists" in result.failed[0][1]


def test_organize_skips_category_folder_that_is_a_file(downloads, history):
    make(downloads, "Images", "I am a file")
    make(downloads, "a.jpg")
    make(downloads, "b.pdf")
    plan = plan_all(downloads)
    # The extension-less "Images" file itself is filed under Other.
    assert sorted(m.source.name for m in plan.moves) == ["Images", "b.pdf"]
    assert [s.path.name for s in plan.skipped] == ["a.jpg"]
    plan.moves = [m for m in plan.moves if m.source.name != "Images"]
    execute_plan(plan, history)
    assert (downloads / "Images").read_text() == "I am a file"
    assert (downloads / "a.jpg").exists()


def test_organize_skips_category_folder_that_is_a_symlink(downloads, history, tmp_path):
    if not can_symlink(tmp_path):
        pytest.skip("Symbolic links not permitted")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    os.symlink(elsewhere, downloads / "Images", target_is_directory=True)
    make(downloads, "a.jpg")
    plan = plan_all(downloads)
    assert plan.moves == []
    assert list(elsewhere.iterdir()) == []


def test_cancel_stops_between_files(downloads, history):
    for i in range(5):
        make(downloads, f"f{i}.txt")
    plan = plan_all(downloads)
    calls = {"n": 0}

    def should_cancel():
        calls["n"] += 1
        return calls["n"] > 2

    result = execute_plan(plan, history, should_cancel=should_cancel)
    assert result.cancelled
    assert len(result.moved) == 2
    op = history.operations()[0]
    assert op.status == "cancelled" and op.undoable


def test_refuses_unsafe_root(history, tmp_path):
    from pathlib import Path

    from tidytray.planner import Plan

    with pytest.raises(UnsafeFolderError):
        execute_plan(Plan(root=Path(Path.home().anchor)), history)
    with pytest.raises(UnsafeFolderError):
        execute_plan(Plan(root=Path.home()), history)


def test_undo_restores_everything(downloads, history):
    make(downloads, "a.jpg", "A")
    make(downloads, "b.pdf", "B")
    make(downloads, "c.tar.gz", "C")
    (downloads / "Documents").mkdir()  # pre-existing folder must survive undo
    before = snapshot(downloads)
    execute_plan(plan_all(downloads), history)
    assert snapshot(downloads) != before

    result = undo_operation(history)
    assert result is not None and len(result.restored) == 3 and not result.failed
    assert snapshot(downloads) == before
    assert not (downloads / "Images").exists()  # created by TidyTray, now empty
    assert not (downloads / "Archives").exists()
    assert (downloads / "Documents").is_dir()  # existed before; kept
    assert history.last_undoable() is None


def test_undo_never_overwrites_new_file_at_original_path(downloads, history):
    make(downloads, "a.jpg", "original")
    execute_plan(plan_all(downloads), history)
    make(downloads, "a.jpg", "newer download")
    result = undo_operation(history)
    assert result.renamed == 1
    assert (downloads / "a.jpg").read_text() == "newer download"
    assert (downloads / "a (1).jpg").read_text() == "original"


def test_undo_keeps_category_folder_with_new_user_files(downloads, history):
    make(downloads, "a.jpg")
    execute_plan(plan_all(downloads), history)
    make(downloads / "Images", "added-by-user.jpg")
    undo_operation(history)
    assert (downloads / "Images" / "added-by-user.jpg").exists()
    assert (downloads / "a.jpg").exists()


def test_undo_reports_file_removed_by_user(downloads, history):
    make(downloads, "a.jpg")
    make(downloads, "b.jpg")
    execute_plan(plan_all(downloads), history)
    (downloads / "Images" / "a.jpg").unlink()
    result = undo_operation(history)
    assert len(result.restored) == 1
    assert result.failed and result.failed[0][0].name == "a.jpg"


def test_undo_goes_back_one_operation_at_a_time(downloads, history):
    make(downloads, "a.jpg")
    execute_plan(plan_all(downloads), history)
    make(downloads, "b.pdf")
    execute_plan(plan_all(downloads), history)
    undo_operation(history)
    assert (downloads / "b.pdf").exists() and not (downloads / "a.jpg").exists()
    undo_operation(history)
    assert (downloads / "a.jpg").exists()
    assert undo_operation(history) is None


def test_history_is_stored_locally_as_json_lines(downloads, history, isolated_data_dir):
    make(downloads, "a.jpg")
    execute_plan(plan_all(downloads), history)
    journals = list((isolated_data_dir / "history").glob("op-*.jsonl"))
    assert len(journals) == 1
    records = [json.loads(line) for line in journals[0].read_text(encoding="utf-8").splitlines()]
    kinds = [r["type"] for r in records]
    assert kinds[0] == "begin" and kinds[-1] == "end"
    moved = [r for r in records if r["type"] == "moved"]
    assert moved[0]["src"] == str(downloads / "a.jpg")
    assert moved[0]["dst"] == str(downloads / "Images" / "a.jpg")


def _simulate_crash_after_intent(downloads, history, finish_move: str):
    """Write a journal as if the app died mid-move, then return the history."""
    src = make(downloads, "a.jpg", "A")
    done = make(downloads, "b.jpg", "B")
    (downloads / "Images").mkdir()
    journal = history.new_journal(downloads, 2)
    journal.append({"type": "mkdir", "path": str(downloads / "Images")})
    # b.jpg completed normally.
    journal.append({"type": "intent", "src": str(done), "dst": str(downloads / "Images" / "b.jpg")})
    os.replace(done, downloads / "Images" / "b.jpg")
    journal.append({"type": "moved", "src": str(done), "dst": str(downloads / "Images" / "b.jpg")})
    # a.jpg: intent written, then the crash.
    dst = downloads / "Images" / "a.jpg"
    journal.append({"type": "intent", "src": str(src), "dst": str(dst)})
    if finish_move == "renamed":
        os.replace(src, dst)
    elif finish_move == "linked":
        os.link(src, dst)
    # Truncated line from the crash:
    with open(journal.path, "a", encoding="utf-8") as fh:
        fh.write('{"type": "mov')
    return src, dst


@pytest.mark.parametrize("finish_move", ["none", "renamed", "linked"])
def test_recovery_after_interruption_then_undo(downloads, history, finish_move):
    if finish_move == "linked" and sys.platform == "win32":
        pytest.skip("The link-then-unlink step is POSIX only")
    src, dst = _simulate_crash_after_intent(downloads, history, finish_move)
    recovered = History(history.directory).recover_incomplete()
    assert len(recovered) == 1 and recovered[0].status == "interrupted"
    op = recovered[0]
    expected_moves = 1 if finish_move == "none" else 2
    assert len(op.moves) == expected_moves
    # Exactly one copy of a.jpg exists, never two names and never zero.
    assert os.path.exists(src) != os.path.exists(dst)

    result = undo_operation(history)
    assert len(result.restored) == expected_moves
    assert (downloads / "a.jpg").read_text() == "A"
    assert (downloads / "b.jpg").read_text() == "B"
    assert not (downloads / "Images").exists()


def test_undo_resumes_after_interruption(downloads, history):
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        make(downloads, name, name)
    execute_plan(plan_all(downloads), history)
    op = history.last_undoable()
    journal = op.journal
    # Simulate an undo that restored one file and died during the second.
    journal.append({"type": "undo_begin"})
    first, second = op.moves[-1], op.moves[-2]
    os.replace(first.destination, first.source)
    journal.append({"type": "restored", "dst": str(first.destination), "target": str(first.source)})
    journal.append({"type": "restore_intent", "dst": str(second.destination), "target": str(second.source)})
    os.replace(second.destination, second.source)

    result = undo_operation(history)
    assert result is not None
    assert snapshot(downloads) == {"a.jpg": b"a.jpg", "b.jpg": b"b.jpg", "c.jpg": b"c.jpg"}


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX permissions as a normal user")
def test_permission_error_is_reported_not_raised(downloads, history):
    make(downloads, "a.jpg")
    plan = plan_all(downloads)
    downloads.chmod(0o555)  # can't create the Images folder
    try:
        result = execute_plan(plan, history)
    finally:
        downloads.chmod(0o755)
    assert not result.moved
    assert "Permission denied" in result.failed[0][1]
    assert (downloads / "a.jpg").exists()


def test_unicode_and_odd_filenames_round_trip(downloads, history):
    names = ["résumé.pdf", "写真.jpg", "emoji 🎉.png", "spaces  and (parens).txt"]
    if sys.platform != "win32":
        names.append(os.fsdecode(b"bad-\xff-bytes.jpg"))  # not valid UTF-8; allowed on Linux
    for name in names:
        make(downloads, name, name.encode("utf-8", "surrogateescape"))
    before = snapshot(downloads)
    result = execute_plan(plan_all(downloads), history)
    assert len(result.moved) == len(names) and not result.failed
    undo = undo_operation(History(history.directory))
    assert len(undo.restored) == len(names)
    assert snapshot(downloads) == before
