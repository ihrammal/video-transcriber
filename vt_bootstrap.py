"""vt_bootstrap.py -- runtime bootstrap.

This module MUST be the first import of the application entry point.

Why it exists
-------------
When PyInstaller builds a *windowed* executable (``console=False``) for Windows,
the bootloader leaves ``sys.stdout`` and ``sys.stderr`` set to ``None``.
Third-party libraries that call ``stream.write(...)`` then die with::

    AttributeError: 'NoneType' object has no attribute 'write'

That is exactly what broke transcription in the first release: the Whisper model
is fetched through ``huggingface_hub``, which renders a ``tqdm`` progress bar on
``sys.stderr``.  ``tqdm`` dereferences the ``None`` stream and raises, the whole
background thread aborts and the user only ever sees "Transcription failed".

This module replaces both streams with real handles backed by a rotating log
file, installs global exception hooks and exposes the small helpers
(``resource_path``, ``app_data_dir``) that the rest of the application uses.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import threading
import traceback

APP_NAME = "Accessible Video Transcriber"
LEGACY_APP_NAME = "VidTrans"
APP_DISPLAY_NAME = "Accessible Video Transcriber"
APP_VERSION = "1.2.0"
LOG_FILENAME = "vidtrans.log"
MAX_LOG_BYTES = 1_000_000

_installed = False
_CONSOLE_STDERR = None  # stderr as it was before teeing (None when frozen)


# --------------------------------------------------------------------- paths
def app_data_dir() -> str:
    """Per-user writable data directory (never Program Files)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        path = os.path.join(os.path.expanduser("~"), APP_NAME)
        os.makedirs(path, exist_ok=True)
    return path


