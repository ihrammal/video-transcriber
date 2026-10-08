# -*- coding: utf-8 -*-
"""vt_secrets.py -- API keys kept in the Windows Credential Manager.

The preferences file (``prefs.json``) is plain text so it can be inspected and
backed up, but an API key must never sit in a plain text file.  This module
stores each key as a generic credential in Windows Credential Manager (the
same store the system uses for saved passwords), scoped to the current user:

* ``store("openai_api_key", "sk-...")``  - write or replace the secret,
* ``retrieve("openai_api_key")``         - read it back (``""`` when absent),
* ``forget("openai_api_key")``           - remove it.

Everything degrades gracefully: if Credential Manager is unavailable (a very
locked down machine, a non Windows test run), :func:`is_available` returns
``False`` and the callers fall back to their previous behaviour instead of
losing the key or raising an exception.
"""

from __future__ import annotations

import ctypes
import logging
import os
from ctypes import wintypes

log = logging.getLogger("vidtrans.secrets")

CRED_TYPE_GENERIC = 1
CRED_PERSIST_ENTERPRISE = 3
TARGET_PREFIX = "VidTrans/"

# Lazily resolved: False when Credential Manager cannot be used at all.
_available = None


class _CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.c_void_p),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def _advapi():
    dll = ctypes.windll.advapi32
    dll.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIAL), wintypes.DWORD]
    dll.CredWriteW.restype = wintypes.BOOL
    dll.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(_CREDENTIAL)),
    ]
    dll.CredReadW.restype = wintypes.BOOL
    dll.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    dll.CredDeleteW.restype = wintypes.BOOL
    dll.CredFree.argtypes = [ctypes.c_void_p]
    dll.CredFree.restype = None
    return dll


def is_available() -> bool:
    """True when Windows Credential Manager can be used on this machine."""
    global _available
    if _available is None:
        if os.name != "nt":
            _available = False
        else:
            try:
                _advapi()
                _available = True
            except Exception:  # noqa: BLE001 - exotic setups only
                log.warning("Credential Manager is not available")
                _available = False
    return bool(_available)


def _target(name: str) -> str:
    return TARGET_PREFIX + str(name).strip()


def store(name: str, value: str) -> bool:
    """Save ``value`` under ``name``; returns True on success."""
    if not is_available():
        return False
    text = str(value or "")
    if not text:
        return forget(name)
    try:
        blob = text.encode("utf-8")
        buf = ctypes.create_string_buffer(blob, len(blob))
        cred = _CREDENTIAL()
        cred.Flags = 0
        cred.Type = CRED_TYPE_GENERIC
        cred.TargetName = _target(name)
        cred.Comment = "VidTrans API key"
        cred.CredentialBlobSize = len(blob)
        cred.CredentialBlob = ctypes.cast(buf, ctypes.c_void_p)
        cred.Persist = CRED_PERSIST_ENTERPRISE
        cred.AttributeCount = 0
        cred.Attributes = None
        cred.TargetAlias = None
        cred.UserName = "vid-trans"
        if not _advapi().CredWriteW(ctypes.byref(cred), 0):
            log.error("CredWriteW failed: %s", ctypes.windll.kernel32.GetLastError())
            return False
        # ``buf`` stays referenced until here, so the API copied a live blob.
        return True
    except Exception:  # noqa: BLE001 - never lose a key silently without log
        log.exception("the key could not be written to Credential Manager")
        return False


def retrieve(name: str) -> str:
    """Return the stored secret, or ``""`` when there is none."""
    if not is_available():
        return ""
    cred_ptr = ctypes.POINTER(_CREDENTIAL)()
    try:
        if not _advapi().CredReadW(_target(name), CRED_TYPE_GENERIC, 0, ctypes.byref(cred_ptr)):
            return ""
        cred = cred_ptr.contents
        size = int(cred.CredentialBlobSize or 0)
        if size <= 0 or not cred.CredentialBlob:
            return ""
        raw = ctypes.string_at(cred.CredentialBlob, size)
        return raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - a missing key is a normal state
        return ""
    finally:
        if cred_ptr:
            try:
                _advapi().CredFree(cred_ptr)
            except Exception:  # noqa: BLE001
                pass


def forget(name: str) -> bool:
    """Delete the stored secret.  A missing entry is a success."""
    if not is_available():
        return False
    try:
        ok = _advapi().CredDeleteW(_target(name), CRED_TYPE_GENERIC, 0)
        if ok:
            return True
        err = ctypes.windll.kernel32.GetLastError()
        return err == 1168  # ERROR_NOT_FOUND: nothing stored is still success
    except Exception:  # noqa: BLE001
        log.exception("the key could not be removed from Credential Manager")
        return False


def status_text(name: str) -> str:
    """Short, human readable state used by the tests and the log."""
    if not is_available():
        return "unavailable"
    return "stored" if retrieve(name) else "empty"
