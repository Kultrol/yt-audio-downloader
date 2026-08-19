from __future__ import annotations

from pathlib import Path

from yt_audio_downloader.models import AlbumDocument


def load_album(path: Path) -> AlbumDocument:
    return AlbumDocument.model_validate_json(path.read_text(encoding="utf-8"))


def save_album(path: Path, doc: AlbumDocument) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc.model_dump_json(indent=2) + "\n", encoding="utf-8")
