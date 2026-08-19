from __future__ import annotations

from pathlib import Path

from yt_audio_downloader.albumjson import save_album
from yt_audio_downloader.config import album_project_dir
from yt_audio_downloader.models import AlbumDocument, SourceInfo
from yt_audio_downloader.prepare import guess_album, select_tracks, source_duration
from yt_audio_downloader.youtube import VideoInfo, save_thumbnail


def create_album_project(info: VideoInfo) -> Path:
    album = guess_album(info)
    tracks = select_tracks(info)
    dest = album_project_dir(artist=album.artist, date=album.date, title=album.title)
    if dest.exists():
        dest = dest.with_name(f"{dest.name}-{info.video_id}")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "source").mkdir(exist_ok=True)
    (dest / "export").mkdir(exist_ok=True)
    doc = AlbumDocument(
        source=SourceInfo(
            url=info.url,
            video_id=info.video_id,
            title=info.title,
            duration=source_duration(info),
            thumbnail_url=info.thumbnail_url,
        ),
        album=album,
        tracks=tracks,
    )
    save_album(dest / "album.json", doc)
    try:
        save_thumbnail(info.thumbnail_url, dest / "cover.jpg")
    except OSError:
        pass
    return dest
