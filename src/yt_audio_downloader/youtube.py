from __future__ import annotations

import re
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


class DownloadFailed(RuntimeError):
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


_VIDEO_ID = re.compile(r"(?:v=|/|youtu\.be/)([A-Za-z0-9_-]{11})")
_ANSI = re.compile(r"\x1b\[[0-9;]*m|\[[0-9;]+m")


def unescape_copied_url(url: str) -> str:
    return (
        url.strip()
        .replace(r"\?", "?")
        .replace(r"\=", "=")
        .replace(r"\&", "&")
        .replace("\\", "")
    )


def extract_video_id(url: str) -> str | None:
    match = _VIDEO_ID.search(unescape_copied_url(url))
    return match.group(1) if match else None


def is_youtube_url(url: str) -> bool:
    parsed = urlparse(unescape_copied_url(url))
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return host in YOUTUBE_HOSTS


def canonical_watch_url(url: str) -> str:
    video_id = extract_video_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return unescape_copied_url(url)


def clean_ydl_error(message: str) -> str:
    text = _ANSI.sub("", message)
    text = text.replace("ERROR:", "").strip()
    return text or "download failed"


def pick_thumbnail_url(primary: str | None, thumbnails: list[dict] | None = None) -> str | None:
    urls = [str(item.get("url")) for item in (thumbnails or []) if item.get("url")]
    if primary:
        urls.append(primary)

    def _is_jpeg(url: str) -> bool:
        lower = url.lower()
        return ".jpg" in lower or ".jpeg" in lower

    jpegs = [url for url in urls if _is_jpeg(url)]
    if jpegs:
        return jpegs[-1]
    pngs = [url for url in urls if ".png" in url.lower()]
    if pngs:
        return pngs[-1]
    non_webp = [url for url in urls if "webp" not in url.lower()]
    if non_webp:
        return non_webp[-1]
    return urls[-1] if urls else None


def ydl_opts(*, download: bool, verbose: bool = False) -> dict:
    opts: dict = {
        "quiet": not verbose,
        "no_warnings": not verbose,
        "noplaylist": True,
        "source_address": "0.0.0.0",
        "js_runtimes": {"node": {}, "deno": {}},
        "remote_components": ["ejs:github"],
        "extractor_args": {
            "youtube": {"player_client": ["web_embedded", "android"]},
        },
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 3,
        "socket_timeout": 30,
    }
    if download:
        opts["format"] = "bestaudio/best"
        opts["noprogress"] = not verbose
    else:
        opts["skip_download"] = True
        opts["quiet"] = True
        opts["no_warnings"] = True
    return opts


def _extract_info(url: str) -> VideoInfo:
    from yt_dlp import YoutubeDL

    with YoutubeDL(ydl_opts(download=False)) as ydl:
        raw = ydl.extract_info(url, download=False)
    if not raw:
        raise RuntimeError(f"could not extract info for {url}")
    chapters = raw.get("chapters") or []
    video_id = str(raw.get("id") or extract_video_id(url) or "")
    stored_url = (
        f"https://www.youtube.com/watch?v={video_id}"
        if len(video_id) == 11
        else canonical_watch_url(url)
    )
    thumbnail = pick_thumbnail_url(raw.get("thumbnail"), raw.get("thumbnails"))
    if video_id and (not thumbnail or "webp" in thumbnail.lower()):
        thumbnail = pick_thumbnail_url(
            thumbnail,
            [{"url": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"}],
        )
    return VideoInfo(
        url=stored_url,
        video_id=video_id,
        title=str(raw.get("title") or "Untitled"),
        duration_seconds=float(raw.get("duration") or 0),
        description=str(raw.get("description") or ""),
        thumbnail_url=thumbnail,
        chapters=chapters,
        uploader=str(raw.get("uploader") or raw.get("channel") or ""),
    )


def inspect(url: str) -> VideoInfo:
    if not is_youtube_url(url):
        raise NotYouTubeURLError(f"only YouTube URLs are supported: {url}")
    return _extract_info(canonical_watch_url(url))


def download_audio(
    url: str,
    dest_dir: Path,
    *,
    on_progress=None,
    verbose: bool = False,
) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for leftover in dest_dir.glob("audio.*"):
        leftover.unlink()

    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, YoutubeDLError

    opts = ydl_opts(download=True, verbose=verbose)
    opts["outtmpl"] = str(dest_dir / "audio.%(ext)s")
    if on_progress is not None:
        opts["progress_hooks"] = [on_progress]
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(canonical_watch_url(url), download=True)
            if not info:
                raise DownloadFailed(f"could not download audio for {url}")
            filename = ydl.prepare_filename(info)
    except (DownloadError, YoutubeDLError) as exc:
        raise DownloadFailed(clean_ydl_error(str(exc))) from exc
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
