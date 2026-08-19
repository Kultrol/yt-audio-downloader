from __future__ import annotations

import importlib.util
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from yt_audio_downloader.albumjson import load_album, save_album
from yt_audio_downloader.media import find_source_audio, split_and_encode
from yt_audio_downloader.models import AlbumDocument, Track
from yt_audio_downloader.project import create_album_project
from yt_audio_downloader.validate import TracklistError
from yt_audio_downloader.youtube import (
    NotYouTubeURLError,
    download_audio,
    inspect,
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
        parent = candidate.parent
        album = candidate
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
        table.add_row(str(track.index), track.start, track.end or "", track.title)
    return table


def _print_album(album_dir: Path, doc: AlbumDocument) -> None:
    header = (
        f"[bold]{doc.album.artist}[/bold] — {doc.album.title}\n"
        f"Date: {doc.album.date or '—'}    Genre: {doc.album.genre}\n"
        f"Source: {doc.source.url}\n"
        f"Path: {album_dir}"
    )
    console.print(Panel(header, title="Album"))
    console.print(_track_table(doc.tracks))


def _inspect_url(url: str):
    try:
        return inspect(url)
    except NotYouTubeURLError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


def _run_download(album_dir: Path, doc: AlbumDocument) -> Path:
    console.print("Downloading audio…")
    path = download_audio(doc.source.url, album_dir / "source")
    console.print(f"Downloaded [bold]{path}[/bold]")
    return path


def _run_build(album_dir: Path, doc: AlbumDocument) -> list[Path]:
    try:
        source = find_source_audio(album_dir / "source")
        paths = split_and_encode(source, doc, album_dir / "export")
    except (TracklistError, FileNotFoundError, RuntimeError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    export = album_dir / "export"
    console.print(f"Wrote {len(paths)} tracks to [bold]{export}[/bold]")
    return paths


def _edit_album_json(path: Path) -> None:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        subprocess.run([*shlex.split(editor), str(path)], check=False)
        return
    if sys.platform == "darwin":
        subprocess.run(["open", "-t", str(path)], check=False)
    else:
        console.print(f"Edit [bold]{path}[/bold] in your editor.")
    Confirm.ask("Press Enter when you have saved album.json", default=True)


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
def add(
    url: str,
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip prompts; download and build after creating album.json.",
    ),
) -> None:
    """Create an album, let you edit metadata, then download and build."""
    info = _inspect_url(url)
    dest = create_album_project(info)
    doc = load_album(dest / "album.json")
    console.print(f"Created album project at [bold]{dest}[/bold]")
    _print_album(dest, doc)
    if not doc.tracks:
        console.print(
            "[yellow]No chapters or description timestamps found. "
            "Add tracks in album.json before building.[/yellow]"
        )

    if not yes:
        if Confirm.ask("Edit album.json before downloading?", default=True):
            _edit_album_json(dest / "album.json")
            doc = load_album(dest / "album.json")
            _print_album(dest, doc)
        if not Confirm.ask("Download audio now?", default=True):
            console.print("Stopped before download. Later: `cd` here and run `ytad download`.")
            return

    doc = load_album(dest / "album.json")
    _run_download(dest, doc)

    if not yes:
        if not Confirm.ask("Build tagged M4A album now?", default=True):
            console.print("Stopped before build. Later: run `ytad build`.")
            return

    doc = load_album(dest / "album.json")
    _run_build(dest, doc)


@app.command()
def init(url: str) -> None:
    """Fetch YouTube metadata and create an album project folder."""
    info = _inspect_url(url)
    dest = create_album_project(info)
    doc = load_album(dest / "album.json")
    console.print(f"Created album project at [bold]{dest}[/bold]")
    console.print(f"Tracks: {len(doc.tracks)}")
    if not doc.tracks:
        console.print(
            "[yellow]No chapters or description timestamps found. "
            "Edit album.json or run `ytad tracks set` to add them.[/yellow]"
        )
    console.print(f"Next: cd {dest} && ytad show")
    console.print("Or start over with `ytad add URL` to be walked through edit, download, and build.")


@app.command()
def show(ctx: typer.Context) -> None:
    """Pretty-print album.json."""
    album_dir, doc = _load(ctx)
    _print_album(album_dir, doc)


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
    """Download audio for the current album into source/."""
    album_dir, doc = _load(ctx)
    _run_download(album_dir, doc)


@app.command()
def build(ctx: typer.Context) -> None:
    """Split, encode AAC/M4A, tag, and write export/."""
    album_dir, doc = _load(ctx)
    _run_build(album_dir, doc)


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
