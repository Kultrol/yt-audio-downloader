from __future__ import annotations

import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


class NotYouTubeURLError(ValueError):
    pass


@dataclass
class VideoInfo:
    url: str
    video_id: str
    title: str
    duration_seconds: float
    description: str
    thumbnail_url: str | None
    chapters: list[dict] = field(default_factory=list)
    uploader: str = ""


def is_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return host in YOUTUBE_HOSTS


def _extract_info(url: str) -> VideoInfo:
    from yt_dlp import YoutubeDL

    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with YoutubeDL(opts) as ydl:
        raw = ydl.extract_info(url, download=False)
    if not raw:
        raise RuntimeError(f"could not extract info for {url}")
    chapters = raw.get("chapters") or []
    return VideoInfo(
        url=url,
        video_id=str(raw.get("id") or ""),
        title=str(raw.get("title") or "Untitled"),
        duration_seconds=float(raw.get("duration") or 0),
        description=str(raw.get("description") or ""),
        thumbnail_url=raw.get("thumbnail"),
        chapters=chapters,
        uploader=str(raw.get("uploader") or raw.get("channel") or ""),
    )


def inspect(url: str) -> VideoInfo:
    if not is_youtube_url(url):
        raise NotYouTubeURLError(f"only YouTube URLs are supported: {url}")
    return _extract_info(url)


def download_audio(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for leftover in dest_dir.glob("audio.*"):
        leftover.unlink()

    from yt_dlp import YoutubeDL

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(dest_dir / "audio.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            raise RuntimeError(f"could not download audio for {url}")
        filename = ydl.prepare_filename(info)
    path = Path(filename)
    if path.exists():
        return path
    matches = sorted(p for p in dest_dir.glob("audio.*") if p.is_file())
    if len(matches) != 1:
        raise RuntimeError(f"download finished but audio file not found in {dest_dir}")
    return matches[0]


def save_thumbnail(url: str | None, dest: Path) -> Path | None:
    if not url:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "ytad/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        dest.write_bytes(response.read())
    return dest
