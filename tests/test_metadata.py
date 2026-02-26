"""Tests for metadata module"""

import struct
from pathlib import Path

import pytest
from mutagen.mp4 import MP4

from shoboi_tag_editor.metadata import (
    SUPPORTED_EXTENSIONS,
    TrackMetadata,
    is_supported_file,
    read_metadata,
    write_metadata,
)


class TestTrackMetadata:
    def test_default_values(self):
        path = Path("/test/file.mp3")
        meta = TrackMetadata(file_path=path)

        assert meta.file_path == path
        assert meta.title == ""
        assert meta.artist == ""
        assert meta.album_artist == ""
        assert meta.album == ""
        assert meta.track_number == ""
        assert meta.year == ""
        assert meta.genre == ""
        assert meta.modified is False

    def test_with_values(self):
        path = Path("/test/file.mp3")
        meta = TrackMetadata(
            file_path=path,
            title="Test Title",
            artist="Test Artist",
            album_artist="Test Album Artist",
            album="Test Album",
            track_number="1",
            year="2024",
            genre="Rock",
        )

        assert meta.title == "Test Title"
        assert meta.artist == "Test Artist"
        assert meta.album_artist == "Test Album Artist"
        assert meta.album == "Test Album"
        assert meta.track_number == "1"
        assert meta.year == "2024"
        assert meta.genre == "Rock"

    def test_copy_from(self):
        path1 = Path("/test/file1.mp3")
        path2 = Path("/test/file2.mp3")

        source = TrackMetadata(
            file_path=path1,
            title="Source Title",
            artist="Source Artist",
            album_artist="Source Album Artist",
            album="Source Album",
            track_number="5",
            year="2023",
            genre="Jazz",
        )

        target = TrackMetadata(file_path=path2)
        target.copy_from(source)

        assert target.file_path == path2
        assert target.title == "Source Title"
        assert target.artist == "Source Artist"
        assert target.album_artist == "Source Album Artist"
        assert target.album == "Source Album"
        assert target.track_number == "5"
        assert target.year == "2023"
        assert target.genre == "Jazz"

    def test_modified_not_compared(self):
        path = Path("/test/file.mp3")
        meta1 = TrackMetadata(file_path=path, title="Test", modified=False)
        meta2 = TrackMetadata(file_path=path, title="Test", modified=True)

        assert meta1 == meta2


class TestIsSupportedFile:
    @pytest.mark.parametrize("ext", SUPPORTED_EXTENSIONS)
    def test_supported_extensions(self, ext):
        path = Path(f"/test/file{ext}")
        assert is_supported_file(path) is True

    @pytest.mark.parametrize("ext", [".MP3", ".M4A", ".FLAC"])
    def test_supported_extensions_uppercase(self, ext):
        path = Path(f"/test/file{ext}")
        assert is_supported_file(path) is True

    @pytest.mark.parametrize("ext", [".wav", ".ogg", ".aac", ".txt", ".pdf"])
    def test_unsupported_extensions(self, ext):
        path = Path(f"/test/file{ext}")
        assert is_supported_file(path) is False


def _create_minimal_mp3(path: Path) -> None:
    """Create a minimal valid MP3 file with multiple MPEG frames."""
    # MPEG1 Layer3 128kbps 44100Hz stereo frame header: FF FB 90 00
    header = b"\xff\xfb\x90\x00"
    # Frame size = int(144 * 128000 / 44100) = 417 bytes
    frame = header + b"\x00" * (417 - 4)
    # Multiple frames needed for mutagen sync detection
    path.write_bytes(frame * 5)


def _create_minimal_m4a(path: Path) -> None:
    """Create a minimal valid M4A file."""
    ftyp = b"ftyp" + b"M4A " + b"\x00\x00\x00\x00" + b"M4A " + b"mp42" + b"isom"
    ftyp_box = struct.pack(">I", len(ftyp) + 4) + ftyp

    mvhd = b"mvhd" + b"\x00" * 104
    mvhd_box = struct.pack(">I", len(mvhd) + 4) + mvhd

    moov = b"moov"
    moov_data = mvhd_box
    moov_box = struct.pack(">I", len(moov) + len(moov_data) + 4) + moov + moov_data

    path.write_bytes(ftyp_box + moov_box)


def _create_minimal_flac(path: Path) -> None:
    """Create a minimal valid FLAC file with proper STREAMINFO."""
    data = bytearray()
    data.extend(b"fLaC")
    # STREAMINFO: last-metadata-block (0x80) | type 0x00 = 0x80, length = 34
    data.append(0x80)
    data.extend(struct.pack(">I", 34)[1:])  # 3-byte big-endian length
    # STREAMINFO data (34 bytes total)
    data.extend(struct.pack(">HH", 4096, 4096))  # min/max block size
    data.extend(b"\x00" * 3)  # min frame size
    data.extend(b"\x00" * 3)  # max frame size
    # 8 bytes: sample_rate(20) | channels-1(3) | bps-1(5) | total_samples(36)
    sr = 44100
    val = (sr << 44) | (1 << 41) | (15 << 36) | 0  # stereo, 16-bit, 0 samples
    data.extend(struct.pack(">Q", val))
    data.extend(b"\x00" * 16)  # MD5
    path.write_bytes(bytes(data))


