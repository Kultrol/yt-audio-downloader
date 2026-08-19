from __future__ import annotations

import os
from pathlib import Path

DEFAULT_LIBRARY = Path.home() / "Music" / "ytad"
_FORBIDDEN = '<>:"/\\|?*'


def library_root() -> Path:
    override = os.environ.get("YTAD_LIBRARY")
    return Path(override).expanduser() if override else DEFAULT_LIBRARY


def sanitize_name(name: str) -> str:
    cleaned = "".join("_" if ch in _FORBIDDEN else ch for ch in name).strip(" .")
    return cleaned or "untitled"


def album_project_dir(*, artist: str, date: str | None, title: str) -> Path:
    year = (date or "")[:4] if date and date[:4].isdigit() else None
    folder = f"{year} - {sanitize_name(title)}" if year else sanitize_name(title)
    return library_root() / sanitize_name(artist) / folder
