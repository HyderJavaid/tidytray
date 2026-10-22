from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tidytray.history import History  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path_factory, monkeypatch):
    """Keep every test's history away from the real user data folder."""
    data = tmp_path_factory.mktemp("tidytray-data")
    monkeypatch.setenv("TIDYTRAY_DATA_DIR", str(data))
    return data


@pytest.fixture
def history(isolated_data_dir):
    return History(isolated_data_dir / "history")


@pytest.fixture
def downloads(tmp_path):
    folder = tmp_path / "Downloads"
    folder.mkdir()
    return folder


def make(folder: Path, name: str, content: str | bytes = "x") -> Path:
    path = folder / name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def can_symlink(tmp_path: Path) -> bool:
    try:
        os.symlink(tmp_path, tmp_path / "__probe_link")
    except (OSError, NotImplementedError):
        return False
    os.unlink(tmp_path / "__probe_link")
    return True
