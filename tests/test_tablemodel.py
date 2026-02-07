"""Tests for tablemodel module"""

from pathlib import Path

import pytest
from PyQt6.QtCore import Qt

from shoboi_tag_editor.metadata import TrackMetadata
from shoboi_tag_editor.tablemodel import MetadataTableModel


@pytest.fixture
def model(qapp):
    return MetadataTableModel()


@pytest.fixture
def sample_track():
    return TrackMetadata(
        file_path=Path("/test/song.mp3"),
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        track_number="1",
        year="2024",
        genre="Rock",
    )


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestMetadataTableModel:
    def test_empty_model(self, model):
        assert model.rowCount() == 0
        assert model.columnCount() == 8

    def test_add_track(self, model, sample_track):
        model.add_track(sample_track)

        assert model.rowCount() == 1

    def test_add_tracks(self, model):
        tracks = [
            TrackMetadata(file_path=Path(f"/test/song{i}.mp3"), title=f"Song {i}")
            for i in range(3)
        ]
        model.add_tracks(tracks)

        assert model.rowCount() == 3

    def test_add_empty_tracks(self, model):
        model.add_tracks([])
        assert model.rowCount() == 0

    def test_clear(self, model, sample_track):
        model.add_track(sample_track)
        assert model.rowCount() == 1

        model.clear()
        assert model.rowCount() == 0

    def test_clear_empty(self, model):
        model.clear()
        assert model.rowCount() == 0

    def test_data_display_role(self, model, sample_track):
        model.add_track(sample_track)

        # Cover column (0) returns empty string for DisplayRole
        index = model.index(0, 0)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == ""

        # Filename column (1)
        index = model.index(0, 1)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "song.mp3"

        # Title column (2)
        index = model.index(0, 2)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Test Song"

        # Artist column (3)
        index = model.index(0, 3)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Test Artist"

    def test_data_invalid_index(self, model, sample_track):
        model.add_track(sample_track)

        index = model.index(-1, 0)
        assert model.data(index) is None

        index = model.index(0, 100)
        assert model.data(index) is None

    def test_set_data(self, model, sample_track):
        model.add_track(sample_track)

        # Title column is now index 2
        index = model.index(0, 2)
        result = model.setData(index, "New Title", Qt.ItemDataRole.EditRole)

        assert result is True
        assert model.data(index) == "New Title"

    def test_set_data_marks_modified(self, model, sample_track):
        model.add_track(sample_track)

        # Title column is now index 2
        index = model.index(0, 2)
        model.setData(index, "New Title", Qt.ItemDataRole.EditRole)

        modified = model.get_modified_tracks()
        assert len(modified) == 1

    def test_set_data_same_value(self, model, sample_track):
        model.add_track(sample_track)

        # Title column is now index 2
        index = model.index(0, 2)
        result = model.setData(index, "Test Song", Qt.ItemDataRole.EditRole)

        assert result is False

    def test_set_data_filename_readonly(self, model, sample_track):
        model.add_track(sample_track)

        # Filename column is now index 1
        index = model.index(0, 1)
        result = model.setData(index, "new_name.mp3", Qt.ItemDataRole.EditRole)

        assert result is False

    def test_flags_cover_not_editable(self, model, sample_track):
        model.add_track(sample_track)

        # Cover column (0)
        index = model.index(0, 0)
        flags = model.flags(index)

        assert not (flags & Qt.ItemFlag.ItemIsEditable)

    def test_flags_filename_not_editable(self, model, sample_track):
        model.add_track(sample_track)

        # Filename column (1)
        index = model.index(0, 1)
        flags = model.flags(index)

        assert not (flags & Qt.ItemFlag.ItemIsEditable)

    def test_flags_other_columns_editable(self, model, sample_track):
        model.add_track(sample_track)

        # Columns 2+ (Title, Artist, etc.) are editable
        for col in range(2, model.columnCount()):
            index = model.index(0, col)
            flags = model.flags(index)
            assert flags & Qt.ItemFlag.ItemIsEditable

    def test_has_file(self, model, sample_track):
        model.add_track(sample_track)

        assert model.has_file(Path("/test/song.mp3")) is True
        assert model.has_file(Path("/test/other.mp3")) is False

    def test_get_modified_tracks(self, model):
        tracks = [
            TrackMetadata(file_path=Path(f"/test/song{i}.mp3"), title=f"Song {i}")
            for i in range(3)
        ]
        model.add_tracks(tracks)

        # Title column is now index 2
        index = model.index(1, 2)
        model.setData(index, "Modified", Qt.ItemDataRole.EditRole)

        modified = model.get_modified_tracks()
        assert len(modified) == 1
        assert modified[0].title == "Modified"

    def test_get_all_tracks(self, model):
        tracks = [
            TrackMetadata(file_path=Path(f"/test/song{i}.mp3"))
            for i in range(3)
        ]
        model.add_tracks(tracks)

        all_tracks = model.get_all_tracks()
        assert len(all_tracks) == 3

    def test_mark_all_saved(self, model):
        tracks = [
            TrackMetadata(file_path=Path(f"/test/song{i}.mp3"), title=f"Song {i}")
            for i in range(2)
        ]
        model.add_tracks(tracks)

        # Title column is now index 2
        model.setData(model.index(0, 2), "Modified 1", Qt.ItemDataRole.EditRole)
        model.setData(model.index(1, 2), "Modified 2", Qt.ItemDataRole.EditRole)

        assert len(model.get_modified_tracks()) == 2

        model.mark_all_saved()

        assert len(model.get_modified_tracks()) == 0

    def test_header_data(self, model):
        # Cover column (0)
        header = model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        assert header == "Cover"

        # Filename column (1)
        header = model.headerData(1, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        assert header == "Filename"

        # Title column (2)
        header = model.headerData(2, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        assert header == "Title"
