from pathlib import Path
import shutil
import subprocess

from yt_audio_downloader.models import AlbumDocument, AlbumInfo, SourceInfo, Track

ffmpeg_missing = shutil.which("ffmpeg") is None


def write_silent_m4a(path: Path, seconds: float = 1.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            str(seconds),
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            str(path),
        ],
        check=True,
    )
    return path


def write_cover_jpg(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=32x32",
            "-frames:v",
            "1",
            str(path),
        ],
        check=True,
    )
    return path


def sample_doc() -> AlbumDocument:
    return AlbumDocument(
        source=SourceInfo(
            url="https://www.youtube.com/watch?v=abc123def45",
            video_id="abc123def45",
            title="Some Artist - Live at Venue (2024)",
            duration="0:06",
        ),
        album=AlbumInfo(
            title="Live at Venue",
            artist="Some Artist",
            album_artist="Some Artist",
            date="2024",
            genre="Live",
        ),
        tracks=[
            Track(index=1, title="Intro", start="0:00", end="0:02"),
            Track(index=2, title="Opening Song", start="0:02", end="0:06"),
        ],
    )
