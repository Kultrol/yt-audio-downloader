# ytad

Turn a YouTube concert or live-set URL into a tagged M4A album you can add to Apple Music or Spotify Local Files.

`ytad` fetches metadata with [yt-dlp](https://github.com/yt-dlp/yt-dlp), guesses artist/title/year, and builds a tracklist from video chapters or timestamps in the description. If neither exists, it treats the whole video as one track. You fix mistakes in `album.json` (or via CLI commands). Then it downloads audio, splits with ffmpeg, and writes tagged AAC/M4A files.

Use this only on videos you have the right to download. You are responsible for complying with YouTube's terms and copyright law.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- `ffmpeg` and `ffprobe` on `PATH`
- Node.js or Deno on `PATH` (YouTube challenge solving; `ytad doctor` checks this)

## Install

```bash
uv sync
uv run ytad --help
uv run ytad doctor
```

## Usual workflow

```bash
uv run ytad add 'https://www.youtube.com/watch?v=VIDEO_ID'
```

That command:

1. Creates an album project and `album.json`
2. Shows the guessed album and tracks
3. Asks if you want to edit `album.json` (titles, timestamps, tags)
4. Downloads audio
5. Splits, encodes AAC/M4A at 256 kbps, tags, and writes `export/`

`--yes` / `-y` skips the prompts and runs download + build after init.

Individual commands stay available if you want to run steps yourself.

## Manual commands

```bash
uv run ytad init 'https://www.youtube.com/watch?v=VIDEO_ID'
cd ~/Music/ytad/Artist/'2024 - Live at Venue'
uv run ytad show
uv run ytad set --title 'Live at Venue' --artist 'Artist'
uv run ytad tracks set 3 --title 'Corrected Title' --start '12:04'
# or edit album.json in any editor — it is the source of truth
uv run ytad download
uv run ytad build
```

Library root defaults to `~/Music/ytad`. Override with `YTAD_LIBRARY`.

Existing-album commands (`show`, `set`, `tracks`, `download`, `build`) look for `album.json` in the current directory, or take `--path DIR`.

## Album project layout

```text
~/Music/ytad/
  Artist Name/
    2024 - Live at Venue/
      album.json          # source of truth (human-edited)
      cover.jpg           # YouTube thumbnail when available
      source/             # unsplit download
      export/             # tagged M4A tracks — add this folder to Apple Music / Spotify
        01 - Intro.m4a
        02 - Opening Song.m4a
        cover.jpg
```

Import `export/`, not `source/`.

## Commands

| Command | Purpose |
|---|---|
| `ytad add URL` | Guided path: create, edit, download, build |
| `ytad init URL` | Inspect YouTube; write the project folder + `album.json` |
| `ytad show` | Print album and tracks |
| `ytad set` | Patch album title/artist/date/genre |
| `ytad tracks list` | Track table |
| `ytad tracks add` | Append a track |
| `ytad tracks set N` | Edit one track |
| `ytad download` | Download best audio into `source/` |
| `ytad build` | Split, encode, tag, write `export/` |
| `ytad doctor` | Check `ffmpeg`, `ffprobe`, `yt-dlp`, Node/Deno |

## Planned

These are not built yet:

- **URL queue** — pass several YouTube links in one session and process them one after another
- **Album from multiple URLs** — combine separate videos into a single album (for example five song URLs that become tracks 1–5 under one `album.json`)

## Tests

```bash
uv run pytest -v
```

Default tests do not hit YouTube. ffmpeg is used for split/tag tests when it is installed.

## Out of scope

- Keeping or splitting video
- Sites other than YouTube
- SQLite / a library database
- MusicBrainz, setlist.fm, or other metadata APIs
