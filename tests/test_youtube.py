import pytest

from yt_audio_downloader.youtube import (
    NotYouTubeURLError,
    VideoInfo,
    inspect,
    is_youtube_url,
)


def test_is_youtube_url_accepts_watch_and_short():
    assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
    assert is_youtube_url("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
    assert not is_youtube_url("https://vimeo.com/123")
    assert not is_youtube_url("not-a-url")


def test_inspect_rejects_non_youtube():
    with pytest.raises(NotYouTubeURLError):
        inspect("https://vimeo.com/123")


def test_inspect_uses_extractor(monkeypatch):
    def fake_extract(url: str) -> VideoInfo:
        return VideoInfo(
            url=url,
            video_id="abc",
            title="Artist - Live at Venue (2024)",
            duration_seconds=200,
            description="0:00 Intro\n1:23 Song",
            thumbnail_url=None,
            chapters=[
                {"start_time": 0, "title": "Intro"},
                {"start_time": 83, "title": "Song"},
            ],
            uploader="Artist",
        )

    monkeypatch.setattr("yt_audio_downloader.youtube._extract_info", fake_extract)
    info = inspect("https://www.youtube.com/watch?v=abc")
    assert info.video_id == "abc"
    assert info.chapters[1]["title"] == "Song"
