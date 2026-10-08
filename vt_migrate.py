# -*- coding: utf-8 -*-
"""vt_migrate.py -- one-time import of the version 1.1 data folders.

Version 1.1 kept its per-user data in ``%LOCALAPPDATA%\\VidTrans`` and the
Whisper model cache in ``%USERPROFILE%\\.cache\\huggingface``.  Version 1.2
keeps everything under ``%LOCALAPPDATA%\\Accessible Video Transcriber``.  On
the first start after an upgrade :func:`migrate_once` copies the old files
into the new folder, under these rules:

* the old folders are read only -- never moved, never deleted, never changed;
* a file that already exists in the new folder is never overwritten;
* each file is copied to a temporary ``.part`` name first and renamed into
  place afterwards, so a run that dies halfway can never leave a half-written
  settings file behind, and the next run simply finishes the job;
* a marker file is written only when every file succeeded, so the migration
  runs once when it works and resumes safely when it does not;
* only file names and counts are ever logged -- the settings files hold API
  keys and their contents must never be printed or logged.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import shutil

log = logging.getLogger("vidtrans.migrate")

MARKER_NAME = "migrated_from_1_1.json"

#: Sub-folder of the new data folder that receives the old model cache.
MODEL_CACHE_SUBDIR = "huggingface"


def legacy_app_data_dir() -> str:
    """The 1.1 settings folder (read only, never modified)."""
    try:
        import vt_bootstrap

        name = getattr(vt_bootstrap, "LEGACY_APP_NAME", "VidTrans")
    except Exception:
        name = "VidTrans"
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, name)


def legacy_model_cache_dir() -> str:
    """The Hugging Face cache the 1.1 program downloaded models into."""
    return os.path.join(os.path.expanduser("~"), ".cache", "huggingface")


def _marker_path(target: str) -> str:
    return os.path.join(target, MARKER_NAME)


def _is_link(path: str) -> bool:
    if os.path.islink(path):
        return True
    isjunction = getattr(os.path, "isjunction", None)
    return bool(isjunction(path)) if isjunction else False


def _copy_tree(source: str, target: str) -> tuple:
    """Copy every file of ``source`` under ``target``, skipping existing ones.

    Returns ``(copied, skipped, failed)`` counts.  File contents are copied
    but never read into memory for logging.
    """
    copied = skipped = failed = 0
    for dirpath, dirnames, filenames in os.walk(source):
        # never follow a link or junction out of the folder we were given
        dirnames[:] = [d for d in dirnames if not _is_link(os.path.join(dirpath, d))]
        relative_dir = os.path.relpath(dirpath, source)
        for filename in filenames:
            src = os.path.join(dirpath, filename)
            rel = filename if relative_dir == "." else os.path.join(relative_dir, filename)
            dst = os.path.join(target, rel)
            if os.path.exists(dst):
                skipped += 1
                log.debug("migration keeps the existing file: %s", rel)
                continue
            part = dst + ".part"
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, part)
                os.replace(part, dst)
                copied += 1
                log.debug("migration copied: %s", rel)
            except OSError as error:
                failed += 1
                log.warning("migration could not copy %s: %s", rel, error.__class__.__name__)
                try:
                    os.remove(part)
                except OSError:
                    pass
    return copied, skipped, failed


def migrate_once(target: str = None, legacy_data: str = None,
                 legacy_models: str = None) -> dict:
    """Copy the 1.1 folders into ``target`` once.  Never raises.

    Returns a summary dict: ``ran``, ``copied``, ``skipped``, ``failed``.
    """
    summary = {"ran": False, "copied": 0, "skipped": 0, "failed": 0}
    try:
        import vt_bootstrap

        target = target or vt_bootstrap.app_data_dir()
        legacy_data = legacy_data or legacy_app_data_dir()
        legacy_models = legacy_models or legacy_model_cache_dir()
        marker = _marker_path(target)

        if os.path.exists(marker):
            return summary  # the one-shot migration already ran

        sources = []
        if os.path.isdir(legacy_data):
            sources.append((legacy_data, target, "settings"))
        model_target = os.path.join(target, MODEL_CACHE_SUBDIR)
        if os.path.isdir(legacy_models):
            sources.append((legacy_models, model_target, "models"))

        if not sources:
            # a fresh install: nothing to import, record that we looked
            _write_marker(target, summary)
            return summary

        summary["ran"] = True
        for source, destination, kind in sources:
            log.info(
                "importing the %s folder of version 1.1 into the new data folder",
                kind,
            )
            copied, skipped, failed = _copy_tree(source, destination)
            summary["copied"] += copied
            summary["skipped"] += skipped
            summary["failed"] += failed

        if summary["failed"] == 0:
            _write_marker(target, summary)
            log.info(
                "version 1.1 data imported: %d files copied, %d already present",
                summary["copied"],
                summary["skipped"],
            )
        else:
            log.warning(
                "version 1.1 data import incomplete (%d failed); "
                "it will continue on the next start",
                summary["failed"],
            )
    except Exception:
        summary["failed"] += 1
        log.exception("the version 1.1 data import stopped early; it will retry")
    return summary


def _write_marker(target: str, summary: dict) -> None:
    try:
        payload = dict(summary)
        payload["when"] = _dt.datetime.now().isoformat(timespec="seconds")
        part = _marker_path(target) + ".part"
        with open(part, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.replace(part, _marker_path(target))
    except OSError:
        log.warning("the migration marker could not be written")
