from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from yt_audio_downloader.albumjson import load_album, save_album
from yt_audio_downloader.config import album_project_dir
from yt_audio_downloader.media import split_and_encode
from yt_audio_downloader.models import AlbumDocument, SourceInfo, Track
from yt_audio_downloader.prepare import guess_album, select_tracks, source_duration
from yt_audio_downloader.youtube import (
    NotYouTubeURLError,
    download_audio,
    inspect,
    save_thumbnail,
)

app = typer.Typer(
    no_args_is_help=True,
    help="Turn YouTube concerts into tagged local albums.",
)
tracks_app = typer.Typer(no_args_is_help=True, help="List and edit tracks in album.json.")
app.add_typer(tracks_app, name="tracks")

console = Console()


def _ctx_path(ctx: typer.Context) -> Path | None:
    current: typer.Context | None = ctx
    while current is not None:
        obj = current.obj
        if isinstance(obj, dict) and "path" in obj:
            return obj["path"]
        current = current.parent
    return None


def resolve_album_dir(path: Path | None) -> Path:
    candidate = (path or Path.cwd()).expanduser().resolve()
    if candidate.is_file() and candidate.name == "album.json":
        album = candidate
        parent = candidate.parent
    else:
        parent = candidate
        album = parent / "album.json"
    if not album.is_file():
        raise typer.BadParameter(f"no album.json in {parent}")
    return parent


def _load(ctx: typer.Context) -> tuple[Path, AlbumDocument]:
    album_dir = resolve_album_dir(_ctx_path(ctx))
    return album_dir, load_album(album_dir / "album.json")


def _track_table(tracks: list[Track]) -> Table:
    table = Table(title="Tracks")
    table.add_column("#", justify="right")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Title")
    for track in tracks:
        table.add_row(
            str(track.index),
            track.start,
            track.end or "",
            track.title,
        )
    return table


@app.callback()
def main(
    ctx: typer.Context,
    path: Path | None = typer.Option(
        None,
        "--path",
        help="Album project directory (must contain album.json).",
    ),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["path"] = path


@app.command()
def doctor() -> None:
    """Check ffmpeg, ffprobe, and yt-dlp."""
    checks = [
        ("ffmpeg", shutil.which("ffmpeg") is not None),
        ("ffprobe", shutil.which("ffprobe") is not None),
        ("yt-dlp", importlib.util.find_spec("yt_dlp") is not None),
    ]
    table = Table(title="ytad doctor")
    table.add_column("Component")
    table.add_column("Status")
    missing = False
    for name, present in checks:
        if not present:
            missing = True
        table.add_row(name, "ok" if present else "MISSING")
    console.print(table)
    if missing:
        raise typer.Exit(1)


@app.command()
def init(url: str) -> None:
    """Fetch YouTube metadata and create an album project folder."""
    try:
        info = inspect(url)
    except NotYouTubeURLError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

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
    except NotImplementedError:
        pass

    console.print(f"Created album project at [bold]{dest}[/bold]")
    console.print(f"Tracks: {len(tracks)}")
    if not tracks:
        console.print(
            "[yellow]No chapters or description timestamps found. "
            "Edit album.json or run `ytad tracks set` to add them.[/yellow]"
        )
    console.print(f"Next: cd {dest!s} && ytad show")


@app.command()
def show(ctx: typer.Context) -> None:
    """Pretty-print album.json."""
    album_dir, doc = _load(ctx)
    header = (
        f"[bold]{doc.album.artist}[/bold] — {doc.album.title}\n"
        f"Date: {doc.album.date or '—'}    Genre: {doc.album.genre}\n"
        f"Source: {doc.source.url}\n"
        f"Path: {album_dir}"
    )
    console.print(Panel(header, title="Album"))
    console.print(_track_table(doc.tracks))


@app.command("set")
def set_album(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title"),
    artist: str | None = typer.Option(None, "--artist"),
    album_artist: str | None = typer.Option(None, "--album-artist"),
    date: str | None = typer.Option(None, "--date"),
    genre: str | None = typer.Option(None, "--genre"),
) -> None:
    """Patch album fields in album.json."""
    album_dir, doc = _load(ctx)
    updates = {
        "title": title,
        "artist": artist,
        "album_artist": album_artist,
        "date": date,
        "genre": genre,
    }
    data = doc.album.model_dump()
    changed = False
    for key, value in updates.items():
        if value is not None:
            data[key] = value
            changed = True
    if not changed:
        console.print("[yellow]No fields provided. Nothing changed.[/yellow]")
        return
    doc.album = type(doc.album).model_validate(data)
    save_album(album_dir / "album.json", doc)
    console.print(f"Updated {album_dir / 'album.json'}")


@app.command()
def download(ctx: typer.Context) -> None:
    """Download audio for the current album (not implemented yet)."""
    album_dir, doc = _load(ctx)
    try:
        download_audio(doc.source.url, album_dir / "source")
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


@app.command()
def build(ctx: typer.Context) -> None:
    """Split, encode, and export tagged tracks (not implemented yet)."""
    album_dir, doc = _load(ctx)
    source_dir = album_dir / "source"
    source_audio = next(source_dir.glob("*"), source_dir / "audio")
    try:
        split_and_encode(source_audio, doc, album_dir / "export")
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


@tracks_app.command("list")
def tracks_list(ctx: typer.Context) -> None:
    """List tracks from album.json."""
    _, doc = _load(ctx)
    console.print(_track_table(doc.tracks))


@tracks_app.command("set")
def tracks_set(
    ctx: typer.Context,
    index: int = typer.Argument(..., min=1),
    title: str | None = typer.Option(None, "--title"),
    start: str | None = typer.Option(None, "--start"),
    end: str | None = typer.Option(None, "--end"),
) -> None:
    """Edit one track in album.json (1-based index)."""
    album_dir, doc = _load(ctx)
    track = next((item for item in doc.tracks if item.index == index), None)
    if track is None:
        console.print(f"[red]No track with index {index}[/red]")
        raise typer.Exit(1)
    data = track.model_dump()
    if title is not None:
        data["title"] = title
    if start is not None:
        data["start"] = start
    if end is not None:
        data["end"] = end
    updated = Track.model_validate(data)
    doc.tracks = [updated if item.index == index else item for item in doc.tracks]
    save_album(album_dir / "album.json", doc)
    console.print(f"Updated track {index}")
