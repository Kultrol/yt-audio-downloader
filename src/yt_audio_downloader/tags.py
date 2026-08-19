from pathlib import Path

from yt_audio_downloader.models import AlbumDocument, Track


def write_tags(path: Path, doc: AlbumDocument, track: Track, cover: Path | None) -> None:
    raise NotImplementedError("tagging is not implemented yet")
