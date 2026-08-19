from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from yt_audio_downloader.config import sanitize_name
from yt_audio_downloader.models import AlbumDocument
from yt_audio_downloader.tags import write_tags
from yt_audio_downloader.validate import track_span, validate_tracks

AAC_BITRATE = "256k"
AUDIO_EXTENSIONS = {".m4a", ".webm", ".opus", ".ogg", ".mp3", ".wav", ".mka", ".aac", ".mp4"}


def find_source_audio(source_dir: Path) -> Path:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"no downloaded audio in {source_dir}")
    files = [
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    ]
    if not files:
        raise FileNotFoundError(f"no downloaded audio in {source_dir}")
    return sorted(files)[0]


def split_and_encode(
    source_audio: Path,
    doc: AlbumDocument,
    dest_dir: Path,
    cover: Path | None = None,
    on_track: Callable[[int, int, str], None] | None = None,
) -> list[Path]:
    validate_tracks(doc)
    if not source_audio.is_file():
        raise FileNotFoundError(f"source audio not found: {source_audio}")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not on PATH; install it and run `ytad doctor`")

    dest_dir.mkdir(parents=True, exist_ok=True)
    duration = None
    if doc.source.duration:
        from yt_audio_downloader.timestamps import parse_timestamp

        duration = parse_timestamp(doc.source.duration)

    cover_path = cover if cover is not None else dest_dir.parent / "cover.jpg"
    if cover_path is not None and not cover_path.is_file():
        cover_path = None

    outputs: list[Path] = []
    tracks = sorted(doc.tracks, key=lambda item: item.index)
    total = len(tracks)
    for track in tracks:
        if on_track is not None:
            on_track(track.index, total, track.title)
        start, end = track_span(track, duration)
        filename = f"{track.index:02d} - {sanitize_name(track.title)}.m4a"
        output = dest_dir / filename
        _extract_segment(source_audio, output, start, end)
        write_tags(output, doc, track, cover_path)
        outputs.append(output)

    if cover_path is not None:
        shutil.copyfile(cover_path, dest_dir / "cover.jpg")
    return outputs


def _extract_segment(source: Path, dest: Path, start: float, end: float) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-ss",
        f"{start:.3f}",
        "-to",
        f"{end:.3f}",
        "-vn",
        "-c:a",
        "aac",
        "-b:a",
        AAC_BITRATE,
        "-movflags",
        "+faststart",
        str(dest),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "ffmpeg failed").strip()
        raise RuntimeError(detail)
    if not dest.is_file():
        raise RuntimeError(f"ffmpeg did not write {dest}")
