"""Tests for metadata module"""

from pathlib import Path

import pytest

from shoboi_tag_editor.metadata import (
    SUPPORTED_EXTENSIONS,
    TrackMetadata,
    is_supported_file,
)


class TestTrackMetadata:
    def test_default_values(self):
        path = Path("/test/file.mp3")
        meta = TrackMetadata(file_path=path)

        assert meta.file_path == path
        assert meta.title == ""
        assert meta.artist == ""
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
            album="Test Album",
            track_number="1",
            year="2024",
            genre="Rock",
        )

        assert meta.title == "Test Title"
        assert meta.artist == "Test Artist"
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
