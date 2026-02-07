"""Main window implementation"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .metadata import is_supported_file, read_metadata, write_metadata
from .tablemodel import MetadataTableModel


class MainWindow(QMainWindow):
    """Main window for the music metadata editor"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shoboi Tag Editor")
        self.setMinimumSize(900, 600)

        self._model = MetadataTableModel(self)
        self._setup_ui()
        self._setup_actions()
        self._setup_toolbar()

        self.setAcceptDrops(True)

    def _setup_ui(self) -> None:
        """Set up the UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        self._table_view = QTableView()
        self._table_view.setModel(self._model)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        header = self._table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.resizeSection(0, 200)
        header.resizeSection(1, 150)
        header.resizeSection(2, 120)
        header.resizeSection(3, 150)

        layout.addWidget(self._table_view)

    def _setup_actions(self) -> None:
        """Set up actions"""
        self._open_action = QAction(self.tr("Open Files..."), self)
        self._open_action.setShortcut(QKeySequence.StandardKey.Open)
        self._open_action.triggered.connect(self._on_open_files)

        self._save_action = QAction(self.tr("Save"), self)
        self._save_action.setShortcut(QKeySequence.StandardKey.Save)
        self._save_action.triggered.connect(self._on_save)

        self._clear_action = QAction(self.tr("Clear"), self)
        self._clear_action.triggered.connect(self._on_clear)

    def _setup_toolbar(self) -> None:
        """Set up the toolbar"""
        toolbar = QToolBar(self.tr("Main"))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction(self._open_action)
        toolbar.addAction(self._save_action)
        toolbar.addSeparator()
        toolbar.addAction(self._clear_action)

    def _on_open_files(self) -> None:
        """Show the open file dialog"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Select Music Files"),
            "",
            self.tr("Music Files (*.mp3 *.m4a *.flac);;All Files (*)"),
        )

        self._add_files([Path(f) for f in files])

    def _add_files(self, file_paths: list[Path]) -> None:
        """Add files"""
        for file_path in file_paths:
            if not file_path.is_file():
                continue
            if not is_supported_file(file_path):
                continue
            if self._model.has_file(file_path):
                continue

            try:
                metadata = read_metadata(file_path)
                self._model.add_track(metadata)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self.tr("Load Error"),
                    self.tr("Failed to load file:") + f"\n{file_path}\n\n{e}",
                )

    def _on_save(self) -> None:
        """Save modified metadata"""
        modified = self._model.get_modified_tracks()
        if not modified:
            QMessageBox.information(self, self.tr("Save"), self.tr("No modified tracks."))
            return

        errors = []
        for track in modified:
            try:
                write_metadata(track)
            except Exception as e:
                errors.append(f"{track.file_path.name}: {e}")

        self._model.mark_all_saved()

        if errors:
            QMessageBox.warning(
                self,
                self.tr("Save Error"),
                self.tr("Failed to save some files:") + "\n\n" + "\n".join(errors),
            )
        else:
            QMessageBox.information(
                self,
                self.tr("Save Complete"),
                self.tr("Saved %n file(s).", "", len(modified)),
            )

    def _on_clear(self) -> None:
        """Clear the list"""
        modified = self._model.get_modified_tracks()
        if modified:
            reply = QMessageBox.question(
                self,
                self.tr("Confirm"),
                self.tr("There are %n unsaved change(s). Clear anyway?", "", len(modified)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._model.clear()

    def dragEnterEvent(self, event) -> None:
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        """Handle drop event"""
        urls = event.mimeData().urls()
        file_paths = []

        for url in urls:
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.is_dir():
                    for ext in [".mp3", ".m4a", ".flac"]:
                        file_paths.extend(path.rglob(f"*{ext}"))
                else:
                    file_paths.append(path)

        self._add_files(file_paths)
        event.acceptProposedAction()

    def closeEvent(self, event) -> None:
        """Confirm before closing the window"""
        modified = self._model.get_modified_tracks()
        if modified:
            reply = QMessageBox.question(
                self,
                self.tr("Confirm"),
                self.tr("There are %n unsaved change(s). Exit anyway?", "", len(modified)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

        event.accept()
