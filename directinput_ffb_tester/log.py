"""Session log for the test tool: appended timestamped lines plus stack traces."""
from __future__ import annotations

import datetime
import os
import threading
import traceback

_log_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                        "py_directinput_ffb")
FilePath = os.path.join(_log_dir, "test_tool.log")
_lock = threading.Lock()


def set_dir(path: str) -> None:
    global _log_dir, FilePath
    _log_dir = path
    FilePath = os.path.join(_log_dir, "test_tool.log")


def _write(kind: str, msg: str, exc: object = None) -> None:
    line = (f"{datetime.datetime.now().isoformat(timespec='milliseconds')} "
            f"[{kind}] {msg}")
    if exc is not None:
        line += "\n" + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    with _lock:
        try:
            os.makedirs(_log_dir, exist_ok=True)
            with open(FilePath, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass


def info(msg: str) -> None:
    _write("INFO", msg)


def warn(msg: str) -> None:
    _write("WARN", msg)


def error(msg: str, exc: object = None) -> None:
    _write("ERROR", msg, exc)


def open_in_editor() -> None:
    try:
        os.startfile(FilePath)
    except Exception:
        pass


__all__ = ["FilePath", "set_dir", "info", "warn", "error", "open_in_editor"]
