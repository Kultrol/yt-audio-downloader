import pytest

from yt_audio_downloader.models import AlbumDocument, AlbumInfo, SourceInfo, Track
from yt_audio_downloader.validate import TracklistError, validate_tracks


def _doc(tracks: list[Track], duration: str = "10:00") -> AlbumDocument:
    return AlbumDocument(
        source=SourceInfo(
            url="https://www.youtube.com/watch?v=abc",
            video_id="abc",
            title="Live",
            duration=duration,
        ),
        album=AlbumInfo(title="Live", artist="Artist"),
        tracks=tracks,
    )


def test_validate_accepts_contiguous_tracks():
    validate_tracks(
        _doc(
            [
                Track(index=1, title="A", start="0:00", end="1:00"),
                Track(index=2, title="B", start="1:00", end="3:00"),
            ]
        )
    )


def test_validate_allows_gaps():
    validate_tracks(
        _doc(
            [
                Track(index=1, title="A", start="0:00", end="1:00"),
                Track(index=2, title="B", start="1:30", end="3:00"),
            ]
        )
    )


def test_validate_rejects_empty_tracklist():
    with pytest.raises(TracklistError, match="no tracks"):
        validate_tracks(_doc([]))


def test_validate_rejects_overlap():
    with pytest.raises(TracklistError, match="overlap"):
        validate_tracks(
            _doc(
                [
                    Track(index=1, title="A", start="0:00", end="1:30"),
                    Track(index=2, title="B", start="1:00", end="3:00"),
                ]
            )
        )


def test_validate_rejects_end_before_start():
    with pytest.raises(TracklistError, match="end"):
        validate_tracks(
            _doc([Track(index=1, title="A", start="2:00", end="1:00")])
        )


def test_validate_rejects_end_past_duration():
    with pytest.raises(TracklistError, match="duration"):
        validate_tracks(
            _doc(
                [Track(index=1, title="A", start="0:00", end="12:00")],
                duration="10:00",
            )
        )
