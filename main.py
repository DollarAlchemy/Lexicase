"""LexiCase — entry point.

Run from inside the lexicase/ folder:
    python main.py

Build Step 1: open the dashboard shell. No case data is loaded yet — that
arrives in Step 2 (the case data model). Everything the UI needs from disk
will go through app/case_api.py, never directly, so later steps slot in
cleanly. See the build map for the full sequence.
"""
import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.theme import ACTIVE, build_qss


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LexiCase")
    app.setOrganizationName("LexiCase")
    app.setStyle("Fusion")              # consistent base across OSes (ignores OS dark mode)
    app.setStyleSheet(build_qss(ACTIVE))  # applies to the window AND dialogs

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
