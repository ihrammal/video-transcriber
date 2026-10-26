"""Regression checks for audio support, shared wording and optional greetings."""
from datetime import timedelta
import wave

import pytest


def test_translation_table_is_shared():
    import vid_trans_app
    import vt_i18n
    assert vid_trans_app.TR is vt_i18n.TR
    for language in ("en", "ar"):
        assert vid_trans_app.tr(language, "btn_open") == vt_i18n.tr(language, "btn_open")


@pytest.mark.parametrize("language", ["en", "ar"])
def test_audio_selection_uses_localized_labels(qapp, profile, monkeypatch, language):
    import vid_trans_app as app
    window = app.MainWindow(language)
    seen = []
    def choose(*args):
        seen.append(args[3])
        return str(profile / "تسجيل.MP3"), ""
    monkeypatch.setattr(app.QFileDialog, "getOpenFileName", choose)
    window.select_video()
    assert "*.mp3" in seen[0] and "*.mp4" in seen[0]
    assert window._source_is_audio()
    assert "تسجيل.MP3" in window.path_label.accessibleName()
    window.deleteLater()


def test_saved_greeting_choices_skip_panels(qapp, profile, monkeypatch):
    import vt_a11y
    import vt_setup
    vt_a11y.update(show_welcome=False, show_farewell=False)
    monkeypatch.setattr(vt_setup, "_WelcomePanel", lambda *args: pytest.fail("Greeting should be skipped"))
    assert vt_setup.show_welcome_screen(qapp) in ("en", "ar")
    assert vt_setup.show_exit_screen(qapp, lambda: None) is False


def test_welcome_duration_is_capped(qapp, profile):
    import vt_setup
    panel = vt_setup._WelcomePanel("en", seconds=90)
    assert 0 < panel._seconds <= 3
    panel.deleteLater()


@pytest.mark.parametrize("language", ["en", "ar"])
def test_welcome_checkbox_saves_without_waiting_for_timeout(qapp, profile, language):
    import vt_a11y
    import vt_setup
    panel = vt_setup._WelcomePanel(language)
    panel.show_next_time.setChecked(False)
    assert vt_a11y.load()["show_welcome"] is False
    assert panel.show_next_time.accessibleName() == panel.show_next_time.text()
    # The delayed focus helper must not interrupt someone using the checkbox.
    panel.show()
    panel.show_next_time.setFocus()
    panel._land_on_continue()
    assert panel.focusWidget() is panel.show_next_time
    panel.accept()
    panel.deleteLater()


def test_farewell_checkbox_persists(qapp, profile, monkeypatch):
    import vt_a11y
    import vt_setup
    from PySide6.QtWidgets import QCheckBox, QDialog
    monkeypatch.setattr(vt_setup, "play_farewell_music", lambda: None)
    def dismiss(dialog):
        checkbox = dialog.findChild(QCheckBox)
        assert checkbox is not None
        checkbox.setChecked(False)
        dialog.accept()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog, "exec", dismiss)
    finished = []
    assert vt_setup.show_exit_screen(qapp, lambda: finished.append(True))
    assert vt_a11y.load()["show_farewell"] is False
    assert finished == [True]


def test_clean_exit_has_no_extra_confirmation(qapp, profile, monkeypatch):
    import vid_trans_app as app
    from PySide6.QtGui import QCloseEvent
    window = app.MainWindow("en")
    monkeypatch.setattr(app.QMessageBox, "exec", lambda box: pytest.fail("Clean exit must not ask for confirmation"))
    monkeypatch.setattr(app.vt_setup, "show_exit_screen", lambda *args: False)
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    window.deleteLater()


def test_model_choices_and_message_options_persist(qapp, profile):
    import vt_prefs
    import vt_a11y
    from vt_settings import SettingsDialog
    dialog = SettingsDialog()
    dialog._model_radios["turbo"].setChecked(True)
    dialog._cloud_models["groq"].setCurrentText("whisper-large-v3-turbo")
    dialog.accessibility_checks["show_welcome"].setChecked(False)
    dialog.accessibility_checks["show_farewell"].setChecked(False)
    dialog._on_save()
    assert vt_prefs.load()["whisper_model"] == "turbo"
    assert vt_prefs.load()["groq_model"] == "whisper-large-v3-turbo"
    assert vt_a11y.load()["show_welcome"] is False
    assert vt_a11y.load()["show_farewell"] is False


