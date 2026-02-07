"""Application entry point"""

import sys

from PyQt6.QtWidgets import QApplication

from .mainwindow import MainWindow


def main() -> int:
    """Start the application"""
    app = QApplication(sys.argv)
    app.setApplicationName("Shoboi Tag Editor")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
