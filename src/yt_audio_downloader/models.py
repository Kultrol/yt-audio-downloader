from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from yt_audio_downloader.timestamps import parse_timestamp


class SourceInfo(BaseModel):
    url: str
    video_id: str
    title: str
    duration: str
    thumbnail_url: str | None = None


class AlbumInfo(BaseModel):
    title: str
    artist: str
    album_artist: str | None = None
    date: str | None = None
    genre: str = "Live"


class Track(BaseModel):
    index: int = Field(ge=1)
    title: str
    start: str
    end: str | None = None
    artist: str | None = None

    @field_validator("start", "end")
    @classmethod
    def _valid_timestamp(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parse_timestamp(value)
        return value


class AlbumDocument(BaseModel):
    schema_version: int = 1
    source: SourceInfo
    album: AlbumInfo
    tracks: list[Track] = Field(default_factory=list)
