from pathlib import Path

from yt_audio_downloader.config import album_project_dir, library_root, sanitize_name


def test_library_root_uses_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("YTAD_LIBRARY", str(tmp_path))
    assert library_root() == tmp_path


def test_sanitize_name_strips_forbidden_chars():
    assert sanitize_name("A/B:C*") == "A_B_C_"
    assert sanitize_name("  .  ") == "untitled"


def test_album_project_dir_layout(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("YTAD_LIBRARY", str(tmp_path))
    path = album_project_dir(artist="Artist Name", date="2024", title="Live at Venue")
    assert path == tmp_path / "Artist Name" / "2024 - Live at Venue"
