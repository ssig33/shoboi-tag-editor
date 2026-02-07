"""Custom QTableView with Excel-like keyboard navigation"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemDelegate, QAbstractItemView, QTableView


class NavigableTableView(QTableView):
    """QTableView with Excel-like keyboard navigation"""

    # Filename column (read-only, skip when navigating)
    FILENAME_COLUMN = 0
    # First editable column (Title)
    FIRST_EDITABLE_COLUMN = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)

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

        # If currently editing, let the editor handle arrow keys
        if self.state() == QAbstractItemView.State.EditingState:
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right):
                super().keyPressEvent(event)
                return

        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._handle_enter(current)
        elif key == Qt.Key.Key_Tab:
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                self._handle_shift_tab(current)
            else:
                self._handle_tab(current)
        elif key == Qt.Key.Key_Up:
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
        """Handle Tab key: move right, skip Filename column, wrap to next row"""
        model = self.model()
        row = current.row()
        col = current.column()

        # Find next editable column
        next_col = col + 1
        while next_col < model.columnCount():
            if next_col != self.FILENAME_COLUMN:
                self._move_to_cell(row, next_col)
                return
            next_col += 1

        # Reached end of row, move to next row's first editable column
        next_row = row + 1
        if next_row < model.rowCount():
            self._move_to_cell(next_row, self.FIRST_EDITABLE_COLUMN)

    def _handle_shift_tab(self, current) -> None:
        """Handle Shift+Tab: move left, skip Filename column, wrap to previous row"""
        model = self.model()
        row = current.row()
        col = current.column()

        # Find previous editable column
        prev_col = col - 1
        while prev_col >= 0:
            if prev_col != self.FILENAME_COLUMN:
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
