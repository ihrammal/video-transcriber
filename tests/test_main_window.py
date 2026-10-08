"""The main window: menus, shortcuts, controls, language switch, sounds."""

from __future__ import annotations

import pytest


@pytest.fixture()
def window(qapp, profile):
    import vid_trans_app

    win = vid_trans_app.MainWindow("en")
    yield win
    win.deleteLater()
    qapp.processEvents()


def _shortcut_map(window):
    seen = {}
    for menu_action in window.menuBar().actions():
        menu = menu_action.menu()
        if menu is None:
            continue
        for action in menu.actions():
            if action.isSeparator() or action.menu() is not None:
                continue
            key = action.shortcut().toString()
            if key:
                seen.setdefault(key, []).append(action.text())
    return seen


def _action_by_shortcut(window, key):
    for menu_action in window.menuBar().actions():
        menu = menu_action.menu()
        if menu is None:
            continue
        for action in menu.actions():
            if action.isSeparator() or action.menu() is not None:
                continue
            if action.shortcut().toString() == key:
                return action
    return None


def test_the_seven_menus_are_there(window):
    titles = [a.text().replace("&", "") for a in window.menuBar().actions()]
    for name in ("File", "Edit", "Settings", "Accessibility", "Tools", "Models", "Help"):
        assert name in titles, titles


def test_every_action_has_a_shortcut(window):
    # The two Help entries that hand the page over to the default browser
    # deliberately carry no keystroke, so they stay out of the shortcut
    # lists (in the program and in the HTML documents) on purpose.
    external = {
        id(act)
        for act, key in window._action_map
        if key in ("act_guide_file", "act_shortcuts_file")
    }
    missing = []
    for menu_action in window.menuBar().actions():
        menu = menu_action.menu()
        if menu is None:
            continue
        for action in menu.actions():
            if action.isSeparator() or action.menu() is not None:
                continue
            if action.shortcut().isEmpty() and id(action) not in external:
                missing.append(action.text())
    assert not missing, missing


def test_no_shortcut_is_bound_twice(window):
    shared = {k: v for k, v in _shortcut_map(window).items() if len(v) > 1}
    assert not shared, shared


def test_main_screen_widgets_exist(window):
    for name in (
        "open_button", "task_combo", "language_combo", "target_combo",
        "engine_combo", "start_button", "cancel_button", "status_label",
        "progress_bar", "editor", "save_button", "copy_button",
        "export_button", "timestamps_check", "path_label", "drop_hint",
    ):
        assert getattr(window, name) is not None, name


def test_the_transcript_editor_is_a_plain_text_area(window):
    from PyQt6.QtWidgets import QPlainTextEdit

    assert isinstance(window.editor, QPlainTextEdit)
    assert window.editor.isReadOnly() is False
    assert window.editor.tabChangesFocus()  # Tab must not trap keyboard users
    assert window.editor.accessibleName()
    assert window.editor.placeholderText()


def test_export_and_timestamps_have_real_shortcuts(window):
    export = _action_by_shortcut(window, "Ctrl+E")
    assert export is not None and export.text() == window.t("act_export")
    stamps = _action_by_shortcut(window, "Ctrl+Shift+T")
    assert stamps is not None and stamps.isCheckable()
    assert stamps.text() == window.t("act_timestamps")
    assert window.timestamps_check.toolTip().endswith("Ctrl+Shift+T")


def test_show_timestamps_is_remembered_and_stays_in_sync(window, profile):
    import vt_prefs

    assert window.timestamps_check.isChecked() is True  # the default
    window.timestamps_check.setChecked(False)
    assert window.show_timestamps is False
    assert window._timestamps_act.isChecked() is False
    saved = vt_prefs.normalized(vt_prefs.load())
    assert saved["show_timestamps"] == "false"

    window._timestamps_act.trigger()  # the menu item flips the check box
    assert window.timestamps_check.isChecked() is True
    assert window.show_timestamps is True
    saved = vt_prefs.normalized(vt_prefs.load())
    assert saved["show_timestamps"] == "true"
    vt_prefs.save({"show_timestamps": "true"})


def test_timestamps_change_keeps_edited_text(window):
    import vt_prefs

    window.show_timestamps = True
    window.editor.setPlainText(
        "[00:00:01,000 --> 00:00:03,000] first line\nsecond line"
    )
    window.timestamps_check.setChecked(False)
    # the second line belongs to the first caption and is folded into it
    assert window.editor.toPlainText() == "first line / second line"
    window.timestamps_check.setChecked(True)
    assert window.editor.toPlainText().startswith(
        "[00:00:01,000 --> 00:00:03,000] first line"
    )

    # plain lines typed while timestamps are off become their own captions
    window.timestamps_check.setChecked(False)
    window.editor.setPlainText("alpha\nbeta")
    window.timestamps_check.setChecked(True)
    lines = window.editor.toPlainText().splitlines()
    assert len(lines) == 2, lines
    assert lines[0].startswith("[00:00:") and lines[0].endswith("alpha")
    assert lines[1].startswith("[00:00:") and lines[1].endswith("beta")

    window.editor.clear()
    window.subtitles = []
    window.show_timestamps = True
    vt_prefs.save({"show_timestamps": "true"})


