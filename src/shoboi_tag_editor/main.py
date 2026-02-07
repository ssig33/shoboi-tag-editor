"""Application entry point"""

import sys

from PyQt6.QtCore import QLocale, QTranslator
from PyQt6.QtWidgets import QApplication

from .mainwindow import MainWindow
from .translations import TRANSLATIONS_DIR


def main() -> int:
    """Start the application"""
    app = QApplication(sys.argv)
    app.setApplicationName("Shoboi Tag Editor")

    translator = QTranslator()
    locale = QLocale.system().name()

    if locale.startswith("ja"):
        translation_file = TRANSLATIONS_DIR / "shoboi_tag_editor_ja.qm"
        if translation_file.exists() and translator.load(str(translation_file)):
            app.installTranslator(translator)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
