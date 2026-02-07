"""Metadata table model inheriting QAbstractTableModel"""

from pathlib import Path
from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QImage, QPixmap

from .metadata import TrackMetadata

# Column indices
COVER_COLUMN = 0
FILENAME_COLUMN = 1


class MetadataTableModel(QAbstractTableModel):
    """Table model for displaying and editing music metadata"""

    COLUMNS = [
        ("Cover", "cover_image"),
        ("Filename", "file_name"),
        ("Title", "title"),
        ("Artist", "artist"),
        ("Album", "album"),
        ("Track Number", "track_number"),
        ("Year", "year"),
        ("Genre", "genre"),
    ]

    # Cover display size (width x height)
    COVER_WIDTH = 48
    COVER_HEIGHT = 20

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
        attr_name = self.COLUMNS[col][1]

        # Cover image column - special handling
        if attr_name == "cover_image":
            if role == Qt.ItemDataRole.DecorationRole:
                if track.cover_image:
                    return self._get_cover_pixmap(track.cover_image)
                return None
            if role == Qt.ItemDataRole.UserRole:
                # Return raw image data for copy/paste
                return (track.cover_image, track.cover_mime)
            if role == Qt.ItemDataRole.DisplayRole:
                return ""
            if role == Qt.ItemDataRole.BackgroundRole:
                if track.modified:
                    from PyQt6.QtGui import QColor
                    return QColor(255, 255, 200)
            return None

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if attr_name == "file_name":
                return track.file_path.name
            return getattr(track, attr_name, "")

        if role == Qt.ItemDataRole.BackgroundRole:
            if track.modified:
                from PyQt6.QtGui import QColor
                return QColor(255, 255, 200)

        return None

    def _get_cover_pixmap(self, image_data: bytes) -> QPixmap:
        """Convert image data to center-cropped horizontal strip QPixmap"""
        image = QImage()
        if not image.loadFromData(image_data):
            return QPixmap()

        # Calculate crop dimensions to match display aspect ratio
        target_ratio = self.COVER_WIDTH / self.COVER_HEIGHT
        img_w, img_h = image.width(), image.height()

        # Crop a horizontal strip from the center
        crop_w = img_w
        crop_h = int(img_w / target_ratio)
        if crop_h > img_h:
            crop_h = img_h
            crop_w = int(img_h * target_ratio)

        x = (img_w - crop_w) // 2
        y = (img_h - crop_h) // 2
        cropped = image.copy(x, y, crop_w, crop_h)

        # Scale to display size
        scaled = cropped.scaled(
            self.COVER_WIDTH,
            self.COVER_HEIGHT,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return QPixmap.fromImage(scaled)

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
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

        # Handle cover image with UserRole
        if attr_name == "cover_image":
            if role == Qt.ItemDataRole.UserRole:
                # value is (bytes | None, str)
                if isinstance(value, tuple) and len(value) == 2:
                    image_data, mime = value
                    track.cover_image = image_data
                    track.cover_mime = mime if mime else "image/jpeg"
                    track.modified = True
                    self.dataChanged.emit(index, index, [Qt.ItemDataRole.DecorationRole])
                    return True
            return False

        # Handle text fields with EditRole
        if role != Qt.ItemDataRole.EditRole:
            return False

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
        # Cover and Filename are not text-editable
        if attr_name not in ("file_name", "cover_image"):
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
