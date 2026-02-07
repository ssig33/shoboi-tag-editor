"""Module for reading and writing music file metadata"""

from dataclasses import dataclass, field
from pathlib import Path

from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3


@dataclass
class TrackMetadata:
    """Dataclass for holding track metadata"""

    file_path: Path
    title: str = ""
    artist: str = ""
    album: str = ""
    track_number: str = ""
    year: str = ""
    genre: str = ""
    modified: bool = field(default=False, compare=False)

    def copy_from(self, other: "TrackMetadata") -> None:
        """Copy metadata from another TrackMetadata"""
        self.title = other.title
        self.artist = other.artist
        self.album = other.album
        self.track_number = other.track_number
        self.year = other.year
        self.genre = other.genre


SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".flac"}


def is_supported_file(path: Path) -> bool:
    """Check if the file format is supported"""
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def _get_first_value(tags: dict, key: str) -> str:
    """Get the first value from tags"""
    values = tags.get(key, [])
    if values:
        return str(values[0])
    return ""


def read_metadata(file_path: Path) -> TrackMetadata:
    """Read metadata from a file"""
    suffix = file_path.suffix.lower()
    metadata = TrackMetadata(file_path=file_path)

    if suffix == ".mp3":
        try:
            audio = MP3(file_path, ID3=EasyID3)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags(ID3=EasyID3)
            return metadata

        metadata.title = _get_first_value(audio, "title")
        metadata.artist = _get_first_value(audio, "artist")
        metadata.album = _get_first_value(audio, "album")
        metadata.track_number = _get_first_value(audio, "tracknumber")
        metadata.year = _get_first_value(audio, "date")
        metadata.genre = _get_first_value(audio, "genre")

    elif suffix == ".m4a":
        audio = EasyMP4(file_path)
        metadata.title = _get_first_value(audio, "title")
        metadata.artist = _get_first_value(audio, "artist")
        metadata.album = _get_first_value(audio, "album")
        metadata.track_number = _get_first_value(audio, "tracknumber")
        metadata.year = _get_first_value(audio, "date")
        metadata.genre = _get_first_value(audio, "genre")

    elif suffix == ".flac":
        audio = FLAC(file_path)
        metadata.title = _get_first_value(audio, "title")
        metadata.artist = _get_first_value(audio, "artist")
        metadata.album = _get_first_value(audio, "album")
        metadata.track_number = _get_first_value(audio, "tracknumber")
        metadata.year = _get_first_value(audio, "date")
        metadata.genre = _get_first_value(audio, "genre")

    return metadata


def write_metadata(metadata: TrackMetadata) -> None:
    """Write metadata to a file"""
    file_path = metadata.file_path
    suffix = file_path.suffix.lower()

    if suffix == ".mp3":
        try:
            audio = MP3(file_path, ID3=EasyID3)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags(ID3=EasyID3)
            audio = MP3(file_path, ID3=EasyID3)

        audio["title"] = metadata.title
        audio["artist"] = metadata.artist
        audio["album"] = metadata.album
        audio["tracknumber"] = metadata.track_number
        audio["date"] = metadata.year
        audio["genre"] = metadata.genre
        audio.save()

    elif suffix == ".m4a":
        audio = EasyMP4(file_path)
        audio["title"] = metadata.title
        audio["artist"] = metadata.artist
        audio["album"] = metadata.album
        audio["tracknumber"] = metadata.track_number
        audio["date"] = metadata.year
        audio["genre"] = metadata.genre
        audio.save()

    elif suffix == ".flac":
        audio = FLAC(file_path)
        audio["title"] = metadata.title
        audio["artist"] = metadata.artist
        audio["album"] = metadata.album
        audio["tracknumber"] = metadata.track_number
        audio["date"] = metadata.year
        audio["genre"] = metadata.genre
        audio.save()

    metadata.modified = False
