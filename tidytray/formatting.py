"""Human-friendly text for sizes, counts and dates."""

from __future__ import annotations

from datetime import datetime


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}" if size < 100 else f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.0f} TB"


def plural(count: int, word: str, plural_word: str | None = None) -> str:
    return f"{count} {word if count == 1 else (plural_word or word + 's')}"


def short_date(timestamp: float | datetime) -> str:
    moment = timestamp if isinstance(timestamp, datetime) else datetime.fromtimestamp(timestamp)
    return moment.strftime("%Y-%m-%d %H:%M")
