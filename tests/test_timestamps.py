from pathlib import Path

from yt_audio_downloader.timestamps import (
    format_timestamp,
    parse_description_timestamps,
    parse_timestamp,
    tracks_from_chapters,
    tracks_from_timed_titles,
)

FIXTURE = Path(__file__).parent / "fixtures" / "descriptions" / "concert.txt"


def test_parse_timestamp_mmss_and_hhmmss():
    assert parse_timestamp("0:00") == 0
    assert parse_timestamp("4:12") == 252
    assert parse_timestamp("1:02:03") == 3723
    assert parse_timestamp("01:02:03") == 3723


def test_format_timestamp_omits_hours_when_zero():
    assert format_timestamp(0) == "0:00"
    assert format_timestamp(252) == "4:12"
    assert format_timestamp(3723) == "1:02:03"


def test_parse_description_timestamps_from_fixture():
    text = FIXTURE.read_text(encoding="utf-8")
    pairs = parse_description_timestamps(text)
    assert [(t, title) for t, title in pairs] == [
        (0, "Intro"),
        (83, "Opening Song"),
        (400, "Deep Cut (Live)"),
        (4325, "Encore"),
    ]


def test_parse_description_ignores_prose_without_leading_timestamps():
    assert parse_description_timestamps("See you at 8:00 tonight folks") == []


def test_tracks_from_timed_titles_fills_end_from_next_start():
    tracks = tracks_from_timed_titles(
        [(0, "Intro"), (83, "Opening Song")],
        duration_seconds=200,
    )
    assert [(t.index, t.title, t.start, t.end) for t in tracks] == [
        (1, "Intro", "0:00", "1:23"),
        (2, "Opening Song", "1:23", "3:20"),
    ]


def test_tracks_from_chapters_uses_chapter_titles_and_starts():
    chapters = [
        {"start_time": 0, "title": "Intro"},
        {"start_time": 83, "title": "Opening Song"},
    ]
    tracks = tracks_from_chapters(chapters, duration_seconds=200)
    assert tracks[0].title == "Intro"
    assert tracks[1].start == "1:23"
    assert tracks[-1].end == "3:20"
