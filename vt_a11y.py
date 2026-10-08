# -*- coding: utf-8 -*-
"""Accessibility preferences for the Accessible Video Transcriber.

Everything here is written so that the values can be read by a screen reader
and changed with the keyboard alone: the settings are stored as simple
true/false flags in ``accessibility.json`` next to the other preferences, and
the dialog built by :func:`open_dialog` is a normal modal dialog with an
explicit tab order.

The flags:

* ``high_contrast``      - maximum-contrast black/white theme.
* ``large_focus``        - thicker, brighter focus rectangle on every control.
* ``simplified_layout``  - hide the advanced pickers on the main screen.
* ``announce_progress``  - speak percentage steps while a task runs.
* ``sounds``             - play the short completion/error tones.
"""

import json
import logging
import os

DEFAULTS = {
    "high_contrast": False,
    "large_focus": False,
    "simplified_layout": False,
    "announce_progress": True,
    "sounds": True,
}

FLAGS = tuple(DEFAULTS)


def settings_path():
    """Full path of the accessibility settings file."""
    try:
        import vt_bootstrap

        folder = vt_bootstrap.app_data_dir()
    except Exception:
        folder = os.path.join(
            os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
            "Accessible Video Transcriber",
        )
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:  # noqa: BLE001 - a read-only profile still gets defaults
        logging.exception("could not create the settings folder")
    return os.path.join(folder, "accessibility.json")


def load():
    """Return the saved flags, falling back to the defaults for any problem."""
    path = settings_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:  # noqa: BLE001 - missing or corrupt file is not an error
        return dict(DEFAULTS)
    if not isinstance(data, dict):
        return dict(DEFAULTS)
    return {key: bool(data.get(key, DEFAULTS[key])) for key in FLAGS}


def save(settings):
    """Write the given flags to disk and return them normalised."""
    clean = {key: bool(settings.get(key, DEFAULTS[key])) for key in FLAGS}
    path = settings_path()
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(clean, handle, indent=2, sort_keys=True)
    except Exception:  # noqa: BLE001 - never block the toggle itself
        logging.exception("accessibility settings could not be saved")
    return clean


def update(**flags):
    """Update a subset of the flags (``update(high_contrast=True)``)."""
    merged = load()
    for key, value in flags.items():
        if key in DEFAULTS:
            merged[key] = bool(value)
    return save(merged)


def apply(app):
    """Push the saved flags into a running application instance."""
    settings = load()
    try:
        app.accessibility_settings = settings
        if hasattr(app, "high_contrast_check") and app.high_contrast_check is not None:
            app.high_contrast_check.blockSignals(True)
            app.high_contrast_check.setChecked(settings["high_contrast"])
            app.high_contrast_check.blockSignals(False)
        if hasattr(app, "apply_theme"):
            app.apply_theme()
        if hasattr(app, "apply_layout_mode"):
            app.apply_layout_mode()
        if hasattr(app, "_sync_settings_menus"):
            app._sync_settings_menus()
    except Exception:  # noqa: BLE001 - applying settings must not crash the app
        logging.exception("could not apply accessibility settings")
    return settings


def build_dialog(parent=None, lang="en"):
    """Build (but do not run) the Accessibility Settings dialog.

    Returns ``(dialog, checks)`` where ``checks`` maps every flag name to its
    checkbox, so a test can drive the dialog without blocking on ``exec()``.
    Every control is reachable with Tab/Shift+Tab, and each label describes the
    effect of its checkbox for screen readers.
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QLabel,
        QVBoxLayout,
    )

    try:
        from vid_trans_app import tr

        def key_text(key, **kwargs):
            return tr(lang, key, **kwargs)

    except Exception:  # noqa: BLE001 - fall back to the shared table directly
        from vt_i18n import tr

        def key_text(key, **kwargs):
            return tr(lang, key, **kwargs)

    settings = load()

    dlg = QDialog(parent)
    dlg.setWindowTitle(key_text("acc_title"))
    dlg.setAccessibleName(key_text("acc_title"))
    dlg.setModal(True)
    layout = QVBoxLayout(dlg)
    heading = QLabel(key_text("acc_intro"))
    heading.setWordWrap(True)
    layout.addWidget(heading)

    form = QFormLayout()
    checks = {}
    rows = (
        ("high_contrast", "acc_lbl_hc", "acc_desc_hc"),
        ("large_focus", "acc_lbl_focus", "acc_desc_focus"),
        ("simplified_layout", "acc_lbl_simple", "acc_desc_simple"),
        ("announce_progress", "acc_lbl_progress", "acc_desc_progress"),
        ("sounds", "acc_lbl_sounds", "acc_desc_sounds"),
    )
    for key, label_key, desc_key in rows:
        box = QCheckBox(key_text(label_key))
        box.setChecked(bool(settings.get(key, DEFAULTS[key])))
        box.setAccessibleName(key_text(label_key))
        box.setAccessibleDescription(key_text(desc_key))
        box.setToolTip(key_text(desc_key))
        form.addRow(box, QLabel(""))
        checks[key] = box
    layout.addLayout(form)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText(key_text("btn_ok_n"))
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(key_text("btn_cancel"))
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    layout.addWidget(buttons)

    dlg.resize(560, 420)
    return dlg, checks


def open_dialog(parent=None, lang="en"):
    """Open the modal Accessibility Settings dialog.

    Returns ``True`` when the user pressed OK, ``False`` otherwise.  The
    change is saved and pushed into the running window when OK is pressed.
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QDialog

    dlg, checks = build_dialog(parent=parent, lang=lang)
    dlg.show()
    dlg.raise_()
    dlg.activateWindow()
    checks["high_contrast"].setFocus(Qt.FocusReason.OtherFocusReason)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        return False

    values = {key: box.isChecked() for key, box in checks.items()}
    save(values)
    if parent is not None:
        try:
            apply(parent)
        except Exception:  # noqa: BLE001
            logging.exception("could not apply accessibility settings")
        try:
            from vid_trans_app import tr

            parent.announce(tr(lang, "msg_settings_saved"))
        except Exception:  # noqa: BLE001 - announcing is best effort
            pass
    return True
