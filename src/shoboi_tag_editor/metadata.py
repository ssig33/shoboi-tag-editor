"""Module for reading and writing music file metadata"""

from dataclasses import dataclass, field
from pathlib import Path

from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover
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
    cover_image: bytes | None = field(default=None, compare=False)
    cover_mime: str = field(default="image/jpeg", compare=False)
    modified: bool = field(default=False, compare=False)

    def copy_from(self, other: "TrackMetadata") -> None:
        """Copy metadata from another TrackMetadata"""
        self.title = other.title
        self.artist = other.artist
        self.album = other.album
        self.track_number = other.track_number
        self.year = other.year
        self.genre = other.genre
        self.cover_image = other.cover_image
        self.cover_mime = other.cover_mime


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

        # Read cover image from ID3 tags
        try:
            id3 = ID3(file_path)
            for key in id3.keys():
                if key.startswith("APIC"):
                    apic = id3[key]
                    metadata.cover_image = apic.data
                    metadata.cover_mime = apic.mime
                    break
        except ID3NoHeaderError:
            pass

    elif suffix == ".m4a":
        audio = EasyMP4(file_path)
        metadata.title = _get_first_value(audio, "title")
        metadata.artist = _get_first_value(audio, "artist")
        metadata.album = _get_first_value(audio, "album")
        metadata.track_number = _get_first_value(audio, "tracknumber")
        metadata.year = _get_first_value(audio, "date")
        metadata.genre = _get_first_value(audio, "genre")

        # Read cover image from MP4 tags
        mp4 = MP4(file_path)
        covers = mp4.tags.get("covr", []) if mp4.tags else []
        if covers:
            cover = covers[0]
            metadata.cover_image = bytes(cover)
            if cover.imageformat == MP4Cover.FORMAT_PNG:
                metadata.cover_mime = "image/png"
            else:
                metadata.cover_mime = "image/jpeg"

    elif suffix == ".flac":
        audio = FLAC(file_path)
        metadata.title = _get_first_value(audio, "title")
        metadata.artist = _get_first_value(audio, "artist")
        metadata.album = _get_first_value(audio, "album")
        metadata.track_number = _get_first_value(audio, "tracknumber")
        metadata.year = _get_first_value(audio, "date")
        metadata.genre = _get_first_value(audio, "genre")

        # Read cover image from FLAC pictures
        if audio.pictures:
            pic = audio.pictures[0]
            metadata.cover_image = pic.data
            metadata.cover_mime = pic.mime

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

        # Write cover image to ID3 tags
        try:
            id3 = ID3(file_path)
        except ID3NoHeaderError:
            id3 = ID3()
            id3.save(file_path)
            id3 = ID3(file_path)

        # Remove existing APIC frames
        for key in list(id3.keys()):
            if key.startswith("APIC"):
                del id3[key]

        if metadata.cover_image:
            id3.add(
                APIC(
                    encoding=3,
                    mime=metadata.cover_mime,
                    type=3,  # Front cover
                    desc="Cover",
                    data=metadata.cover_image,
                )
            )
        id3.save(file_path)

    elif suffix == ".m4a":
        audio = EasyMP4(file_path)
        audio["title"] = metadata.title
        audio["artist"] = metadata.artist
        audio["album"] = metadata.album
        audio["tracknumber"] = metadata.track_number
        audio["date"] = metadata.year
        audio["genre"] = metadata.genre
        audio.save()

        # Write cover image to MP4 tags
        mp4 = MP4(file_path)
        if metadata.cover_image:
            if metadata.cover_mime == "image/png":
                fmt = MP4Cover.FORMAT_PNG
            else:
                fmt = MP4Cover.FORMAT_JPEG
            mp4["covr"] = [MP4Cover(metadata.cover_image, imageformat=fmt)]
        else:
            if "covr" in mp4:
                del mp4["covr"]
        mp4.save()

    elif suffix == ".flac":
        audio = FLAC(file_path)
        audio["title"] = metadata.title
        audio["artist"] = metadata.artist
        audio["album"] = metadata.album
        audio["tracknumber"] = metadata.track_number
        audio["date"] = metadata.year
        audio["genre"] = metadata.genre

        # Clear existing pictures and add new one
        audio.clear_pictures()
        if metadata.cover_image:
            pic = Picture()
            pic.type = 3  # Front cover
            pic.mime = metadata.cover_mime
            pic.desc = "Cover"
            pic.data = metadata.cover_image
            audio.add_picture(pic)
        audio.save()

    metadata.modified = False
