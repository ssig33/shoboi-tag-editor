"""Metadata table model inheriting QAbstractTableModel"""

from pathlib import Path
from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from .metadata import TrackMetadata


class MetadataTableModel(QAbstractTableModel):
    """Table model for displaying and editing music metadata"""

    COLUMNS = [
        ("Filename", "file_name"),
        ("Title", "title"),
        ("Artist", "artist"),
        ("Album", "album"),
        ("Track Number", "track_number"),
        ("Year", "year"),
        ("Genre", "genre"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list[TrackMetadata] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._tracks)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.COLUMNS)

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self.COLUMNS):
                return self.tr(self.COLUMNS[section][0])
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._tracks):
            return None
        if col < 0 or col >= len(self.COLUMNS):
            return None

        track = self._tracks[row]

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            attr_name = self.COLUMNS[col][1]
            if attr_name == "file_name":
                return track.file_path.name
            return getattr(track, attr_name, "")

        if role == Qt.ItemDataRole.BackgroundRole:
            if track.modified:
                from PyQt6.QtGui import QColor
                return QColor(255, 255, 200)

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._tracks):
            return False
        if col < 0 or col >= len(self.COLUMNS):
            return False

        attr_name = self.COLUMNS[col][1]
        if attr_name == "file_name":
            return False

        track = self._tracks[row]
        old_value = getattr(track, attr_name, "")

        if old_value != value:
            setattr(track, attr_name, str(value))
            track.modified = True
            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        col = index.column()
        attr_name = self.COLUMNS[col][1]
        if attr_name != "file_name":
            flags |= Qt.ItemFlag.ItemIsEditable

        return flags

    def add_tracks(self, tracks: list[TrackMetadata]) -> None:
        """Add tracks"""
        if not tracks:
            return
        begin = len(self._tracks)
        end = begin + len(tracks) - 1
        self.beginInsertRows(QModelIndex(), begin, end)
        self._tracks.extend(tracks)
        self.endInsertRows()

    def add_track(self, track: TrackMetadata) -> None:
        """Add a single track"""
        self.add_tracks([track])

    def clear(self) -> None:
        """Clear all tracks"""
        if not self._tracks:
            return
        self.beginRemoveRows(QModelIndex(), 0, len(self._tracks) - 1)
        self._tracks.clear()
        self.endRemoveRows()

    def get_modified_tracks(self) -> list[TrackMetadata]:
        """Return list of modified tracks"""
        return [t for t in self._tracks if t.modified]

    def get_all_tracks(self) -> list[TrackMetadata]:
        """Return all tracks"""
        return self._tracks.copy()

    def has_file(self, file_path: Path) -> bool:
        """Check if the specified file has already been added"""
        return any(t.file_path == file_path for t in self._tracks)

    def mark_all_saved(self) -> None:
        """Clear the modified flag of all tracks"""
        for track in self._tracks:
            track.modified = False
        if self._tracks:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._tracks) - 1, len(self.COLUMNS) - 1),
            )
