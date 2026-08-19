from pathlib import Path

import pytest
from mutagen.mp4 import MP4

from tests.media_helpers import ffmpeg_missing, sample_doc, write_cover_jpg, write_silent_m4a
from yt_audio_downloader.media import find_source_audio, split_and_encode
from yt_audio_downloader.validate import TracklistError

pytestmark = pytest.mark.skipif(ffmpeg_missing, reason="ffmpeg is required")


def test_split_and_encode_writes_tagged_tracks(tmp_path: Path):
    source = write_silent_m4a(tmp_path / "source" / "audio.m4a", seconds=6)
    write_cover_jpg(tmp_path / "cover.jpg")
    dest = tmp_path / "export"
    paths = split_and_encode(source, sample_doc(), dest)
    assert [p.name for p in paths] == ["01 - Intro.m4a", "02 - Opening Song.m4a"]
    tagged = MP4(paths[0])
    assert tagged["\xa9nam"] == ["Intro"]
    assert tagged["\xa9alb"] == ["Live at Venue"]
    assert tagged["trkn"] == [(1, 2)]
    assert (dest / "cover.jpg").is_file()


def test_split_and_encode_rejects_empty_tracks(tmp_path: Path):
    source = write_silent_m4a(tmp_path / "audio.m4a", seconds=1)
    doc = sample_doc()
    doc.tracks = []
    with pytest.raises(TracklistError, match="no tracks"):
        split_and_encode(source, doc, tmp_path / "export")


def test_find_source_audio_picks_downloaded_file(tmp_path: Path):
    dest = tmp_path / "source"
    dest.mkdir()
    (dest / "notes.txt").write_text("ignore")
    audio = dest / "audio.webm"
    audio.write_bytes(b"data")
    assert find_source_audio(dest) == audio


def test_find_source_audio_missing(tmp_path: Path):
    dest = tmp_path / "source"
    dest.mkdir()
    with pytest.raises(FileNotFoundError):
        find_source_audio(dest)
