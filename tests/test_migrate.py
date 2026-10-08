# -*- coding: utf-8 -*-
"""The one-shot import of the version 1.1 data folders (vt_migrate).

The rules under test: the old folder is only ever read, existing files in
the new folder are never overwritten, the migration runs once behind a
marker, a halfway failure resumes safely, and nothing but file names and
counts reaches the log -- the settings files can contain API keys.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

import pytest

import vt_migrate

REAL_LEGACY = Path(os.environ.get("LOCALAPPDATA") or "") / "VidTrans"
NEW_FOLDER_NAME = "Accessible Video Transcriber"


def _digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fingerprint(root: Path) -> dict:
    """name -> sha256 for every file; comparing digests never prints content."""
    return {
        str(p.relative_to(root)): _digest(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _seed_real_or_synthetic(destination: Path) -> None:
    """A copy of this machine's real 1.1 folder, or a realistic stand-in."""
    if REAL_LEGACY.is_dir():
        shutil.copytree(REAL_LEGACY, destination)
        return
    (destination / "audio").mkdir(parents=True)
    (destination / "prefs.json").write_text(
        '{"transcribe_engine": "openai", "openai_api_key": "sk-synthetic-test-key",'
        ' "whisper_model": "small", "show_timestamps": "false"}',
        encoding="utf-8",
    )
    (destination / "setup.json").write_text('{"language": "ar"}', encoding="utf-8")
    (destination / "accessibility.json").write_text(
        '{"high_contrast": true, "sounds": false}', encoding="utf-8"
    )
    (destination / "audio" / "welcome.wav").write_bytes(b"RIFFfake")


@pytest.fixture()
def seeded(tmp_path, monkeypatch):
    """A profile folder whose VidTrans is a copy of a real 1.1 folder."""
    profile = tmp_path / "profile"
    legacy = profile / "VidTrans"
    _seed_real_or_synthetic(legacy)
    monkeypatch.setenv("LOCALAPPDATA", str(profile))
    # never let a test copy the machine's real Hugging Face cache
    absent_models = tmp_path / "no-hf-cache"
    return {
        "profile": profile,
        "legacy": legacy,
        "target": profile / NEW_FOLDER_NAME,
        "legacy_models": absent_models,
    }


def _migrate(seeded, **kwargs):
    kwargs.setdefault("legacy_models", str(seeded["legacy_models"]))
    return vt_migrate.migrate_once(**kwargs)


def test_a_copy_of_the_real_1_1_folder_is_imported(seeded):
    before_source = _fingerprint(seeded["legacy"])
    summary = _migrate(seeded)

    assert summary["failed"] == 0, summary
    assert summary["ran"] is True
    assert summary["copied"] == len(before_source), summary

    target = seeded["target"]
    assert (target / vt_migrate.MARKER_NAME).is_file()
    for relative, digest in before_source.items():
        imported = target / relative
        assert imported.is_file(), relative
        assert _digest(imported) == digest, relative

    # the old folder is never moved, deleted or changed
    assert _fingerprint(seeded["legacy"]) == before_source
    # nothing is left half copied
    assert not list(target.rglob("*.part"))


def test_the_migration_runs_only_once(seeded):
    assert _migrate(seeded)["ran"] is True
    extra = seeded["legacy"] / "extra-after-upgrade.json"
    extra.write_text('{"later": true}', encoding="utf-8")

    second = _migrate(seeded)
    assert second["ran"] is False
    assert not (seeded["target"] / "extra-after-upgrade.json").exists()


def test_settings_already_in_the_new_folder_are_never_overwritten(seeded):
    target = seeded["target"]
    target.mkdir(parents=True)
    fresh = target / "prefs.json"
    fresh.write_text('{"transcribe_engine": "local"}', encoding="utf-8")
    fresh_digest = _digest(fresh)
    before_source = _fingerprint(seeded["legacy"])

    summary = _migrate(seeded)

    assert summary["failed"] == 0
    assert summary["skipped"] >= 1
    assert _digest(fresh) == fresh_digest
    assert _fingerprint(seeded["legacy"]) == before_source


def test_a_halfway_failure_resumes_on_the_next_start(seeded, monkeypatch):
    real_shutil = vt_migrate.shutil

    class FlakyCopy:
        failed = False

        @classmethod
        def copy2(cls, src, dst, *args, **kwargs):
            if Path(src).name == "setup.json" and not cls.failed:
                cls.failed = True
                raise OSError("simulated disk full")
            return real_shutil.copy2(src, dst, *args, **kwargs)

    monkeypatch.setattr(vt_migrate, "shutil", FlakyCopy)

    first = _migrate(seeded)
    assert first["failed"] == 1
    assert not (seeded["target"] / vt_migrate.MARKER_NAME).exists()
    assert not list(seeded["target"].rglob("*.part"))
    before_source = _fingerprint(seeded["legacy"])

    monkeypatch.setattr(vt_migrate, "shutil", real_shutil)
    second = _migrate(seeded)
    assert second["failed"] == 0
    assert second["ran"] is True
    assert (seeded["target"] / vt_migrate.MARKER_NAME).is_file()
    for relative, digest in before_source.items():
        assert _digest(seeded["target"] / relative) == digest, relative
    assert _fingerprint(seeded["legacy"]) == before_source


def test_no_settings_contents_ever_reach_the_log(seeded, caplog):
    secret = "sk-real-test-key-must-not-be-logged"
    prefs = seeded["legacy"] / "prefs.json"
    prefs.write_text('{"openai_api_key": "%s"}' % secret, encoding="utf-8")

    with caplog.at_level("DEBUG"):
        _migrate(seeded)

    assert secret not in caplog.text
    assert "prefs.json" in caplog.text  # names and counts are fine


def test_setup_runtime_dirs_moves_temp_and_models_into_the_new_folder(
    profile, monkeypatch
):
    import tempfile

    import vt_bootstrap

    for variable in ("TMPDIR", "TEMP", "TMP", "HF_HOME"):
        monkeypatch.setenv(variable, "unchanged")
    monkeypatch.setattr(tempfile, "tempdir", tempfile.gettempdir())

    data = Path(vt_bootstrap.setup_runtime_dirs())

    assert data == profile / NEW_FOLDER_NAME
    temp = data / "temp"
    assert Path(tempfile.gettempdir()) == temp
    for variable in ("TMPDIR", "TEMP", "TMP"):
        assert Path(os.environ[variable]) == temp
    assert Path(os.environ["HF_HOME"]) == data / "huggingface"


def test_every_settings_path_lives_in_the_new_folder(profile):
    from pathlib import Path as P

    import update_checker
    import vt_a11y
    import vt_bootstrap
    import vt_prefs

    new = profile / NEW_FOLDER_NAME
    for path in (vt_bootstrap.app_data_dir(), update_checker.user_data_dir()):
        assert P(path) == new, path
    for path in (vt_bootstrap.log_path(), vt_a11y.settings_path(), vt_prefs.prefs_path()):
        assert P(path).parent == new, path
    assert NEW_FOLDER_NAME in str(vt_bootstrap.log_path())
    assert "VidTrans" not in str(vt_a11y.settings_path())
    assert "VidTrans" not in str(vt_prefs.prefs_path())
