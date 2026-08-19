import pytest
from pydantic import ValidationError

from yt_audio_downloader.models import AlbumDocument, Track


def _doc(**overrides) -> AlbumDocument:
    data = {
        "source": {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "video_id": "dQw4w9WgXcQ",
            "title": "Artist - Live at Venue (2024)",
            "duration": "2:01:03",
        },
        "album": {
            "title": "Live at Venue",
            "artist": "Artist",
            "album_artist": "Artist",
            "date": "2024",
            "genre": "Live",
        },
        "tracks": [
            {"index": 1, "title": "Intro", "start": "0:00", "end": "1:23"},
        ],
    }
    data.update(overrides)
    return AlbumDocument.model_validate(data)


def test_round_trip_json():
    doc = _doc()
    loaded = AlbumDocument.model_validate_json(doc.model_dump_json())
    assert loaded.album.title == "Live at Venue"
    assert loaded.tracks[0].start == "0:00"
    assert loaded.schema_version == 1


def test_track_index_must_be_positive():
    with pytest.raises(ValidationError):
        Track(index=0, title="x", start="0:00", end="1:00")


def test_invalid_timestamp_rejected():
    with pytest.raises(ValidationError):
        Track(index=1, title="x", start="abc", end="1:00")
