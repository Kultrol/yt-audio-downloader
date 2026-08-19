from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yt_audio_downloader.models import Track

_TS = re.compile(
    r"^\s*(?:[-*]|\d+[.)])?\s*"
    r"\[?\(?(?P<ts>(?:\d+:)?\d{1,2}:\d{2})\)?\]?"
    r"(?:\s*[-–—:]\s*|\s+)"
    r"(?P<title>.+?)\s*$"
)


def parse_timestamp(value: str) -> float:
    parts = [int(p) for p in value.strip().split(":")]
    if len(parts) == 2:
        hours, minutes, seconds = 0, parts[0], parts[1]
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"invalid timestamp: {value!r}")
    if seconds >= 60 or minutes >= 60:
        raise ValueError(f"invalid timestamp: {value!r}")
    return hours * 3600 + minutes * 60 + seconds


def format_timestamp(seconds: float) -> str:
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def parse_description_timestamps(description: str) -> list[tuple[float, str]]:
    pairs: list[tuple[float, str]] = []
    for raw_line in description.splitlines():
        match = _TS.match(raw_line)
        if not match:
            continue
        start = parse_timestamp(match.group("ts"))
        title = match.group("title").strip()
        pairs.append((start, title))
    if len(pairs) < 2:
        return []
    pairs.sort(key=lambda item: item[0])
    return pairs


def tracks_from_timed_titles(
    pairs: list[tuple[float, str]],
    duration_seconds: float,
) -> list[Track]:
    from yt_audio_downloader.models import Track

    tracks: list[Track] = []
    for index, (start, title) in enumerate(pairs, start=1):
        if index < len(pairs):
            end = pairs[index][0]
        else:
            end = duration_seconds
        tracks.append(
            Track(
                index=index,
                title=title,
                start=format_timestamp(start),
                end=format_timestamp(end),
            )
        )
    return tracks


def tracks_from_chapters(
    chapters: list[dict],
    duration_seconds: float,
) -> list[Track]:
    pairs = [
        (float(ch["start_time"]), str(ch.get("title") or f"Track {i}"))
        for i, ch in enumerate(chapters, start=1)
    ]
    return tracks_from_timed_titles(pairs, duration_seconds)
