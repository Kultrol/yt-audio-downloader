from __future__ import annotations

import re

from yt_audio_downloader.models import AlbumInfo, Track
from yt_audio_downloader.timestamps import (
    format_timestamp,
    parse_description_timestamps,
    tracks_from_chapters,
    tracks_from_timed_titles,
)
from yt_audio_downloader.youtube import VideoInfo

_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def select_tracks(info: VideoInfo) -> list[Track]:
    duration = info.duration_seconds
    if info.chapters:
        return tracks_from_chapters(info.chapters, duration)
    pairs = parse_description_timestamps(info.description)
    if pairs:
        return tracks_from_timed_titles(pairs, duration)
    return []


def guess_album(info: VideoInfo) -> AlbumInfo:
    title = info.title.strip()
    artist = info.uploader.strip() or "Unknown Artist"
    rest = title
    if " - " in title:
        left, right = title.split(" - ", 1)
        if left.strip():
            artist = left.strip()
            rest = right.strip()
    year_match = _YEAR.search(title)
    date = year_match.group(1) if year_match else None
    album_title = rest
    if date:
        album_title = re.sub(rf"[\(\[\-,\s]*{date}[\)\]]*", "", album_title).strip(" -–—")
    if not album_title:
        album_title = title or "Untitled Album"
    return AlbumInfo(
        title=album_title,
        artist=artist,
        album_artist=artist,
        date=date,
        genre="Live",
    )


def source_duration(info: VideoInfo) -> str:
    return format_timestamp(info.duration_seconds)
