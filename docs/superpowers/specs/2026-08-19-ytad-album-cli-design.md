# ytad album CLI design

Date: 2026-08-19

## Goal

A uv-managed Python CLI (`ytad`) that turns one long YouTube concert/set video into an editable album project, then later a tagged AAC/M4A album suitable for Apple Music and Spotify Local Files.

This document records the product decisions and the scaffolding that is implemented now.

## Product decisions

| Decision | Choice | Why |
|---|---|---|
| Primary input | One long concert/set URL | Typical use: live performances not on streaming services |
| Output | Audio album only | Daily listening in Apple Music / Spotify; no kept video |
| Corrections | `album.json` is source of truth; CLI can edit it | Easy to fix titles and timestamps in an editor |
| Persistence | Per-album folder + JSON | Matches the edit-a-file workflow. SQLite is worse for hand-editing; a derived index can wait |
| Sites | YouTube only | Project name and v1 scope. yt-dlp is the YouTube interface |
| Tracklist | Chapters, else description timestamps, else empty | "Take care of the rest" without guessing setlists |
| Export codec (later) | AAC/M4A | Works for both Apple Music and Spotify Local Files. YouTube audio is already lossy, so FLAC would be fake lossless |
| HTTP / gRPC | No httpx, no gRPC | yt-dlp already talks to YouTube. Revisit httpx only if we add MusicBrainz or Cover Art Archive |

## On-disk layout

```text
~/Music/ytad/                          # YTAD_LIBRARY overrides
  Artist Name/
    2024 - Live at Venue/
      album.json
      cover.jpg
      source/
      export/
```

`export/` is the import folder. `source/` holds the unsplit download so Music/Spotify do not pick it up.

If the target directory already exists, `init` appends `-{video_id}`.

## album.json

Timestamps are `M:SS` or `H:MM:SS` strings, not raw seconds.

```json
{
  "schema_version": 1,
  "source": {
    "url": "https://www.youtube.com/watch?v=VIDEOID",
    "video_id": "VIDEOID",
    "title": "Artist – Live at Venue (2024)",
    "duration": "2:01:03",
    "thumbnail_url": null
  },
  "album": {
    "title": "Live at Venue",
    "artist": "Artist Name",
    "album_artist": "Artist Name",
    "date": "2024",
    "genre": "Live"
  },
  "tracks": [
    { "index": 1, "title": "Intro", "start": "0:00", "end": "1:23" }
  ]
}
```

Pydantic (`AlbumDocument`) validates the file. Invalid timestamps raise a validation error. Track indexes are 1-based.

## CLI

| Command | Behavior now |
|---|---|
| `ytad init URL` | yt-dlp inspect (download=False), write project + `album.json` |
| `ytad show` | Rich panel + track table |
| `ytad set` | Patch album fields |
| `ytad tracks list` | Track table |
| `ytad tracks set N` | Edit one track |
| `ytad download` | Calls `download_audio`; currently `NotImplementedError` |
| `ytad build` | Calls `split_and_encode`; currently `NotImplementedError` |
| `ytad doctor` | `ffmpeg`, `ffprobe`, import `yt_dlp` |

`--path DIR` selects an existing album project. Otherwise cwd must contain `album.json`.

## Modules

| Module | Responsibility |
|---|---|
| `models` | Pydantic document |
| `timestamps` | Parse/format; description regex; chapters → tracks |
| `albumjson` | Load/save |
| `config` | Library root, sanitizing, folder names |
| `youtube` | URL check, `VideoInfo`, `inspect`, stubs for download/thumbnail |
| `prepare` | Chapter-vs-description selection; artist/title/year guess |
| `media` | ffmpeg split/encode stub |
| `tags` | mutagen tagging stub |
| `cli` | Typer app |

## Tracklist rules

1. If yt-dlp returns chapters, use them.
2. Else parse description lines that start with a timestamp (`0:00 Title`, `1:12:05 Encore`, optional bullets/`-`). Require at least two hits so prose like "see you at 8:00" is ignored.
3. Else empty tracklist; `init` warns. The user fills timestamps by editing JSON or `ytad tracks set`.

Last track `end` is the video duration. Other ends are the next track's start.

## Metadata guess

If the YouTube title contains ` - `, the left side is artist and the right side is album title. A 19xx/20xx year in the title becomes `album.date`. Parenthetical years are stripped from the album title. Uploader is the artist fallback. Users are expected to correct this.

## Testing

- pytest, no live YouTube in the default suite
- `inspect` / `_extract_info` monkeypatched in CLI and unit tests
- Timestamp fixtures under `tests/fixtures/descriptions/`

## Later work

- `download_audio` via yt-dlp into `source/`
- ffmpeg split + AAC encode into `export/`
- mutagen tags + embedded cover
- `save_thumbnail` implementation
- Overlap/gap validation at `build` time
- Optional httpx only if an external metadata API is added
