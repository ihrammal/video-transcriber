"""Regression tests for the bugs found in the installed build.

* ``TypeError: tr() got multiple values for argument 'lang'`` crashed the app
  right after every transcription (``crash.log``).
* ``vt_a11y.update()`` was called with a positional dict, so accessibility
  toggles could not be saved.
* The welcome and exit screens now count down three seconds and close
  themselves, then the main window opens / the program exits.
"""

from __future__ import annotations

import re
import time
from datetime import timedelta

from PyQt6.QtCore import QTimer


def test_transcribe_done_does_not_crash(qapp, profile):
    """The exact crash from crash.log: t(..., lang=...) collides with tr()."""
    import srt

    from vid_trans_app import MainWindow

    window = MainWindow("en")
    try:
        window.announce = lambda *a, **k: None
        window.feedback = lambda *a, **k: None
        subtitles = [
            srt.Subtitle(index=1, start=timedelta(0), end=timedelta(1),
                         content="Hello world"),
        ]
        window._on_transcribe_done(subtitles, "en", "missing.wav")
        assert window.subtitles == subtitles
        # and the Arabic string formats with the same keyword
        assert "1" in window.t(
            "msg_transcribe_done", count=1, language=window.lang_name("ar")
        )
    finally:
        window.deleteLater()
        qapp.processEvents()


def test_set_a11y_saves_the_flag(qapp, profile, monkeypatch):
    """update() takes keyword flags only: update(**{...}), not update({...})."""
    import vt_a11y

    from vid_trans_app import MainWindow

    recorded = {}
    monkeypatch.setattr(vt_a11y, "update", lambda **flags: recorded.update(flags))
    window = MainWindow("en")
    try:
        window._set_a11y("high_contrast", True)
    finally:
        window.deleteLater()
        qapp.processEvents()
    assert recorded == {"high_contrast": True}


def test_no_translation_call_passes_lang_kwarg():
    """tr(lang, key, ...) would raise 'multiple values for argument lang'."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    source = (root / "vid_trans_app.py").read_text(encoding="utf-8")
    assert not re.search(r'\.t\(\s*"[^"]+"\s*,[^)]*?\blang\s*=', source, re.S)


def test_transcribe_done_placeholder_is_language():
    import vt_i18n
    import vid_trans_app

    for table in (vid_trans_app.TR, vt_i18n.TR):
        for lang in ("en", "ar"):
            text = table[lang]["msg_transcribe_done"]
            assert "{language}" in text, (lang, text)
            assert "{lang}" not in text, (lang, text)


def test_welcome_counts_down_and_shows_every_launch(qapp, profile, monkeypatch):
    import vt_setup

    monkeypatch.setattr(vt_setup, "play_welcome_music", lambda: None)
    monkeypatch.setattr(vt_setup, "stop_music", lambda: None)

    visible = []
    QTimer.singleShot(150, lambda: visible.append(qapp.activeModalWidget() is not None))
    start = time.monotonic()
    language = vt_setup.show_welcome_screen(qapp, seconds=0.4)
    elapsed = time.monotonic() - start
    assert language in ("en", "ar")
    assert visible == [True], "the greeting must be on screen during the countdown"
    assert 0.3 <= elapsed < 5.0, "the panel must close itself after the countdown"

    # the second launch shows it again (no first-run gate any more)
    visible2 = []
    QTimer.singleShot(150, lambda: visible2.append(qapp.activeModalWidget() is not None))
    start = time.monotonic()
    vt_setup.show_welcome_screen(qapp, seconds=0.3)
    elapsed2 = time.monotonic() - start
    assert visible2 == [True]
    assert 0.2 <= elapsed2 < 5.0


def test_exit_screen_counts_down_and_finishes(qapp, profile, monkeypatch):
    import vt_setup

    monkeypatch.setattr(vt_setup, "play_farewell_music", lambda: None)
    monkeypatch.setattr(vt_setup, "stop_music", lambda: None)
    monkeypatch.setattr(vt_setup, "EXIT_SECONDS", 0.4)

    visible = []
    finished = []
    QTimer.singleShot(150, lambda: visible.append(qapp.activeModalWidget() is not None))
    start = time.monotonic()
    ok = vt_setup.show_exit_screen(qapp, lambda: finished.append(True))
    elapsed = time.monotonic() - start
    assert ok is True
    assert visible == [True], "the goodbye screen must show before it closes"
    assert finished == [True], "closing must run the quit callback"
    assert 0.3 <= elapsed < 5.0


def test_e2e_argument_parsing():
    """``--e2e video [target] [engine]`` drives the headless pipeline."""
    from vt_e2e import _parse

    assert _parse([]) == ("", "none", "auto")
    assert _parse(["video.mp4"]) == ("video.mp4", "none", "auto")
    assert _parse(["video.mp4", "en"]) == ("video.mp4", "en", "auto")
    assert _parse(["video.mp4", "ar", "local"]) == ("video.mp4", "ar", "local")
    assert _parse(["video.mp4", "en", "gemini"]) == ("video.mp4", "en", "gemini")
    # unknown engine words are ignored instead of reaching the engine switch
    assert _parse(["video.mp4", "en", "weird"]) == ("video.mp4", "en", "auto")
    # flags never become the video path
    assert _parse(["--e2e", "video.mp4"]) == ("video.mp4", "none", "auto")


def test_main_routes_the_e2e_flag():
    """The shipped executable must expose the --e2e hook before Qt starts."""
    from pathlib import Path

    source = Path("vid_trans_app.py").read_text(encoding="utf-8")
    hook = source.find('sys.argv[1] == "--e2e"')
    assert hook != -1, "the --e2e flag must be handled in main()"
    window = source.find("app = QApplication(sys.argv)")
    assert window != -1 and hook < window, (
        "the e2e run must start before the main window is created")
