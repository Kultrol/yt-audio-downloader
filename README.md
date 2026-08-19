# ytad

Turn a YouTube concert or live-set URL into an editable album project, then (later) a tagged M4A album you can add to Apple Music or Spotify Local Files.

`ytad` is a local CLI. You paste a YouTube URL; it fetches metadata with [yt-dlp](https://github.com/yt-dlp/yt-dlp), guesses artist/title/year, and builds a tracklist from video chapters or timestamps in the description. You fix mistakes in `album.json` (or via CLI commands). Audio download, split, and tagging are stubbed in this pass.

Use this only on videos you have the right to download. You are responsible for complying with YouTube's terms and copyright law.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- `ffmpeg` and `ffprobe` on `PATH` (needed for `ytad doctor` and, later, `build`)

## Install

```bash
uv sync
uv run ytad --help
uv run ytad doctor
```

## Workflow

```bash
uv run ytad init 'https://www.youtube.com/watch?v=VIDEO_ID'
cd ~/Music/ytad/Artist/'2024 - Live at Venue'
uv run ytad show
uv run ytad set --title 'Live at Venue' --artist 'Artist'
uv run ytad tracks set 3 --title 'Corrected Title' --start '12:04'
# edit album.json in any editor — it is the source of truth
uv run ytad download   # not implemented yet
uv run ytad build      # not implemented yet
```

Library root defaults to `~/Music/ytad`. Override with `YTAD_LIBRARY`.

Existing-album commands (`show`, `set`, `tracks`, `download`, `build`) look for `album.json` in the current directory, or take `--path DIR`.

## Album project layout

```text
~/Music/ytad/
  Artist Name/
    2024 - Live at Venue/
      album.json          # source of truth (human-edited)
      cover.jpg           # best-effort; may be missing for now
      source/             # unsplit download (later)
      export/             # tagged M4A tracks for Apple Music / Spotify (later)
```

Import `export/` later, not `source/`.

## Commands

| Command | Purpose |
|---|---|
| `ytad init URL` | Inspect YouTube (no audio download); write the project folder + `album.json` |
| `ytad show` | Print album and tracks |
| `ytad set` | Patch album title/artist/date/genre |
| `ytad tracks list` | Track table |
| `ytad tracks set N` | Edit one track |
| `ytad download` | Stub |
| `ytad build` | Stub |
| `ytad doctor` | Check `ffmpeg`, `ffprobe`, `yt-dlp` |

## Tests

```bash
uv run pytest -v
```

Default tests do not hit the network or YouTube.

## Out of scope (this pass)

- Keeping or splitting video
- Sites other than YouTube
- SQLite / a library database
- MusicBrainz, setlist.fm, or other metadata APIs
- Actual audio download, ffmpeg split, and mutagen tagging
