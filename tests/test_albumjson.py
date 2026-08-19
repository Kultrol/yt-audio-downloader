from pathlib import Path

import pytest

from yt_audio_downloader.albumjson import load_album, save_album
from yt_audio_downloader.models import AlbumDocument, AlbumInfo, SourceInfo, Track


def test_save_and_load_round_trip(tmp_path: Path):
    doc = AlbumDocument(
        source=SourceInfo(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            title="Artist - Live",
            duration="10:00",
        ),
        album=AlbumInfo(title="Live", artist="Artist"),
        tracks=[Track(index=1, title="Intro", start="0:00", end="1:00")],
    )
    path = tmp_path / "album.json"
    save_album(path, doc)
    loaded = load_album(path)
    assert loaded.album.artist == "Artist"
    assert loaded.tracks[0].title == "Intro"


def test_load_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_album(tmp_path / "album.json")
