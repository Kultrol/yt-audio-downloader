from pathlib import Path

import pytest
from mutagen.mp4 import MP4

from tests.media_helpers import ffmpeg_missing, sample_doc, write_cover_jpg, write_silent_m4a
from yt_audio_downloader.tags import write_tags

pytestmark = pytest.mark.skipif(ffmpeg_missing, reason="ffmpeg is required")


def test_write_tags_sets_mp4_metadata_and_cover(tmp_path: Path):
    audio = write_silent_m4a(tmp_path / "01 - Intro.m4a")
    cover = write_cover_jpg(tmp_path / "cover.jpg")
    doc = sample_doc()
    write_tags(audio, doc, doc.tracks[0], cover)

    tagged = MP4(audio)
    assert tagged["\xa9nam"] == ["Intro"]
    assert tagged["\xa9ART"] == ["Some Artist"]
    assert tagged["\xa9alb"] == ["Live at Venue"]
    assert tagged["aART"] == ["Some Artist"]
    assert tagged["trkn"] == [(1, 2)]
    assert tagged["\xa9day"] == ["2024"]
    assert tagged["\xa9gen"] == ["Live"]
    assert tagged.get("covr")
    assert len(bytes(tagged["covr"][0])) == len(cover.read_bytes())
