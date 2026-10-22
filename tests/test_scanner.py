import os
import sys

import pytest

from conftest import can_symlink, make
from tidytray.categories import (
    ARCHIVES, AUDIO, CODE, DOCUMENTS, IMAGES, INSTALLERS, OTHER, VIDEOS, classify,
)
from tidytray.scanner import ScanError, scan_folder


@pytest.mark.parametrize(
    "name, category",
    [
        ("photo.JPG", IMAGES),
        ("scan.png", IMAGES),
        ("report.pdf", DOCUMENTS),
        ("notes.TXT", DOCUMENTS),
        ("movie.mkv", VIDEOS),
        ("song.mp3", AUDIO),
        ("backup.zip", ARCHIVES),
        ("source.tar.gz", ARCHIVES),
        ("setup.exe", INSTALLERS),
        ("tool.AppImage", INSTALLERS),
        ("package.deb", INSTALLERS),
        ("script.py", CODE),
        ("mystery.xyz", OTHER),
        ("README", OTHER),
    ],
)
def test_classify(name, category):
    assert classify(name) == category


def test_scan_counts_and_sizes(downloads):
    make(downloads, "a.jpg", "12345")
    make(downloads, "b.png", "123")
    make(downloads, "c.pdf", "1")
    make(downloads, "d.unknown", "")
    result = scan_folder(downloads)
    summary = result.summary()
    assert summary[IMAGES] == (2, 8)
    assert summary[DOCUMENTS] == (1, 1)
    assert summary[OTHER] == (1, 0)
    assert summary[VIDEOS] == (0, 0)
    assert result.total_size == 9


def test_scan_is_not_recursive(downloads):
    sub = downloads / "Nested"
    sub.mkdir()
    make(sub, "deep.jpg")
    make(downloads, "top.jpg")
    result = scan_folder(downloads)
    assert [f.name for f in result.files] == ["top.jpg"]


def test_scan_skips_hidden_and_partial_downloads(downloads):
    make(downloads, ".hidden.jpg")
    make(downloads, "movie.mp4.crdownload")
    make(downloads, "file.part")
    make(downloads, "ok.txt")
    result = scan_folder(downloads)
    assert [f.name for f in result.files] == ["ok.txt"]
    reasons = {s.path.name: s.reason for s in result.skipped}
    assert "Hidden" in reasons[".hidden.jpg"]
    assert "in progress" in reasons["movie.mp4.crdownload"]
    assert "file.part" in reasons


def test_scan_skips_symlinks(downloads, tmp_path):
    if not can_symlink(tmp_path):
        pytest.skip("Symbolic links not permitted for this user (Windows without Developer Mode)")
    outside = tmp_path / "outside.jpg"
    outside.write_text("secret")
    os.symlink(outside, downloads / "link.jpg")
    os.symlink(tmp_path, downloads / "linkdir")
    result = scan_folder(downloads)
    assert result.files == []
    assert {s.path.name for s in result.skipped} == {"link.jpg", "linkdir"}


def test_scan_missing_folder_raises(tmp_path):
    with pytest.raises(ScanError):
        scan_folder(tmp_path / "nope")


def test_scan_file_instead_of_folder_raises(tmp_path):
    f = make(tmp_path, "file.txt")
    with pytest.raises(ScanError):
        scan_folder(f)


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX permissions as a normal user")
def test_scan_unreadable_folder_raises(downloads):
    downloads.chmod(0o000)
    try:
        with pytest.raises(ScanError, match="permission"):
            scan_folder(downloads)
    finally:
        downloads.chmod(0o755)
