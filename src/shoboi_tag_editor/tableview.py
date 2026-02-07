"""Custom QTableView with Excel-like keyboard navigation"""

from io import BytesIO
from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice, QItemSelection, QItemSelectionModel, Qt
from PyQt6.QtGui import QGuiApplication, QImage
from PyQt6.QtWidgets import QAbstractItemDelegate, QAbstractItemView, QTableView

from .tablemodel import COVER_COLUMN, FILENAME_COLUMN


class SingleColumnSelectionModel(QItemSelectionModel):
    """Selection model that restricts selection to a single column"""

    def __init__(self, model=None, parent=None):
        super().__init__(model, parent)
        self._active_column = None

    def select(self, selection, command):
        """Override to restrict selection to a single column"""
        # Reset active column on Clear
        if command & QItemSelectionModel.SelectionFlag.Clear:
            self._active_column = None

        # Determine which column we're trying to select
        if isinstance(selection, QItemSelection):
            if selection.isEmpty():
                super().select(selection, command)
                return
            # Get the first index from the selection
            indexes = selection.indexes()
            if not indexes:
                super().select(selection, command)
                return
            new_column = indexes[0].column()
        else:
            # selection is a QModelIndex
            if not selection.isValid():
                super().select(selection, command)
                return
            new_column = selection.column()

        # If we have an active column and the new selection is in a different column,
        # clear the selection and set the new column as active
        if self._active_column is not None and new_column != self._active_column:
            self._active_column = new_column
            # Clear existing selection and select the new item
            super().select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            return

        # Set or maintain the active column
        if self._active_column is None:
            self._active_column = new_column

        super().select(selection, command)


