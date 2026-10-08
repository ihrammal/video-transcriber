"""vt_prefs.py -- user preferences: transcription / translation engine, model, API keys.

The file lives next to the rest of the per-user data (``%LOCALAPPDATA%\\Accessible Video Transcriber``)
so it survives upgrades and is deleted by the uninstaller.  Everything here is
standard library only: the settings screen must be able to open even when the
optional speech or network packages are missing.

Storage format (``prefs.json``)::

    {
      "transcribe_engine": "local",      local | openai | groq | gemini
      "translate_engine":  "local",      local | openai | groq | gemini
      "whisper_model":     "base",       tiny | base | small
      "openai_api_key":    "",
      "groq_api_key":      "",
      "gemini_api_key":    "",
      "openai_model":      "whisper-1",
      "groq_model":        "whisper-large-v3",
      "gemini_model":      "gemini-2.5-flash",
      "openai_translate_model": "gpt-4o-mini",
      "groq_translate_model":   "llama-3.1-8b-instant",
      "gemini_translate_model": "gemini-2.5-flash",
      "show_timestamps":        "true"        # "true" | "false"
    }

Anything unreadable falls back to the defaults, so a corrupt or half written
file can never stop the application from starting.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile

log = logging.getLogger("vidtrans.prefs")

ENGINES = ("local", "openai", "groq", "gemini")
API_ENGINES = ("openai", "groq", "gemini")
WHISPER_MODELS = ("tiny", "base", "small")

DEFAULTS = {
    "transcribe_engine": "local",
    "translate_engine": "local",
    "whisper_model": "base",
    "openai_api_key": "",
    "groq_api_key": "",
    "gemini_api_key": "",
    "openai_model": "whisper-1",
    "groq_model": "whisper-large-v3",
    "gemini_model": "gemini-2.5-flash",
    "openai_translate_model": "gpt-4o-mini",
    "groq_translate_model": "llama-3.1-8b-instant",
    "gemini_translate_model": "gemini-2.5-flash",
    "show_timestamps": "true",
}

ENGINE_LABELS = {
    "local": "Local Whisper (free, offline)",
    "openai": "OpenAI API",
    "groq": "Groq API",
    "gemini": "Google Gemini API",
}

# Short names used inside sentences: "The {engine} key does not look valid".
SHORT_LABELS = {
    "openai": "OpenAI",
    "groq": "Groq",
    "gemini": "Google Gemini",
}


def prefs_dir() -> str:
    try:
        import vt_bootstrap

        return vt_bootstrap.app_data_dir()
    except Exception:
        return tempfile.gettempdir()


def prefs_path() -> str:
    return os.path.join(prefs_dir(), "prefs.json")


SECRET_FIELDS = tuple(engine + "_api_key" for engine in API_ENGINES)


def _secret_read(field: str) -> str:
    try:
        import vt_secrets

        return vt_secrets.retrieve(field)
    except Exception:  # noqa: BLE001 - secrets are optional
        return ""


def _secret_write(field: str, value: str) -> bool:
    try:
        import vt_secrets

        return bool(vt_secrets.store(field, value))
    except Exception:  # noqa: BLE001 - fall back to the plain text file
        log.warning("the key could not be moved to Credential Manager")
        return False


def _migrate_plaintext_keys(data: dict) -> dict:
    """Move any key left in prefs.json into Credential Manager.

    Older versions (and a machine where Credential Manager was unavailable)
    kept the key in the file.  Once it can be stored securely the file copy is
    removed, so a single call to this function brings an old profile up to
    date.
    """
    rewrite = False
    migrated = []
    for field in SECRET_FIELDS:
        stored = _secret_read(field)
        plain = str(data.get(field) or "")
        if stored:
            # The secure value always wins; any plain-text copy left in
            # prefs.json is removed from the file right now.
            data[field] = stored
            if plain:
                migrated.append(field)
                rewrite = True
            continue
        if plain and _secret_write(field, plain):
            # The key now lives in Credential Manager; keep returning it from
            # this load, while the file itself gets an empty value below.
            data[field] = _secret_read(field) or plain
            migrated.append(field)
            rewrite = True
    if rewrite:
        file_copy = dict(data)
        for field in migrated:
            file_copy[field] = ""
        _write_file(file_copy)
    return data


def _write_file(data: dict) -> bool:
    """Persist ``data`` as JSON, atomically, and return True on success."""
    path = prefs_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception as exc:  # noqa: BLE001 - reported to the caller, never raised
        log.error("preferences could not be saved: %s", exc)
        return False


def load() -> dict:
    """Return the preferences, merging the stored file over the defaults."""
    data = dict(DEFAULTS)
    path = prefs_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            stored = json.load(handle)
    except FileNotFoundError:
        return data
    except Exception as exc:  # noqa: BLE001 - a broken file must never crash the app
        log.warning("preferences could not be read (%s); using the defaults", exc)
        return data
    if not isinstance(stored, dict):
        log.warning("preferences were not a JSON object; using the defaults")
        return data
    for key, value in stored.items():
        if key in DEFAULTS and isinstance(value, str):
            data[key] = value
    for field in SECRET_FIELDS:
        secret = _secret_read(field)
        if secret:
            data[field] = secret
    return _migrate_plaintext_keys(data)


def save(data: dict) -> bool:
    """Write ``data`` (partial or complete) and return True on success.

    Every API key the caller sends is handed to the Windows Credential Manager
    and stripped from the JSON file; only when Credential Manager is
    unavailable does the key stay in the file (the previous behaviour).
    """
    merged = load()
    for key, value in (data or {}).items():
        if key in DEFAULTS and isinstance(value, str):
            merged[key] = value
    for field in SECRET_FIELDS:
        if field not in (data or {}):
            continue  # untouched: leave whatever is stored alone
        if _secret_write(field, str(merged.get(field, ""))):
            merged[field] = ""
        # else: keep the value in the file, Credential Manager unavailable
    return _write_file(merged)


def _clean(engine: str) -> str:
    engine = str(engine or "").strip().lower()
    return engine if engine in ENGINES else "local"


def normalized(data: dict) -> dict:
    """``data`` with every value forced back into its allowed range."""
    out = dict(DEFAULTS)
    for key in DEFAULTS:
        value = (data or {}).get(key, DEFAULTS[key])
        if isinstance(value, str):
            out[key] = value
    out["transcribe_engine"] = _clean(out["transcribe_engine"])
    out["translate_engine"] = _clean(out["translate_engine"])
    model = str(out["whisper_model"] or "").strip().lower()
    out["whisper_model"] = model if model in WHISPER_MODELS else "base"
    for key in ("openai_api_key", "groq_api_key", "gemini_api_key"):
        out[key] = str(out[key] or "").strip()
    for key in DEFAULTS:
        if key.endswith("_model"):
            out[key] = str(out[key] or "").strip() or DEFAULTS[key]
    return out


def key_for(engine: str, data: dict = None) -> str:
    data = normalized(load() if data is None else data)
    engine = _clean(engine)
    if engine == "local":
        return ""
    return data.get(engine + "_api_key", "")


def needs_key(engine: str) -> bool:
    return _clean(engine) in API_ENGINES


def validate(data: dict, lang: str = "en") -> list:
    """Return a list of ``(field, message)`` problems; empty when usable.

    Missing keys and malformed values are reported instead of raising, so the
    settings screen can show an alert dialog and offer to fall back to the free
    local engine.
    """
    from vt_i18n import tr

    problems = []
    data = normalized(data)
    for engine in (data["transcribe_engine"], data["translate_engine"]):
        if not needs_key(engine):
            continue
        key = data.get(engine + "_api_key", "")
        if not key:
            problems.append(
                (
                    engine + "_api_key",
                    tr(lang, "err_key_missing", engine=ENGINE_LABELS.get(engine, engine)),
                )
            )
        elif len(key) < 8 or (" " in key and not key.startswith("sk-")):
            problems.append(
                (
                    engine + "_api_key",
                    tr(lang, "err_key_invalid", engine=SHORT_LABELS.get(engine, engine)),
                )
            )
    if data["whisper_model"] not in WHISPER_MODELS:
        problems.append(("whisper_model", tr(lang, "err_model_invalid")))
    if data["transcribe_engine"] != data["translate_engine"]:
        # not an error: engines are chosen per task, only reported for clarity
        pass
    return problems


def mask(value: str) -> str:
    """Show enough of a key to recognise it without exposing it."""
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (min(12, len(value) - 8)) + value[-4:]
