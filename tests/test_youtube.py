import pytest

from pathlib import Path

from yt_audio_downloader.youtube import (
    DownloadFailed,
    NotYouTubeURLError,
    VideoInfo,
    canonical_watch_url,
    clean_ydl_error,
    download_audio,
    extract_video_id,
    inspect,
    is_youtube_url,
    pick_thumbnail_url,
    save_thumbnail,
    ydl_opts,
)


def test_is_youtube_url_accepts_watch_and_short():
    assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
    assert is_youtube_url("https://youtu.be/9Z8v-4SLbM4?si=osHYeKkVTnQABdWq")
    assert is_youtube_url("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
    assert not is_youtube_url("https://vimeo.com/123")
    assert not is_youtube_url("not-a-url")


def test_canonical_watch_url_strips_share_params():
    assert (
        canonical_watch_url("https://youtu.be/9Z8v-4SLbM4?si=osHYeKkVTnQABdWq")
        == "https://www.youtube.com/watch?v=9Z8v-4SLbM4"
    )
    assert (
        canonical_watch_url("https://www.youtube.com/watch?v=9Z8v-4SLbM4&t=12s")
        == "https://www.youtube.com/watch?v=9Z8v-4SLbM4"
    )


def test_canonical_watch_url_handles_shell_escaped_share_link():
    raw = r"https://youtu.be/GgnClrx8N2k\?si\=gC3MbSE7f7anCHv_"
    assert canonical_watch_url(raw) == "https://www.youtube.com/watch?v=GgnClrx8N2k"
    assert is_youtube_url(raw)


def test_extract_video_id_from_noisy_string():
    assert extract_video_id(r"https://youtu.be/GgnClrx8N2k\?si\=abc") == "GgnClrx8N2k"


def test_clean_ydl_error_strips_ansi_and_error_prefix():
    raw = "\x1b[0;31mERROR:\x1b[0m  Got error: _ssl.c:993: The handshake operation timed out"
    cleaned = clean_ydl_error(raw)
    assert "handshake operation timed out" in cleaned
    assert "[0;31m" not in cleaned
    assert "ERROR:" not in cleaned


def test_pick_thumbnail_url_prefers_jpeg_over_webp():
    webp = "https://i.ytimg.com/vi_webp/abc/maxresdefault.webp"
    jpg = "https://i.ytimg.com/vi/abc/maxresdefault.jpg"
    assert pick_thumbnail_url(webp, [{"url": webp}, {"url": jpg}]) == jpg
    assert pick_thumbnail_url(webp, [{"url": webp}]) == webp


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


def test_inspect_canonicalizes_share_urls(monkeypatch: pytest.MonkeyPatch):
    seen: dict[str, str] = {}

    def fake_extract(url: str) -> VideoInfo:
        seen["url"] = url
        return VideoInfo(
            url=url,
            video_id="9Z8v-4SLbM4",
            title="x",
            duration_seconds=1,
            description="",
            thumbnail_url=None,
        )

    monkeypatch.setattr("yt_audio_downloader.youtube._extract_info", fake_extract)
    inspect("https://youtu.be/9Z8v-4SLbM4?si=osHYeKkVTnQABdWq")
    assert seen["url"] == "https://www.youtube.com/watch?v=9Z8v-4SLbM4"


class FakeYDL:
    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=True):
        dest = Path(self.opts["outtmpl"].replace("%(ext)s", "webm"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"audio-bytes")
        return {"ext": "webm"}

    def prepare_filename(self, info):
        return self.opts["outtmpl"].replace("%(ext)s", info["ext"])


def test_download_audio_writes_source_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)
    dest = tmp_path / "source"
    leftover = dest / "audio.m4a"
    leftover.parent.mkdir()
    leftover.write_bytes(b"old")
    path = download_audio("https://www.youtube.com/watch?v=abc", dest)
    assert path == dest / "audio.webm"
    assert path.read_bytes() == b"audio-bytes"
    assert not leftover.exists()


def test_save_thumbnail_writes_cover(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"\xff\xd8cover"

    monkeypatch.setattr(
        "yt_audio_downloader.youtube.urllib.request.urlopen",
        lambda req, timeout=30: FakeResp(),
    )
    dest = tmp_path / "cover.jpg"
    result = save_thumbnail("https://i.ytimg.com/vi/abc/maxresdefault.jpg", dest)
    assert result == dest
    assert dest.read_bytes() == b"\xff\xd8cover"


def test_save_thumbnail_skips_missing_url(tmp_path: Path):
    assert save_thumbnail(None, tmp_path / "cover.jpg") is None
    assert not (tmp_path / "cover.jpg").exists()


def test_ydl_opts_use_working_youtube_client():
    opts = ydl_opts(download=True)
    assert opts["format"] == "bestaudio/best"
    assert opts["noplaylist"] is True
    assert opts["quiet"] is True
    assert opts["noprogress"] is True
    assert opts["source_address"] == "0.0.0.0"
    assert opts["retries"] == 10
    assert opts["fragment_retries"] == 10
    assert opts["socket_timeout"] == 30
    assert "node" in opts["js_runtimes"]
    assert "deno" in opts["js_runtimes"]
    assert "ejs:github" in opts["remote_components"]
    clients = opts["extractor_args"]["youtube"]["player_client"]
    assert "web_embedded" in clients
    assert "android" in clients


def test_ydl_opts_verbose_unmutes_yt_dlp():
    opts = ydl_opts(download=True, verbose=True)
    assert opts["quiet"] is False
    assert opts["noprogress"] is False


def test_download_audio_wraps_yt_dlp_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    class BoomYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=True):
            from yt_dlp.utils import DownloadError

            raise DownloadError("ERROR: unable to download video data: HTTP Error 403: Forbidden")

    monkeypatch.setattr("yt_dlp.YoutubeDL", BoomYDL)
    with pytest.raises(DownloadFailed, match="403"):
        download_audio("https://www.youtube.com/watch?v=abc", tmp_path / "source")
