from pathlib import Path

from yt_audio_downloader.models import AlbumDocument


def split_and_encode(source_audio: Path, doc: AlbumDocument, dest_dir: Path) -> list[Path]:
    raise NotImplementedError("build/split is not implemented yet")
