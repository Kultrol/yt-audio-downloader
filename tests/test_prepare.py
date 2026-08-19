from yt_audio_downloader.prepare import guess_album, select_tracks
from yt_audio_downloader.youtube import VideoInfo


def _info(**kwargs) -> VideoInfo:
    base = dict(
        url="https://www.youtube.com/watch?v=abc",
        video_id="abc",
        title="Some Artist - Live at Venue (2024)",
        duration_seconds=500,
        description="",
        thumbnail_url=None,
        chapters=[],
        uploader="Uploader",
    )
    base.update(kwargs)
    return VideoInfo(**base)


def test_select_tracks_prefers_chapters_over_description():
    info = _info(
        description="0:00 Wrong\n1:00 Also Wrong",
        chapters=[
            {"start_time": 0, "title": "Intro"},
            {"start_time": 83, "title": "Song"},
        ],
    )
    tracks = select_tracks(info)
    assert [t.title for t in tracks] == ["Intro", "Song"]


def test_select_tracks_falls_back_to_description():
    info = _info(description="0:00 Intro\n1:23 Opening Song\n")
    tracks = select_tracks(info)
    assert [t.title for t in tracks] == ["Intro", "Opening Song"]
    assert tracks[-1].end == "8:20"


def test_select_tracks_empty_when_no_chapters_or_list():
    info = _info(description="just a concert vlog with no times")
    assert select_tracks(info) == []


def test_guess_album_splits_artist_and_year():
    album = guess_album(_info())
    assert album.artist == "Some Artist"
    assert album.title == "Live at Venue"
    assert album.date == "2024"
    assert album.album_artist == "Some Artist"
