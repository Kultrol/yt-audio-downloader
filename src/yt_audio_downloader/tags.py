from pathlib import Path

from mutagen.mp4 import MP4, MP4Cover

from yt_audio_downloader.models import AlbumDocument, Track


def write_tags(path: Path, doc: AlbumDocument, track: Track, cover: Path | None) -> None:
    audio = MP4(path)
    artist = track.artist or doc.album.artist
    album_artist = doc.album.album_artist or doc.album.artist
    audio["\xa9nam"] = [track.title]
    audio["\xa9ART"] = [artist]
    audio["\xa9alb"] = [doc.album.title]
    audio["aART"] = [album_artist]
    audio["trkn"] = [(track.index, len(doc.tracks))]
    if doc.album.date:
        audio["\xa9day"] = [doc.album.date]
    if doc.album.genre:
        audio["\xa9gen"] = [doc.album.genre]
    if cover is not None and cover.is_file():
        data = cover.read_bytes()
        if data.startswith(b"\x89PNG"):
            fmt = MP4Cover.FORMAT_PNG
        elif data.startswith(b"\xff\xd8"):
            fmt = MP4Cover.FORMAT_JPEG
        else:
            fmt = None
        if fmt is not None:
            audio["covr"] = [MP4Cover(data, imageformat=fmt)]
    audio.save()
