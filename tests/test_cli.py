from pathlib import Path

import pytest
from typer.testing import CliRunner

from yt_audio_downloader.albumjson import load_album, save_album
from yt_audio_downloader.cli import app
from yt_audio_downloader.models import AlbumDocument, AlbumInfo, SourceInfo, Track
from yt_audio_downloader.youtube import VideoInfo

runner = CliRunner()


def _sample_doc() -> AlbumDocument:
    return AlbumDocument(
        source=SourceInfo(
            url="https://www.youtube.com/watch?v=abc123def45",
            video_id="abc123def45",
            title="Some Artist - Live at Venue (2024)",
            duration="3:20",
        ),
        album=AlbumInfo(
            title="Live at Venue",
            artist="Some Artist",
            album_artist="Some Artist",
            date="2024",
            genre="Live",
        ),
        tracks=[
            Track(index=1, title="Intro", start="0:00", end="1:23"),
            Track(index=2, title="Opening Song", start="1:23", end="3:20"),
        ],
    )


@pytest.fixture
def album_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    save_album(tmp_path / "album.json", _sample_doc())
    return tmp_path


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "add" in result.stdout
    assert "doctor" in result.stdout


def test_doctor_runs():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code in (0, 1)
    combined = result.stdout.lower()
    assert "ffmpeg" in combined or "yt-dlp" in combined or "yt_dlp" in combined


def test_init_writes_album_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("YTAD_LIBRARY", str(tmp_path))

    def fake_inspect(url: str) -> VideoInfo:
        return VideoInfo(
            url=url,
            video_id="abc123def45",
            title="Some Artist - Live at Venue (2024)",
            duration_seconds=200,
            description="0:00 Intro\n1:23 Opening Song\n",
            thumbnail_url=None,
            chapters=[],
            uploader="Some Artist",
        )

    monkeypatch.setattr("yt_audio_downloader.cli.inspect", fake_inspect)
    result = runner.invoke(app, ["init", "https://www.youtube.com/watch?v=abc123def45"])
    assert result.exit_code == 0, result.stdout
    album_path = tmp_path / "Some Artist" / "2024 - Live at Venue" / "album.json"
    assert album_path.is_file()
    doc = load_album(album_path)
    assert [t.title for t in doc.tracks] == ["Intro", "Opening Song"]
    assert (album_path.parent / "source").is_dir()
    assert (album_path.parent / "export").is_dir()


def test_init_rejects_non_youtube(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("YTAD_LIBRARY", str(tmp_path))
    result = runner.invoke(app, ["init", "https://vimeo.com/123"])
    assert result.exit_code != 0


def test_show_prints_titles(album_dir: Path):
    result = runner.invoke(app, ["show"])
    assert result.exit_code == 0, result.stdout
    assert "Intro" in result.stdout


def test_set_updates_title(album_dir: Path):
    result = runner.invoke(app, ["set", "--title", "New Title"])
    assert result.exit_code == 0, result.stdout
    assert load_album(album_dir / "album.json").album.title == "New Title"


def test_tracks_set_updates_one_track(album_dir: Path):
    result = runner.invoke(
        app, ["tracks", "set", "1", "--title", "Renamed", "--start", "0:10"]
    )
    assert result.exit_code == 0, result.stdout
    track = load_album(album_dir / "album.json").tracks[0]
    assert track.title == "Renamed"
    assert track.start == "0:10"


def test_download_uses_youtube_downloader(
    album_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    called: dict[str, object] = {}

    def fake_download(url: str, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "audio.webm"
        path.write_bytes(b"audio")
        called["url"] = url
        called["path"] = path
        return path

    monkeypatch.setattr("yt_audio_downloader.cli.download_audio", fake_download)
    result = runner.invoke(app, ["download"])
    assert result.exit_code == 0, result.stdout
    assert called["url"] == "https://www.youtube.com/watch?v=abc123def45"
    assert (album_dir / "source" / "audio.webm").is_file()


def test_build_missing_source(album_dir: Path):
    result = runner.invoke(app, ["build"])
    assert result.exit_code != 0
    assert "no downloaded audio" in result.stdout.lower()


def test_build_exports_tracks(album_dir: Path, monkeypatch: pytest.MonkeyPatch):
    source = album_dir / "source"
    source.mkdir()
    (source / "audio.webm").write_bytes(b"audio")

    def fake_split(source_audio, doc, dest_dir, cover=None):
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = dest_dir / "01 - Intro.m4a"
        out.write_bytes(b"m4a")
        return [out]

    monkeypatch.setattr("yt_audio_downloader.cli.split_and_encode", fake_split)
    result = runner.invoke(app, ["build"])
    assert result.exit_code == 0, result.stdout
    assert "1 tracks" in result.stdout


def _fake_inspect(url: str) -> VideoInfo:
    return VideoInfo(
        url=url,
        video_id="abc123def45",
        title="Some Artist - Live at Venue (2024)",
        duration_seconds=200,
        description="0:00 Intro\n1:23 Opening Song\n",
        thumbnail_url=None,
        chapters=[],
        uploader="Some Artist",
    )


def test_add_yes_inits_downloads_and_builds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("YTAD_LIBRARY", str(tmp_path))
    monkeypatch.setattr("yt_audio_downloader.cli.inspect", _fake_inspect)

    def fake_download(url: str, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "audio.webm"
        path.write_bytes(b"audio")
        return path

    def fake_split(source_audio, doc, dest_dir, cover=None):
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = dest_dir / "01 - Intro.m4a"
        out.write_bytes(b"m4a")
        return [out]

    monkeypatch.setattr("yt_audio_downloader.cli.download_audio", fake_download)
    monkeypatch.setattr("yt_audio_downloader.cli.split_and_encode", fake_split)
    url = "https://www.youtube.com/watch?v=abc123def45"
    result = runner.invoke(app, ["add", url, "--yes"])
    assert result.exit_code == 0, result.stdout
    album_path = tmp_path / "Some Artist" / "2024 - Live at Venue" / "album.json"
    assert album_path.is_file()
    assert "Downloaded" in result.stdout
    assert "Wrote 1 tracks" in result.stdout


def test_add_can_stop_before_download(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("YTAD_LIBRARY", str(tmp_path))
    monkeypatch.setattr("yt_audio_downloader.cli.inspect", _fake_inspect)
    answers = iter([False, False])
    monkeypatch.setattr(
        "yt_audio_downloader.cli.Confirm.ask",
        lambda *args, **kwargs: next(answers),
    )
    downloaded: list[bool] = []
    monkeypatch.setattr(
        "yt_audio_downloader.cli.download_audio",
        lambda *args, **kwargs: downloaded.append(True),
    )
    url = "https://www.youtube.com/watch?v=abc123def45"
    result = runner.invoke(app, ["add", url])
    assert result.exit_code == 0, result.stdout
    assert downloaded == []
    assert "Stopped before download" in result.stdout
    assert (tmp_path / "Some Artist" / "2024 - Live at Venue" / "album.json").is_file()
