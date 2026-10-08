"""Accessibility settings: storage, dialog and applying to the window."""

from __future__ import annotations

import vt_a11y


def test_defaults(profile):
    settings = vt_a11y.load()
    assert settings == vt_a11y.DEFAULTS


def test_update_and_reload(profile):
    vt_a11y.update(high_contrast=True, announce_progress=False)
    settings = vt_a11y.load()
    assert settings["high_contrast"] is True
    assert settings["announce_progress"] is False
    # the other flags keep their values
    assert settings["sounds"] is True
    vt_a11y.save(vt_a11y.DEFAULTS)


def test_corrupt_file_falls_back_to_defaults(profile):
    import os

    os.makedirs(os.path.dirname(vt_a11y.settings_path()), exist_ok=True)
    with open(vt_a11y.settings_path(), "w", encoding="utf-8") as handle:
        handle.write("{not json")
    assert vt_a11y.load() == vt_a11y.DEFAULTS


def test_dialog_is_built_with_every_option(qapp, profile):
    dialog, checks = vt_a11y.build_dialog(lang="en")
    try:
        assert set(checks) == set(vt_a11y.FLAGS)
        assert dialog.windowTitle() == "Accessibility Settings"
        for name, box in checks.items():
            assert box.accessibleName()
            assert box.accessibleDescription()
            assert box.isChecked() == vt_a11y.DEFAULTS[name]
    finally:
        dialog.close()


def test_dialog_in_arabic(qapp, profile):
    dialog, checks = vt_a11y.build_dialog(lang="ar")
    try:
        assert dialog.windowTitle() == "إعدادات الوصول"
        assert checks["high_contrast"].accessibleDescription()
    finally:
        dialog.close()


def test_apply_to_the_window(qapp, profile):
    import vid_trans_app

    vt_a11y.save({**vt_a11y.DEFAULTS, "high_contrast": True, "simplified_layout": True})
    window = vid_trans_app.MainWindow("en")
    try:
        vt_a11y.apply(window)
        window.show()
        qapp.processEvents()
        assert window.high_contrast is True
        assert window.high_contrast_check.isChecked() is True
        # the simplified layout hides the advanced pickers
        assert not window.language_combo.isVisible()
        assert not window.engine_combo.isVisible()
        assert window.task_combo.isVisible()
        # and the menu check mark follows
        actions = window._a11y_actions
        assert actions["act_large_focus"].isChecked() is False
    finally:
        window.deleteLater()
    vt_a11y.save(vt_a11y.DEFAULTS)


def test_settings_survive_a_restart(qapp, profile):
    import vid_trans_app

    vt_a11y.save({**vt_a11y.DEFAULTS, "large_focus": True})
    window = vid_trans_app.MainWindow("en")
    try:
        qapp.processEvents()
        assert window._a11y_actions["act_large_focus"].isChecked() is True
        assert "border: 5px" in window.styleSheet()
    finally:
        window.deleteLater()
        vt_a11y.save(vt_a11y.DEFAULTS)
