"""The Speech and Translation Settings dialog (Preferences)."""

from __future__ import annotations

import pytest


@pytest.fixture()
def dialog(qapp, profile, fake_secrets):
    import vt_settings

    dlg = vt_settings.SettingsDialog(lang="en")
    yield dlg
    dlg.deleteLater()
    qapp.processEvents()


def test_dialog_builds_every_section(dialog):
    assert dialog.engine_box.title()
    assert dialog.model_box.title()
    assert dialog.keys_box.title()
    assert dialog.translate_box.title()
    assert set(dialog._engine_radios) == {"local", "openai", "groq", "gemini"}
    assert set(dialog._key_edits) == {"openai", "groq", "gemini"}


def test_key_rows_have_show_test_and_get_buttons(dialog):
    for engine in ("openai", "groq", "gemini"):
        edit = dialog._key_edits[engine]
        assert edit.echoMode() == edit.EchoMode.Password
        show, test = dialog._key_buttons[engine]
        get = dialog._get_buttons[engine]
        assert show.text() == "Show key"
        assert test.text() == "Test key"
        assert get.text() == "Get API key"
        assert test.accessibleDescription()
        assert get.accessibleDescription()


def test_every_provider_has_a_key_page():
    import vt_settings

    assert set(vt_settings.KEY_URLS) == {"openai", "groq", "gemini"}
    for url in vt_settings.KEY_URLS.values():
        assert url.startswith("https://")


def test_collect_returns_the_selection(dialog):
    data = dialog.collect()
    for field in ("transcribe_engine", "whisper_model", "translate_engine"):
        assert field in data
    for engine in ("openai", "groq", "gemini"):
        assert engine + "_api_key" in data


def test_testing_without_a_key_warns_instead_of_raising(dialog, monkeypatch):
    import vt_settings

    warnings = []
    monkeypatch.setattr(
        vt_settings.QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: warnings.append(a)),
    )
    dialog._on_test_key("openai")
    assert warnings, "a missing key must be reported, not crash"


def test_arabic_dialog_is_translated(qapp, profile, fake_secrets):
    import vt_settings

    dlg = vt_settings.SettingsDialog(lang="ar")
    try:
        assert dlg.windowTitle()
        assert dlg.save_button.text() == "حفظ"
        assert dlg._get_buttons["openai"].text() == "الحصول على مفتاح API"
    finally:
        dlg.deleteLater()


def _visible_provider(dialog):
    return next(
        name for name, holder in dialog._key_holders.items() if not holder.isHidden()
    )


def testChoosingEngineShowsThatProvidersKeyRow(dialog):
    """Choosing Gemini/OpenAI/Groq brings that provider's key row forward."""
    dialog._engine_radios["gemini"].setChecked(True)
    assert dialog._provider_combo.currentData() == "gemini"
    assert _visible_provider(dialog) == "gemini"
    # every button of the chosen provider lives inside the visible row
    assert dialog._get_buttons["gemini"].parent() is dialog._key_holders["gemini"]
    assert dialog._key_buttons["gemini"][0].parent() is dialog._key_holders["gemini"]
    assert dialog._key_buttons["gemini"][1].parent() is dialog._key_holders["gemini"]
    assert dialog._get_buttons["openai"].parent() is dialog._key_holders["openai"]
    assert dialog._key_holders["openai"].isHidden()
    assert dialog._key_holders["groq"].isHidden()

    dialog._engine_radios["openai"].setChecked(True)
    assert _visible_provider(dialog) == "openai"
    assert not dialog._key_holders["openai"].isHidden()
    assert dialog._key_holders["gemini"].isHidden()

    dialog._engine_radios["groq"].setChecked(True)
    assert _visible_provider(dialog) == "groq"


def testLocalEngineKeepsTheKeySectionUsable(dialog):
    """Local transcription must not lock the keys away (translate may be cloud)."""
    dialog._engine_radios["gemini"].setChecked(True)
    assert _visible_provider(dialog) == "gemini"
    dialog._engine_radios["local"].setChecked(True)
    assert dialog.keys_box.isEnabled()
    assert dialog.model_box.isEnabled()
    # the translation engine still drives the key row
    dialog._translate_radios["gemini"].setChecked(True)
    assert _visible_provider(dialog) == "gemini"
    assert dialog.keys_box.isEnabled()
