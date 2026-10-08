"""Preferences and secure key storage."""

from __future__ import annotations

import json

import vt_prefs


def test_defaults_roundtrip(profile):
    data = vt_prefs.normalized(vt_prefs.load())
    assert data["transcribe_engine"] == "local"
    assert data["whisper_model"] in vt_prefs.WHISPER_MODELS
    assert data["openai_api_key"] == ""


def test_save_and_load_keeps_non_secret_fields(profile):
    assert vt_prefs.save({"whisper_model": "small", "transcribe_engine": "groq"})
    data = vt_prefs.load()
    assert data["whisper_model"] == "small"
    assert data["transcribe_engine"] == "groq"


def test_api_keys_never_stay_in_the_file(profile, fake_secrets):
    assert vt_prefs.save({"openai_api_key": "sk-test-1234567890"})
    on_disk = json.load(open(vt_prefs.prefs_path(), encoding="utf-8"))
    assert on_disk.get("openai_api_key", "") == ""
    # ... but the application still gets it back
    assert vt_prefs.key_for("openai") == "sk-test-1234567890"
    assert fake_secrets["openai_api_key"] == "sk-test-1234567890"


def test_clearing_a_key_forgets_it(profile, fake_secrets):
    vt_prefs.save({"groq_api_key": "gsk_1234567890"})
    assert vt_prefs.key_for("groq") == "gsk_1234567890"
    vt_prefs.save({"groq_api_key": ""})
    assert vt_prefs.key_for("groq") == ""
    assert "groq_api_key" not in fake_secrets


def test_plain_text_key_is_migrated_on_load(profile, fake_secrets):
    # A profile written by an older version: key straight in the JSON file.
    path = vt_prefs.prefs_path()
    import os

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({**vt_prefs.DEFAULTS, "gemini_api_key": "AIza-old-key"}, handle)

    assert vt_prefs.key_for("gemini") == "AIza-old-key"
    on_disk = json.load(open(path, encoding="utf-8"))
    assert on_disk.get("gemini_api_key", "") == ""
    assert fake_secrets.get("gemini_api_key") == "AIza-old-key"
    # a second load agrees with the first one
    assert vt_prefs.key_for("gemini") == "AIza-old-key"


def test_without_credential_manager_the_key_stays_in_the_file(profile, monkeypatch):
    import vt_secrets

    monkeypatch.setattr(vt_secrets, "is_available", lambda: False)
    vt_prefs.save({"openai_api_key": "sk-plain-fallback"})
    on_disk = json.load(open(vt_prefs.prefs_path(), encoding="utf-8"))
    assert on_disk["openai_api_key"] == "sk-plain-fallback"
    assert vt_prefs.key_for("openai") == "sk-plain-fallback"


def test_validate_reports_missing_and_silly_keys():
    problems = vt_prefs.validate({**vt_prefs.DEFAULTS, "transcribe_engine": "openai"})
    assert problems and "openai_api_key" in problems[0][0]

    problems = vt_prefs.validate(
        {**vt_prefs.DEFAULTS, "transcribe_engine": "openai", "openai_api_key": "abc"}
    )
    assert problems


def test_mask_hides_the_middle():
    masked = vt_prefs.mask("sk-abcdefghijklmnop")
    assert masked.startswith("sk-a") and masked.endswith("mnop")
    assert "efghijkl" not in masked
