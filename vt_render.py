"""vt_render.py -- helpers for burning captions into a video."""

from __future__ import annotations

import os


def pick_font() -> str:
    """Return a font file that can render both Latin and Arabic text."""
    candidates = [
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), r"Fonts\tahoma.ttf"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), r"Fonts\arial.ttf"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), r"Fonts\segoeui.ttf"),
        "DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return ""


FONT_PATH = pick_font()


def _build_logger(on_progress):
    """Return an object moviepy's ``proglog.default_bar_logger`` accepts.

    moviepy passes the object through unchanged, then calls ``message(...)``,
    ``bars_callback(...)`` and iterates ``iter_bar(...)``.  Subclassing
    ``ProgressBarLogger`` when proglog is present keeps all of that working;
    the fallback implements the same surface by hand so a missing proglog can
    never abort a render.
    """
    try:
        from proglog import ProgressBarLogger
    except Exception:
        ProgressBarLogger = None

    if ProgressBarLogger is not None:

        class _ProglogLogger(ProgressBarLogger):
            def messages_callback(self, message, text="", **kw):
                return None

            def bars_callback(self, bar_name, attribute, value, old_value=None):
                if attribute != "index":
                    return
                bar = self.bars.get(bar_name) or {}
                total = bar.get("total")
                if total:
                    try:
                        on_progress(min(99, int(value / total * 100)))
                    except Exception:
                        pass

        return _ProglogLogger()

    class _FallbackLogger:
        def __call__(self, *args, **kwargs):
            self._handle(kwargs)
            return self

        def message(self, *args, **kwargs):
            return None

        def iter_bar(self, **kwargs):
            key = next(iter(kwargs), "i")
            values = kwargs.get(key) or []
            total = len(list(values)) if not isinstance(values, range) else len(values)
            for count, value in enumerate(values, start=1):
                if total:
                    try:
                        on_progress(min(99, int(count / total * 100)))
                    except Exception:
                        pass
                yield value

        def bars_callback(self, *args, **kwargs):
            return None

        def messages_callback(self, *args, **kwargs):
            return None

        def _handle(self, kwargs):
            progress = kwargs.get("progress")
            if isinstance(progress, dict):
                total = progress.get("total") or progress.get("T")
                index = progress.get("index", progress.get("i", progress.get("t")))
                if total and index is not None:
                    try:
                        on_progress(min(99, int(index / total * 100)))
                    except Exception:
                        pass

    return _FallbackLogger()


class MoviePyProgressLogger:
    """Thin alias so call sites stay readable."""

    def __new__(cls, on_progress):
        return _build_logger(on_progress)
