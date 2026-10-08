"""vt_e2e.py -- headless end-to-end check shipped with the application.

    AccessibleVideoTranscriber.exe --e2e <video> [target-language] [engine]

Runs the real pipeline offscreen: audio extraction, transcription with the
local Whisper model, and -- when a target language is given -- one cloud
translation.  Every stage is recorded in ``e2e-report.txt`` next to the
preferences, the program prints the report when a console exists, and the
exit code is 0 only when the requested work completed without an error.

This is how the installed executable is verified on a user's machine: it
exercises exactly the code paths the Start button uses, without needing a
desktop session, a screen reader or a mouse.
"""

from __future__ import annotations

import io
import logging
import os
import sys
import time
import traceback

log = logging.getLogger("vidtrans.e2e")

TRANSCRIBE_TIMEOUT = 1200
TRANSLATE_TIMEOUT = 300


def _report_path() -> str:
    try:
        import vt_bootstrap

        return os.path.join(vt_bootstrap.app_data_dir(), "e2e-report.txt")
    except Exception:  # noqa: BLE001
        return os.path.join(os.path.expanduser("~"), "vt-e2e-report.txt")


def _parse(argv) -> tuple:
    positional = [arg for arg in argv if not arg.startswith("-")]
    video = positional[0] if positional else ""
    target = positional[1] if len(positional) > 1 else "none"
    engine = "auto"
    if len(positional) > 2 and positional[2] in ("local", "openai", "groq", "gemini"):
        engine = positional[2]
    return video, target, engine


def run(argv) -> int:
    video, target, engine = _parse(argv)
    lines = []

    def say(text):
        lines.append(text)
        try:
            print(text)
        except Exception:  # noqa: BLE001 - a windowed build may have no console
            pass

    say("e2e start: video=%r target=%r engine=%r" % (video, target, engine))
    if not video or not os.path.isfile(video):
        say("FAIL: the video file does not exist")
        return _finish(lines, 2)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    import vid_trans_app

    class _StubBox:
        class Icon:
            Information = 1
            Warning = 2
            Critical = 3

        class ButtonRole:
            AcceptRole = 0
            RejectRole = 1

        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, name):
            def _method(*args, **kwargs):
                if name in ("exec", "exec_"):
                    return 0
                if name == "clickedButton":
                    return None
                say("  box: %s" % name)
                return None

            return _method

        @classmethod
        def warning(cls, *args, **kwargs):
            say("  box warning: %s" % (str(args[1])[:120] if len(args) > 1 else ""))

        @classmethod
        def information(cls, *args, **kwargs):
            say("  box info: %s" % (str(args[1])[:120] if len(args) > 1 else ""))

        @classmethod
        def critical(cls, *args, **kwargs):
            say("  box critical: %s" % (str(args[1])[:120] if len(args) > 1 else ""))

    errors = []
    failures = []
    announcements = []
    markers = []

    # The engine switch below would otherwise leave the user's preferences
    # changed; they are restored when the check finishes.
    import vt_prefs

    original_prefs = dict(vt_prefs.load())

    def _hook(exc_type, exc, value, tb):
        errors.append("".join(traceback.format_exception(exc_type, exc, value, tb)))

    previous_hook = sys.excepthook
    sys.excepthook = _hook

    app = QApplication.instance() or QApplication(sys.argv[:1])
    vid_trans_app.QMessageBox = _StubBox

    window = vid_trans_app.MainWindow("en")
    window.announce = lambda text, show_box=False, kind=None: (
        announcements.append(str(text)), say("  announce: %s" % str(text)[:100]))
    window.feedback = lambda *args, **kwargs: None
    window.video_path = video
    window.audio_path = ""
    window.path_label.setText(video)

    orig_transcribe_done = window._on_transcribe_done
    orig_translate_done = window._on_translate_done
    orig_failed = window.on_failed

    def wrap_transcribe(subtitles, detected, audio_path):
        say("  transcription: %d captions, detected=%s" % (len(subtitles), detected))
        if target in ("en", "ar") and target != detected:
            for index in range(window.target_combo.count()):
                if window.target_combo.itemData(index) == target:
                    window.target_combo.setCurrentIndex(index)
                    break
        markers.append("transcribe")
        return orig_transcribe_done(subtitles, detected, audio_path)

    def wrap_translate(subtitles):
        say("  translation: %d captions" % len(subtitles))
        markers.append("translate")
        return orig_translate_done(subtitles)

    def wrap_failed(message):
        failures.append(str(message))
        say("  FAILED: %s" % str(message)[:200])
        return orig_failed(message)

    window._on_transcribe_done = wrap_transcribe
    window._on_translate_done = wrap_translate
    window.on_failed = wrap_failed

    # The engine argument only chooses the transcription engine; the
    # translation engine always follows the saved preferences, exactly like
    # the automatic setting on the main screen.
    for combo, want in ((window.task_combo, "transcribe"),
                        (window.engine_combo, "auto")):
        for index in range(combo.count()):
            if combo.itemData(index) == want:
                combo.setCurrentIndex(index)
                break
    if engine != "auto":
        vt_prefs.save({"transcribe_engine": engine})

    def pump(predicate, seconds, what):
        deadline = time.time() + seconds
        while time.time() < deadline:
            app.processEvents()
            if predicate():
                return True
            time.sleep(0.05)
        say("  TIMEOUT waiting for %s" % what)
        return False

    started = time.time()
    say("  starting transcription")
    window.start_task()
    # The wait ends when the work finishes OR fails: a failure never sets the
    # marker, and hanging around for the full timeout would only hide it.
    pump(lambda: "transcribe" in markers or failures or errors,
         TRANSCRIBE_TIMEOUT, "transcription")
    done = "transcribe" in markers
    say("  transcription %s after %.1fs" % (done and "OK" or "FAIL",
                                            time.time() - started))

    if done and target in ("en", "ar") and window.subtitles:
        started = time.time()
        pump(lambda: "translate" in markers or failures or errors,
             TRANSLATE_TIMEOUT, "translation")
        say("  translation %s after %.1fs" % (
            "translate" in markers and "OK" or "FAIL", time.time() - started))

    rows = len(window.subtitles)
    say("  captions in transcript: %d" % rows)
    if rows:
        first = window.subtitles[0].content
        say("  first caption: %r" % first[:100])

    if errors:
        say("EXCEPTIONS:")
        for error in errors:
            say(error)
    if failures:
        say("FAILURES:")
        for failure in failures:
            say("  - %s" % failure)

    ok = done and not errors and not failures
    if target in ("en", "ar"):
        ok = ok and "translate" in markers
    try:
        vt_prefs.save(original_prefs)
    except Exception:  # noqa: BLE001 - restoring settings must not fail the run
        log.exception("the preferences could not be restored")
    sys.excepthook = previous_hook
    say("RESULT: %s" % ("OK" if ok else "FAIL"))
    return _finish(lines, 0 if ok else 1)


def _finish(lines, code) -> int:
    path = _report_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        try:
            print("report:", path)
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001 - the exit code still tells the truth
        log.exception("the e2e report could not be written")
    return code