def test_first_launch_honors_installed_model(profile, monkeypatch):
    import vt_install
    import vt_prefs
    (profile / "installed-model.ini").write_text("[transcription]\nmodel=tiny\n", encoding="utf-8")
    monkeypatch.setattr(vt_install, "app_dir", lambda: str(profile))
    assert vt_prefs.load()["whisper_model"] == "tiny"
    vt_prefs.save({"whisper_model": "small"})
    assert vt_prefs.load()["whisper_model"] == "small"


def test_api_does_not_invent_subtitle_timing():
    import vt_api
    with pytest.raises(vt_api.ApiFailure) as failure:
        vt_api._segments_from_openai({"text": "A long transcript without timestamps"}, "en")
    assert failure.value.hint_key == "err_api_timestamps"


def test_status_announces_changes_once_and_preserves_editing_focus(qapp, profile, monkeypatch):
    import vid_trans_app as app
    window = app.MainWindow("en")
    window.show()
    window.editor.setFocus()
    qapp.processEvents()
    events = []
    monkeypatch.setattr(app.QAccessible, "updateAccessibility", lambda event: events.append(event.message()))
    window.announce("Stage one")
    window.announce("Stage one")
    window.announce("Stage two")
    assert events == ["Stage one", "Stage two"]
    assert window.editor.hasFocus()
    assert "Stage two" in window.status_label.text()
    monkeypatch.setattr(app.QMessageBox, "information", lambda *args: None)
    window.announce("Finished", show_box=True)
    assert events == ["Stage one", "Stage two"]
    window.deleteLater()


@pytest.mark.parametrize("language", ["en", "ar"])
def test_online_translation_is_distinct_from_offline_transcription(qapp, profile, language):
    from vt_settings import SettingsDialog
    from vt_i18n import tr
    dialog = SettingsDialog(lang=language)
    assert dialog._translate_radios["local"].text() == tr(language, "lbl_translation_free")
    assert dialog._translate_radios["local"].text() != dialog._engine_radios["local"].text()
    assert "Google" in dialog._translate_radios["local"].text()
    dialog.deleteLater()


def test_render_logger_honors_cancellation():
    from vt_render import MoviePyProgressLogger
    logger = MoviePyProgressLogger(lambda value: None, lambda: True)
    with pytest.raises(InterruptedError):
        list(logger.iter_bar(frame=range(3)))


@pytest.mark.parametrize("failures_before_success", [2, 3])
def test_output_verification_retries_but_rejects_unreadable_files(tmp_path, monkeypatch, failures_before_success):
    import vt_workers
    output = tmp_path / "result.mp4"
    output.write_bytes(b"test output")
    worker = vt_workers.RenderThread("source.mp4", [], str(output), str(tmp_path))
    attempts = []
    def probe(path):
        attempts.append(path)
        if len(attempts) <= failures_before_success:
            raise OSError("Temporary file access failure")
        return True, 2.0, "valid streams"
    monkeypatch.setattr(vt_workers, "probe_video", probe)
    monkeypatch.setattr(vt_workers.time, "sleep", lambda seconds: None)
    if failures_before_success == 2:
        assert worker._verify_output() == (len(b"test output"), 2.0)
    else:
        with pytest.raises(vt_workers.WorkerError):
            worker._verify_output()


def test_audio_render_retains_audio_and_wraps_arabic(qapp, tmp_path):
    import srt
    from vt_workers import RenderThread, probe_video
    source = tmp_path / "audio.wav"
    with wave.open(str(source), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\0\0" * 8000)
    target = tmp_path / "captioned.mp4"
    subtitles = [srt.Subtitle(1, timedelta(0), timedelta(seconds=.5), "مرحبًا بكم في عالم المعرفة — Welcome")]
    worker = RenderThread(str(source), subtitles, str(target), str(tmp_path))
    failures, completed = [], []
    worker.failed.connect(failures.append)
    worker.completed.connect(completed.append)
    worker.run()
    assert failures == []
    assert completed == [str(target)]
    audio, duration, _ = probe_video(str(target))
    assert audio and .4 <= duration <= .65