def resource_path(*parts: str) -> str:
    """Resolve a bundled data file (works in dev mode and inside a frozen exe)."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def log_path() -> str:
    return os.path.join(app_data_dir(), LOG_FILENAME)


def setup_runtime_dirs() -> str:
    """Send temp files and the Whisper model cache into the app data folder.

    Called once at startup, before any window opens: every ``tempfile`` call,
    every subprocess (ffmpeg) and every Hugging Face download then writes
    under ``%LOCALAPPDATA%\\Accessible Video Transcriber`` instead of the
    system temp folder, the user profile cache or the program folder.
    """
    data = app_data_dir()
    temp = os.path.join(data, "temp")
    try:
        os.makedirs(temp, exist_ok=True)
        for variable in ("TMPDIR", "TEMP", "TMP"):
            os.environ[variable] = temp
        import tempfile

        tempfile.tempdir = None  # force gettempdir() to re-read the environment
    except OSError:
        pass
    try:
        home = os.path.join(data, "huggingface")
        os.makedirs(home, exist_ok=True)
        os.environ["HF_HOME"] = home
    except OSError:
        pass
    return data


# ------------------------------------------------------------------- streams
class _LogFileStream:
    """Minimal file-like object that never raises, never blocks and never dies."""

    def __init__(self, handle):
        self._handle = handle

    def write(self, text):
        try:
            if not text:
                return 0
            self._handle.write(str(text))
            self._handle.flush()
            return len(text)
        except Exception:
            return 0

    def writelines(self, lines):
        for line in lines or ():
            self.write(line)

    def flush(self):
        try:
            self._handle.flush()
        except Exception:
            pass

    def isatty(self):
        return False

    def fileno(self):
        raise io.UnsupportedOperation("log stream has no file descriptor")  # noqa: F821

    def close(self):
        # The process-wide log must stay open for the lifetime of the app.
        pass

    @property
    def encoding(self):
        return "utf-8"

    @property
    def errors(self):
        return "replace"


import io  # noqa: E402  (used by _LogFileStream.fileno)


def _open_log_handle():
    path = log_path()
    try:
        if os.path.exists(path) and os.path.getsize(path) > MAX_LOG_BYTES:
            os.replace(path, path + ".old")
    except OSError:
        pass
    try:
        return open(path, "a", encoding="utf-8", errors="replace")
    except OSError:
        return open(os.devnull, "a", encoding="utf-8", errors="replace")


def install_streams() -> None:
    """Point stdout/stderr at the log file when they are None (frozen windowed builds).

    If stdout already exists (running from a terminal) we keep it, but still tee
    into the log file so that a crash is always recorded somewhere.
    """
    handle = _open_log_handle()
    log_stream = _LogFileStream(handle)

    global _CONSOLE_STDERR
    _CONSOLE_STDERR = sys.stderr

    try:
        # Never wrap the log stream into itself: a self-tee would write every
        # line into the log file twice.
        if sys.stdout is None:
            sys.stdout = log_stream
        else:
            sys.stdout = _Tee(sys.stdout, log_stream)
        if sys.stderr is None:
            sys.stderr = log_stream
        else:
            sys.stderr = _Tee(sys.stderr, log_stream)
    except Exception:
        pass


class _Tee:
    """Write to the original stream *and* to the log file."""

    def __init__(self, primary, secondary):
        self._primary = primary
        self._secondary = secondary

    def write(self, text):
        try:
            self._primary.write(text)
        except Exception:
            pass
        self._secondary.write(text)
        return 0 if text is None else len(text)

    def writelines(self, lines):
        for line in lines or ():
            self.write(line)

    def flush(self):
        for stream in (self._primary, self._secondary):
            try:
                stream.flush()
            except Exception:
                pass

    def isatty(self):
        try:
            return bool(self._primary.isatty())
        except Exception:
            return False

    def close(self):
        pass

    @property
    def encoding(self):
        return "utf-8"

    @property
    def errors(self):
        return "replace"


# ------------------------------------------------------------------- logging
def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_vidtrans_configured", False):
        return
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s"
    )

    file_handler = logging.FileHandler(log_path(), encoding="utf-8", errors="replace")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Bind the console stream that existed *before* it was teed into the log
    # file, otherwise every record would be written to the log twice (once by
    # the file handler, once by the tee).  Frozen windowed builds have no
    # console at all, so no stream handler is attached there.
    console = _CONSOLE_STDERR
    if console is None:
        err = sys.stderr
        console = err if err is not None and not isinstance(err, (_Tee, _LogFileStream)) else None
    if console is not None:
        stream_handler = logging.StreamHandler(console)
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    for noisy in ("urllib3", "httpx", "httpcore", "huggingface_hub", "PIL", "matplotlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root._vidtrans_configured = True  # type: ignore[attr-defined]


# --------------------------------------------------------------- error hooks
def _write_crash_report(exc_type, exc_value, exc_tb) -> str:
    path = os.path.join(app_data_dir(), "crash.log")
    try:
        with open(path, "a", encoding="utf-8", errors="replace") as fh:
            fh.write("\n=== %s ===\n" % _now())
            fh.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        return path
    except Exception:
        return ""


def _now() -> str:
    import datetime as _dt

    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _qt_message_box(title: str, text: str) -> None:
    """Show a native error box; used only for fatal, unhandled exceptions."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        QMessageBox.critical(None, title, text)
    except Exception:
        try:
            sys.stderr.write("%s: %s\n" % (title, text))
        except Exception:
            pass


def install_exception_hooks() -> None:
    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        report = _write_crash_report(exc_type, exc_value, exc_tb)
        try:
            logging.getLogger("vidtrans").exception("Unhandled exception")
        except Exception:
            pass
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))[-1500:]
        if report:
            _qt_message_box(
                "%s - unexpected error" % APP_DISPLAY_NAME,
                "An unexpected error occurred. A technical report was saved to:\n"
                "%s\n\n%s" % (report, detail),
            )
        else:
            _qt_message_box("%s - unexpected error" % APP_DISPLAY_NAME, detail)
        raise SystemExit(1)

    sys.excepthook = _hook

    def _thread_hook(args):
        _write_crash_report(args.exc_type, args.exc_value, args.exc_traceback)
        try:
            logging.getLogger("vidtrans").error(
                "Thread %s crashed", args.thread, exc_info=(
                    args.exc_type, args.exc_value, args.exc_traceback
                )
            )
        except Exception:
            pass

    threading.excepthook = _thread_hook


def install() -> None:
    """Idempotent: install streams, logging and exception hooks."""
    global _installed
    if _installed:
        return
    _installed = True
    install_streams()
    configure_logging()
    install_exception_hooks()
    logging.getLogger("vidtrans").info(
        "%s %s starting (frozen=%s, python=%s)",
        APP_DISPLAY_NAME,
        APP_VERSION,
        bool(getattr(sys, "frozen", False)),
        sys.version.split()[0],
    )