class NavigableTableView(QTableView):
    """QTableView with Excel-like keyboard navigation"""

    # First editable text column (Title)
    FIRST_EDITABLE_COLUMN = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)

        # Enable drag and drop for cover images
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

    def setModel(self, model):
        """Override to apply SingleColumnSelectionModel"""
        super().setModel(model)
        if model is not None:
            selection_model = SingleColumnSelectionModel(model, self)
            self.setSelectionModel(selection_model)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard navigation"""
        model = self.model()
        if model is None or model.rowCount() == 0:
            super().keyPressEvent(event)
            return

        current = self.currentIndex()
        if not current.isValid():
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        # If currently editing, let the editor handle keys
        if self.state() == QAbstractItemView.State.EditingState:
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right):
                super().keyPressEvent(event)
                return
            # Let editor handle Ctrl+C/V
            if key in (Qt.Key.Key_C, Qt.Key.Key_V) and modifiers & Qt.KeyboardModifier.ControlModifier:
                super().keyPressEvent(event)
                return

        # Handle copy/paste when not editing
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C:
                self._copy_selection()
                return
            elif key == Qt.Key.Key_V:
                self._paste_to_selection()
                return

        # Handle delete key
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._delete_selection()
            return

        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._handle_enter(current)
        elif key == Qt.Key.Key_Tab:
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                self._handle_shift_tab(current)
            else:
                self._handle_tab(current)
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right):
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                # Let Qt handle shift+arrow for range selection
                super().keyPressEvent(event)
            else:
                # Custom single-cell navigation
                if key == Qt.Key.Key_Up:
                    self._move_to_cell(current.row() - 1, current.column())
                elif key == Qt.Key.Key_Down:
                    self._move_to_cell(current.row() + 1, current.column())
                elif key == Qt.Key.Key_Left:
                    self._move_to_cell(current.row(), current.column() - 1)
                elif key == Qt.Key.Key_Right:
                    self._move_to_cell(current.row(), current.column() + 1)
        else:
            super().keyPressEvent(event)

    def _handle_enter(self, current) -> None:
        """Handle Enter key: commit edit and move down"""
        # Close any active editor
        if self.state() == QAbstractItemView.State.EditingState:
            self.commitData(self.indexWidget(current))
            self.closeEditor(self.indexWidget(current), QAbstractItemDelegate.EndEditHint.NoHint)

        # Move to next row (same column)
        next_row = current.row() + 1
        if next_row < self.model().rowCount():
            self._move_to_cell(next_row, current.column())

    def _handle_tab(self, current) -> None:
        """Handle Tab key: move right, skip Cover/Filename columns, wrap to next row"""
        model = self.model()
        row = current.row()
        col = current.column()

        # Find next editable text column
        next_col = col + 1
        while next_col < model.columnCount():
            if next_col not in (COVER_COLUMN, FILENAME_COLUMN):
                self._move_to_cell(row, next_col)
                return
            next_col += 1

        # Reached end of row, move to next row's first editable column
        next_row = row + 1
        if next_row < model.rowCount():
            self._move_to_cell(next_row, self.FIRST_EDITABLE_COLUMN)

    def _handle_shift_tab(self, current) -> None:
        """Handle Shift+Tab: move left, skip Cover/Filename columns, wrap to previous row"""
        model = self.model()
        row = current.row()
        col = current.column()

        # Find previous editable text column
        prev_col = col - 1
        while prev_col >= 0:
            if prev_col not in (COVER_COLUMN, FILENAME_COLUMN):
                self._move_to_cell(row, prev_col)
                return
            prev_col -= 1

        # Reached beginning of row, move to previous row's last column
        prev_row = row - 1
        if prev_row >= 0:
            last_col = model.columnCount() - 1
            self._move_to_cell(prev_row, last_col)

    def _move_to_cell(self, row: int, col: int) -> None:
        """Move selection to specified cell if valid"""
        model = self.model()
        if model is None:
            return

        if row < 0 or row >= model.rowCount():
            return
        if col < 0 or col >= model.columnCount():
            return

        index = model.index(row, col)
        self.setCurrentIndex(index)

    def _copy_selection(self) -> None:
        """Copy selected cells' values to clipboard"""
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            return

        # Sort by row to get consistent order
        indexes = sorted(indexes, key=lambda idx: idx.row())

        clipboard = QGuiApplication.clipboard()

        # If selecting cover column, copy image
        if indexes[0].column() == COVER_COLUMN:
            # Copy first selected cover image
            data = indexes[0].data(Qt.ItemDataRole.UserRole)
            if data and data[0]:
                image_data, _ = data
                image = QImage()
                if image.loadFromData(image_data):
                    clipboard.setImage(image)
            return

        # Copy text values (newline separated for multiple cells)
        values = []
        for index in indexes:
            value = index.data(Qt.ItemDataRole.DisplayRole)
            if value is not None:
                values.append(str(value))
            else:
                values.append("")

        clipboard.setText("\n".join(values))

    def _paste_to_selection(self) -> None:
        """Paste clipboard value to all selected cells"""
        model = self.model()
        if model is None:
            return

        clipboard = QGuiApplication.clipboard()
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            return

        # If pasting to cover column, try to paste image
        if indexes[0].column() == COVER_COLUMN:
            image = clipboard.image()
            if not image.isNull():
                # Convert image to PNG bytes
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                image.save(buffer, "PNG")
                image_data = bytes(buffer.data())
                buffer.close()

                for index in indexes:
                    if index.column() == COVER_COLUMN:
                        model.setData(index, (image_data, "image/png"), Qt.ItemDataRole.UserRole)
            return

        # Paste text to other columns
        text = clipboard.text()
        if not text:
            return

        # Paste same value to all selected cells (skip cover/filename columns)
        for index in indexes:
            if index.column() in (COVER_COLUMN, FILENAME_COLUMN):
                continue
            model.setData(index, text, Qt.ItemDataRole.EditRole)

    def _delete_selection(self) -> None:
        """Delete selected cells' values"""
        model = self.model()
        if model is None:
            return

        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            return

        for index in indexes:
            col = index.column()
            if col == FILENAME_COLUMN:
                continue
            if col == COVER_COLUMN:
                # Delete cover image
                model.setData(index, (None, "image/jpeg"), Qt.ItemDataRole.UserRole)
            else:
                # Clear text field
                model.setData(index, "", Qt.ItemDataRole.EditRole)

    def dragEnterEvent(self, event) -> None:
        """Handle drag enter for image files"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    path = Path(url.toLocalFile())
                    if path.suffix.lower() in (".jpg", ".jpeg", ".png"):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        """Handle drag move for image files"""
        index = self.indexAt(event.position().toPoint())
        if index.isValid() and index.column() == COVER_COLUMN:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """Handle drop of image files onto cover column"""
        index = self.indexAt(event.position().toPoint())
        if not index.isValid() or index.column() != COVER_COLUMN:
            event.ignore()
            return

        model = self.model()
        if model is None:
            event.ignore()
            return

        urls = event.mimeData().urls()
        for url in urls:
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                suffix = path.suffix.lower()
                if suffix in (".jpg", ".jpeg", ".png"):
                    try:
                        image_data = path.read_bytes()
                        if suffix == ".png":
                            mime = "image/png"
                        else:
                            mime = "image/jpeg"
                        model.setData(index, (image_data, mime), Qt.ItemDataRole.UserRole)
                        event.acceptProposedAction()
                        return
                    except Exception:
                        pass

        event.ignore()
