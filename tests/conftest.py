"""Shared pytest fixtures for the Accessible Video Transcriber test suite.

The suite always runs head-less: Qt uses the ``offscreen`` platform and every
test that touches the per-user profile works inside a throwaway folder, so a
developer machine and a CI agent are never written to.
"""

from __future__ import annotations

import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false")

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """One application instance for the whole session."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture()
def profile(tmp_path, monkeypatch):
    """Redirect ``%LOCALAPPDATA%\\Accessible Video Transcriber`` into a temporary folder."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("HF_HOME", raising=False)
    import tempfile
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    yield tmp_path
    # Flush queued widget deletion while this temporary profile is still set.
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is not None:
        for widget in app.topLevelWidgets():
            timer = getattr(widget, "_recovery_timer", None)
            if timer is not None:
                timer.stop()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture(autouse=True)
def fake_secrets(monkeypatch):
    """In-memory replacement for the Windows Credential Manager helpers.

    Keeps the tests off the real credential store while exercising exactly the
    same ``vt_prefs`` code paths (store, retrieve, forget, migration).
    """
    import vt_secrets

    store = {}

    def _store(name, value):
        if not vt_secrets.is_available():
            return False
        # mirrors the real behaviour: an empty value removes the secret
        if not value:
            store.pop(name, None)
        else:
            store[name] = value
        return True

    monkeypatch.setattr(vt_secrets, "is_available", lambda: True)
    monkeypatch.setattr(vt_secrets, "store", _store)
    monkeypatch.setattr(vt_secrets, "retrieve", lambda name: store.get(name, ""))
    monkeypatch.setattr(
        vt_secrets, "forget", lambda name: (store.pop(name, None) is not None) or True
    )
    return store
