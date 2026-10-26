"""Recovery, large text, and queue lifecycle regressions."""
import json
from datetime import timedelta

import srt
from PySide6.QtCore import QThread, Signal
from PySide6.QtTest import QTest


def test_unfinished_transcript_survives_restart(qapp, profile, monkeypatch):
    import vid_trans_app
    import vt_session
    first = vid_trans_app.MainWindow("ar")
    first.video_path = str(profile / "تسجيل.mp3")
    first.subtitles = [srt.Subtitle(1, timedelta(seconds=2), timedelta(seconds=4), "النص الأصلي")]
    first.editor.setPlainText("[00:00:02,000 --> 00:00:04,000] تعديل غير محفوظ — edited")
    first.save_recovery()
    recovered = json.loads(open(vt_session.path(), encoding="utf-8").read())
    assert "api_key" not in str(recovered)
    second = vid_trans_app.MainWindow("ar")
    monkeypatch.setattr(vid_trans_app.QMessageBox, "question", lambda *args, **kwargs: vid_trans_app.QMessageBox.StandardButton.Yes)
    second.offer_recovery()
    assert second.editor.toPlainText() == first.editor.toPlainText()
    assert second.video_path == first.video_path
    assert second.subtitles[0].start == timedelta(seconds=2)
    second._mark_exported()
    assert vt_session.load() is None
    first.deleteLater()
    second.deleteLater()


def test_language_switch_preserves_edits(qapp, profile):
    from vid_trans_app import MainWindow
    window = MainWindow("en")
    window.subtitles = [srt.Subtitle(1, timedelta(0), timedelta(seconds=2), "Original")]
    window.populate_editor()
    window.editor.setPlainText("Edited text النص المعدّل")
    window.interface_combo.setCurrentIndex(1)
    assert window.editor.toPlainText() == "Edited text النص المعدّل"
    window.deleteLater()


def test_disabling_recovery_clears_private_copy(qapp, profile):
    import vt_session
    from vid_trans_app import MainWindow
    from vt_settings import SettingsDialog
    window = MainWindow("en")
    window.editor.setPlainText("Private unfinished transcript")
    window.save_recovery()
    assert vt_session.load() is not None
    dialog = SettingsDialog(parent=window)
    dialog.recovery_choice.setChecked(False)
    dialog._on_save()
    assert vt_session.load() is None
    window.editor.setPlainText("Another edit")
    window.save_recovery()
    assert vt_session.load() is None
    window.deleteLater()


def test_close_retains_an_active_worker(qapp, profile, monkeypatch):
    import vid_trans_app
    from PySide6.QtGui import QCloseEvent
    class Worker:
        interrupted = False
        def isRunning(self):
            return True
        def requestInterruption(self):
            self.interrupted = True
        def wait(self, milliseconds):
            return False
    window = vid_trans_app.MainWindow("en")
    window.announce = lambda *args, **kwargs: None
    worker = Worker()
    window.worker_thread = worker
    monkeypatch.setattr(vid_trans_app.QMessageBox, "exec", lambda box: 0)
    monkeypatch.setattr(vid_trans_app.QMessageBox, "clickedButton", lambda box: box.buttons()[0])
    event = QCloseEvent()
    window.closeEvent(event)
    assert worker.interrupted
    assert not event.isAccepted()
    assert window.worker_thread is worker
    window.worker_thread = None
    window.deleteLater()


def test_large_text_scrolls_and_is_remembered(qapp, profile):
    from PySide6.QtWidgets import QScrollArea
    from vid_trans_app import MainWindow
    from vt_settings import SettingsDialog
    import vt_prefs
    window = MainWindow("en")
    dialog = SettingsDialog(parent=window)
    dialog.text_size_choice.setCurrentIndex(dialog.text_size_choice.findData("200"))
    dialog._on_save()
    assert vt_prefs.load()["text_size"] == "200"
    window.resize(640, 480)
    window.show()
    qapp.processEvents()
    assert isinstance(window.centralWidget(), QScrollArea)
    assert window.editor.font().pointSizeF() >= 22
    assert window.centralWidget().verticalScrollBar().maximum() > 0
    window.deleteLater()


class FakeTranscriber(QThread):
    completed = Signal(list, str, str)
    failed = Signal(str)
    def __init__(self, source, audio, language, work, **kwargs):
        super().__init__()
        self.source = source
    def run(self):
        if "bad" in self.source:
            self.failed.emit("Unreadable recording")
        else:
            self.completed.emit([srt.Subtitle(1, timedelta(0), timedelta(seconds=2), "Hello مرحبًا")], "ar", "")


def wait_for_queue(dialog):
    for _ in range(300):
        QTest.qWait(10)
        if dialog.worker is None and dialog.start_button.isEnabled():
            return
    raise AssertionError("Queue did not finish")


def test_batch_exports_continues_after_failure_and_never_overwrites(qapp, profile, monkeypatch):
    import vt_batch
    from vid_trans_app import MainWindow
    monkeypatch.setattr(vt_batch, "TranscriptionThread", FakeTranscriber)
    parent = MainWindow("en")
    parent.announce = lambda *args, **kwargs: None
    good, bad = profile / "good.mp3", profile / "bad.mp3"
    good.touch()
    bad.touch()
    dialog = vt_batch.BatchDialog(parent)
    dialog.add_paths([str(good), str(good), str(bad)])
    assert len(dialog.paths) == 2
    dialog.output_folder = str(profile)
    dialog.start_queue()
    wait_for_queue(dialog)
    assert len(dialog.report) == 2
    assert dialog.report[0]["saved"] is True
    assert dialog.report[1]["saved"] is False
    destination = dialog.destination
    text = destination / dialog.report[0]["text"]
    subtitle = destination / dialog.report[0]["subtitles"]
    assert text.read_text(encoding="utf-8") == "Hello مرحبًا\n"
    assert list(srt.parse(subtitle.read_text(encoding="utf-8-sig")))[0].end == timedelta(seconds=2)
    dialog.start_queue()
    wait_for_queue(dialog)
    assert dialog.destination != destination
    assert text.read_text(encoding="utf-8") == "Hello مرحبًا\n"
    dialog.deleteLater()
    parent.deleteLater()


def test_closing_active_queue_stops_without_destroying_worker(qapp, profile, monkeypatch):
    import vt_batch
    from vid_trans_app import MainWindow
    started = []
    class SlowTranscriber(FakeTranscriber):
        def run(self):
            started.append(self.source)
            for _ in range(100):
                if self.isInterruptionRequested():
                    self.failed.emit("Cancelled")
                    return
                self.msleep(5)
            super().run()
    monkeypatch.setattr(vt_batch, "TranscriptionThread", SlowTranscriber)
    parent = MainWindow("en")
    parent.announce = lambda *args, **kwargs: None
    files = [profile / "first.mp3", profile / "second.mp3"]
    for file in files:
        file.touch()
    dialog = vt_batch.BatchDialog(parent)
    dialog.add_paths(list(map(str, files)))
    dialog.output_folder = str(profile)
    dialog.start_queue()
    QTest.qWait(20)
    dialog.reject()
    assert dialog.worker is not None
    wait_for_queue(dialog)
    assert started == [str(files[0])]
    assert dialog.states[1] == dialog.t("batch_cancelled")
    dialog.deleteLater()
    parent.deleteLater()
