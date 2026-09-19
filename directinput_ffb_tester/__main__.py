"""Run the FFB test tool: python -m directinput_ffb_tester"""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from .window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("py_directinput_ffb FFB Test Tool")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