def test_combo_contents(window):
    tasks = [window.task_combo.itemData(i) for i in range(window.task_combo.count())]
    assert tasks == ["transcribe", "translate"]
    targets = [window.target_combo.itemData(i) for i in range(window.target_combo.count())]
    assert targets[0] == "none"
    assert "bilingual" in targets and "en" in targets and "ar" in targets
    engines = [window.engine_combo.itemData(i) for i in range(window.engine_combo.count())]
    assert engines[0] == "auto"
    assert set(engines) == {"auto", "local", "openai", "groq", "gemini"}


def test_tab_order_reaches_every_control(window):
    from PyQt6.QtCore import Qt

    expected = [
        window.open_button, window.task_combo, window.language_combo,
        window.target_combo, window.engine_combo, window.start_button,
        window.cancel_button, window.status_label, window.progress_bar,
        window.editor, window.save_button, window.copy_button,
        window.export_button, window.timestamps_check,
    ]
    for widget in expected:
        assert widget.focusPolicy() != Qt.FocusPolicy.NoFocus, widget


def test_switching_the_language_retranslates(window, qapp):
    original = window.windowTitle()
    window.interface_combo.setCurrentIndex(1)  # Arabic
    qapp.processEvents()
    assert window.current_lang == "ar"
    assert window.windowTitle() != original
    assert window.windowTitle()  # a real Arabic title, not an empty string
    window.interface_combo.setCurrentIndex(0)
    qapp.processEvents()
    assert window.current_lang == "en"
    assert window.windowTitle() == original


def test_engine_choice_is_remembered(window, profile):
    import vt_prefs

    index = window.engine_combo.findData("gemini")
    assert index >= 0
    window.engine_combo.setCurrentIndex(index)
    saved = vt_prefs.normalized(vt_prefs.load())
    assert saved["transcribe_engine"] == "gemini"
    assert saved["translate_engine"] == "gemini"
    assert "gemini" in window.status_label.text().lower()


def test_automatic_engine_falls_back_to_the_local_one(window, profile, fake_secrets):
    """A saved cloud engine without a key must not block a run."""
    import vt_prefs

    vt_prefs.save({"transcribe_engine": "openai", "openai_api_key": ""})
    window.engine_combo.setCurrentIndex(0)  # Automatic
    choice = window._engine_choice("transcribe")
    assert choice is not None
    assert choice[0] == "local"
    assert "OpenAI" in window.status_label.text()


def test_sounds_can_be_switched_off(monkeypatch, window):
    import vt_a11y
    import winsound

    played = []
    monkeypatch.setattr(
        winsound, "PlaySound", lambda *a, **k: played.append(a), raising=False
    )

    vt_a11y.update(sounds=False)
    window.feedback("ok")
    assert played == []

    vt_a11y.update(sounds=True)
    window.feedback("ok")
    assert played, "the confirmation tone should play when the flag is on"
    vt_a11y.save(vt_a11y.DEFAULTS)


def test_output_key_follows_the_target_combo(window):
    window.target_combo.setCurrentIndex(0)
    assert window._output_key() == "out_orig"
    bilingual = window.target_combo.findData("bilingual")
    window.target_combo.setCurrentIndex(bilingual)
    assert window._output_key() == "out_both"


def test_high_contrast_stylesheet(window, qapp):
    window.high_contrast_check.setChecked(True)
    qapp.processEvents()
    assert window.high_contrast is True
    assert "#000000" in window.styleSheet()
    window.high_contrast_check.setChecked(False)
    qapp.processEvents()
    assert window.high_contrast is False


def test_license_text_loads_in_both_languages(window):
    import vt_bootstrap

    for name in ("agreement_en.txt", "agreement_ar.txt"):
        path = vt_bootstrap.resource_path("resources", name)
        with open(path, encoding="utf-8") as handle:
            assert len(handle.read()) > 500, name


def test_model_status_is_plain_text(window, monkeypatch):
    import vt_install
    import vid_trans_app

    boxes = []
    monkeypatch.setattr(
        vid_trans_app.QMessageBox,
        "information",
        staticmethod(lambda *a, **k: boxes.append((a[1], a[2]))),
    )
    monkeypatch.setattr(vt_install, "model_is_cached", lambda name="base": True)
    window.show_model_status()
    assert boxes, "a message box with the model status is expected"
    title, body = boxes[0]
    assert "base" in body and "tiny" in body and "small" in body


def test_accessibility_menu_opens_the_settings_dialog(window, monkeypatch):
    import vt_a11y

    calls = []
    monkeypatch.setattr(
        vt_a11y, "open_dialog", lambda parent=None, lang="en": calls.append((lang, parent))
    )
    window.open_accessibility()
    assert calls and calls[0][0] == "en"


def test_copy_results_with_an_empty_transcript_is_reported(window, monkeypatch):
    import vid_trans_app

    warnings = []
    monkeypatch.setattr(
        vid_trans_app.QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: warnings.append(a)),
    )
    window.copy_results()
    assert warnings, "an empty transcript must be reported, not crash"
