"""Small local preferences file (currently just the theme)."""

from __future__ import annotations

import json

from .paths import data_dir


def _path():
    return data_dir() / "settings.json"


def load() -> dict:
    try:
        with open(_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(**values) -> None:
    data = load()
    data.update(values)
    try:
        path = _path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass  # Preferences are a convenience; never block the app on them.
