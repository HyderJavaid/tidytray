"""File categories and extension-based classification."""

from __future__ import annotations

from pathlib import PurePath

IMAGES = "Images"
DOCUMENTS = "Documents"
VIDEOS = "Videos"
AUDIO = "Audio"
ARCHIVES = "Archives"
INSTALLERS = "Installers"
CODE = "Code"
OTHER = "Other"

# Display order used everywhere in the app.
CATEGORIES: tuple[str, ...] = (
    IMAGES,
    DOCUMENTS,
    VIDEOS,
    AUDIO,
    ARCHIVES,
    INSTALLERS,
    CODE,
    OTHER,
)

_EXTENSIONS: dict[str, tuple[str, ...]] = {
    IMAGES: (
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff",
        ".svg", ".ico", ".heic", ".heif", ".avif", ".raw", ".cr2", ".nef",
        ".arw", ".dng", ".psd", ".xcf",
    ),
    DOCUMENTS: (
        ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".xls",
        ".xlsx", ".ods", ".csv", ".tsv", ".ppt", ".pptx", ".odp", ".epub",
        ".mobi", ".pages", ".numbers", ".key", ".tex", ".log",
    ),
    VIDEOS: (
        ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".m4v",
        ".mpg", ".mpeg", ".3gp", ".ts",
    ),
    AUDIO: (
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".oga", ".opus", ".m4a",
        ".wma", ".aiff", ".aif", ".mid", ".midi",
    ),
    ARCHIVES: (
        ".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".tbz2",
        ".xz", ".txz", ".zst", ".lz", ".lzma", ".cab", ".iso",
    ),
    INSTALLERS: (
        ".exe", ".msi", ".msix", ".appx", ".appimage", ".deb", ".rpm",
        ".flatpakref", ".snap", ".dmg", ".pkg", ".apk", ".run",
    ),
    CODE: (
        ".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".java", ".c", ".h",
        ".cpp", ".hpp", ".cc", ".cs", ".go", ".rs", ".rb", ".php", ".swift",
        ".kt", ".kts", ".scala", ".sh", ".bash", ".ps1", ".bat", ".cmd",
        ".lua", ".pl", ".r", ".sql", ".html", ".htm", ".css", ".scss",
        ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".ipynb",
    ),
}

# ".ts" is ambiguous (TypeScript vs. MPEG transport stream). Downloads folders
# far more often hold source files than raw transport streams, so Code wins.
_EXTENSION_TO_CATEGORY: dict[str, str] = {}
for _category in (VIDEOS, IMAGES, DOCUMENTS, AUDIO, ARCHIVES, INSTALLERS, CODE):
    for _ext in _EXTENSIONS[_category]:
        _EXTENSION_TO_CATEGORY[_ext] = _category

# Multi-part archive suffixes that should be matched before the last suffix.
_COMPOUND_SUFFIXES: tuple[str, ...] = (
    ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst", ".tar.lz", ".tar.lzma",
)

# Files that are still being written by a browser or download manager.
PARTIAL_DOWNLOAD_SUFFIXES: tuple[str, ...] = (
    ".crdownload", ".part", ".partial", ".download", ".opdownload", ".tmp",
)


def compound_suffix(name: str) -> str:
    """Return the full extension of ``name``, keeping e.g. ``.tar.gz`` intact."""
    lower = name.lower()
    for suffix in _COMPOUND_SUFFIXES:
        if lower.endswith(suffix) and len(lower) > len(suffix):
            return name[-len(suffix):]
    return PurePath(name).suffix


def classify(name: str) -> str:
    """Return the category for a file name, based only on its extension."""
    suffix = compound_suffix(name).lower()
    if suffix in _COMPOUND_SUFFIXES:
        return ARCHIVES
    return _EXTENSION_TO_CATEGORY.get(suffix, OTHER)


def is_partial_download(name: str) -> bool:
    return name.lower().endswith(PARTIAL_DOWNLOAD_SUFFIXES)