@pytest.fixture
def tmp_mp3(tmp_path):
    p = tmp_path / "test.mp3"
    _create_minimal_mp3(p)
    return p


@pytest.fixture
def tmp_m4a(tmp_path):
    p = tmp_path / "test.m4a"
    _create_minimal_m4a(p)
    try:
        mp4 = MP4(p)
        mp4.save()
    except Exception:
        pytest.skip("Cannot create valid M4A test file")
    return p


@pytest.fixture
def tmp_flac(tmp_path):
    p = tmp_path / "test.flac"
    _create_minimal_flac(p)
    return p


class TestWriteReadCycleMP3:
    """Test write/read cycle for MP3 files."""

    def test_write_and_read_metadata(self, tmp_mp3):
        meta = TrackMetadata(
            file_path=tmp_mp3,
            title="Test",
            artist="Artist",
            album_artist="Album Artist",
            album="Album",
            track_number="3",
            year="2025",
            genre="Pop",
        )
        write_metadata(meta)
        result = read_metadata(tmp_mp3)
        assert result.title == "Test"
        assert result.artist == "Artist"
        assert result.album_artist == "Album Artist"
        assert result.album == "Album"
        assert result.track_number == "3"
        assert result.year == "2025"
        assert result.genre == "Pop"

    def test_empty_fields_are_cleared(self, tmp_mp3):
        # First write some data
        meta = TrackMetadata(
            file_path=tmp_mp3,
            title="Title",
            artist="Artist",
            album_artist="Album Artist",
            album="Album",
            track_number="1",
            year="2025",
            genre="Rock",
        )
        write_metadata(meta)

        # Now write empty fields
        meta2 = TrackMetadata(file_path=tmp_mp3)
        write_metadata(meta2)

        result = read_metadata(tmp_mp3)
        assert result.title == ""
        assert result.artist == ""
        assert result.album_artist == ""
        assert result.album == ""
        assert result.track_number == ""
        assert result.year == ""
        assert result.genre == ""


class TestWriteReadCycleFLAC:
    """Test write/read cycle for FLAC files."""

    def test_write_and_read_metadata(self, tmp_flac):
        meta = TrackMetadata(
            file_path=tmp_flac,
            title="Test",
            artist="Artist",
            album_artist="Album Artist",
            album="Album",
            track_number="3",
            year="2025",
            genre="Pop",
        )
        write_metadata(meta)
        result = read_metadata(tmp_flac)
        assert result.title == "Test"
        assert result.artist == "Artist"
        assert result.album_artist == "Album Artist"
        assert result.album == "Album"
        assert result.track_number == "3"
        assert result.year == "2025"
        assert result.genre == "Pop"

    def test_empty_fields_are_cleared(self, tmp_flac):
        # First write some data
        meta = TrackMetadata(
            file_path=tmp_flac,
            title="Title",
            artist="Artist",
            album_artist="Album Artist",
            album="Album",
            track_number="1",
            year="2025",
            genre="Rock",
        )
        write_metadata(meta)

        # Now write empty fields
        meta2 = TrackMetadata(file_path=tmp_flac)
        write_metadata(meta2)

        result = read_metadata(tmp_flac)
        assert result.title == ""
        assert result.artist == ""
        assert result.album_artist == ""
        assert result.album == ""
        assert result.track_number == ""
        assert result.year == ""
        assert result.genre == ""


class TestWriteReadCycleM4A:
    """Test write/read cycle for M4A files."""

    def test_write_and_read_metadata(self, tmp_m4a):
        meta = TrackMetadata(
            file_path=tmp_m4a,
            title="Test",
            artist="Artist",
            album_artist="Album Artist",
            album="Album",
            track_number="3",
            year="2025",
            genre="Pop",
        )
        write_metadata(meta)
        result = read_metadata(tmp_m4a)
        assert result.title == "Test"
        assert result.artist == "Artist"
        assert result.album_artist == "Album Artist"
        assert result.album == "Album"
        assert result.track_number == "3"
        assert result.year == "2025"
        assert result.genre == "Pop"

    def test_empty_fields_are_cleared(self, tmp_m4a):
        # First write some data
        meta = TrackMetadata(
            file_path=tmp_m4a,
            title="Title",
            artist="Artist",
            album_artist="Album Artist",
            album="Album",
            track_number="1",
            year="2025",
            genre="Rock",
        )
        write_metadata(meta)

        # Now write empty fields
        meta2 = TrackMetadata(file_path=tmp_m4a)
        write_metadata(meta2)

        result = read_metadata(tmp_m4a)
        assert result.title == ""
        assert result.artist == ""
        assert result.album_artist == ""
        assert result.album == ""
        assert result.track_number == ""
        assert result.year == ""
        assert result.genre == ""

    def test_empty_tracknumber_no_exception(self, tmp_m4a):
        """Ensure empty tracknumber does not raise ValueError on M4A."""
        meta = TrackMetadata(
            file_path=tmp_m4a,
            title="Test",
            track_number="",
        )
        # Should not raise
        write_metadata(meta)
