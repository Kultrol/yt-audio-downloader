from __future__ import annotations

from yt_audio_downloader.models import AlbumDocument, Track
from yt_audio_downloader.timestamps import parse_timestamp


class TracklistError(ValueError):
    pass


def track_span(track: Track, duration_seconds: float | None) -> tuple[float, float]:
    start = parse_timestamp(track.start)
    if track.end:
        end = parse_timestamp(track.end)
    elif duration_seconds is not None:
        end = duration_seconds
    else:
        raise TracklistError(f"track {track.index} is missing end time")
    return start, end


def validate_tracks(doc: AlbumDocument) -> None:
    if not doc.tracks:
        raise TracklistError("album.json has no tracks; add timestamps before building")

    duration = parse_timestamp(doc.source.duration) if doc.source.duration else None
    previous_end = 0.0
    previous_index: int | None = None

    for track in sorted(doc.tracks, key=lambda item: item.index):
        start, end = track_span(track, duration)
        if end <= start:
            raise TracklistError(
                f"track {track.index} end ({track.end}) is not after start ({track.start})"
            )
        if previous_index is not None and start < previous_end:
            raise TracklistError(
                f"track {track.index} overlaps track {previous_index}"
            )
        if duration is not None and end > duration + 0.5:
            raise TracklistError(
                f"track {track.index} end ({track.end}) is past source duration "
                f"({doc.source.duration})"
            )
        previous_end = end
        previous_index = track.index
