"""Application bootstrap."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
import traceback

from .storage_json import JsonStorage


ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT_DIR / "logs" / "app.log"
DATA_PATH = ROOT_DIR / "data" / "launcher.json"


def setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def _handle_unexpected_exception(exc_type, exc_value, exc_tb):
    from PyQt6.QtWidgets import QApplication, QMessageBox

    message = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.error("Unhandled exception\n%s", message)
    app = QApplication.instance()
    if app is not None:
        QMessageBox.critical(None, "Unhandled Exception", str(exc_value))


def main() -> int:
    from PyQt6.QtWidgets import QApplication

    setup_logging()
    logging.info("Application starting")

    sys.excepthook = _handle_unexpected_exception

    app = QApplication(sys.argv)
    from .ui_mainwindow import MainWindow

    storage = JsonStorage(DATA_PATH)
    window = MainWindow(storage)
    window.show()
    return app.exec()
