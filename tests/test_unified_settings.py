"""Keyboard navigation and optional descriptions in unified settings."""
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest


def test_pages_and_keyboard_navigation(qapp, profile, fake_secrets):
    from vt_settings import SettingsDialog
    dialog = SettingsDialog()
    dialog.show()
    qapp.processEvents()
    assert dialog.tabs.count() == 4
    dialog.interface_choice.setFocus()
    QTest.keyClick(dialog.interface_choice, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
    assert dialog.tabs.currentIndex() == 1
    QTest.keyClick(dialog.tabs, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    assert dialog.tabs.currentIndex() == 0
    dialog.tabs.tabBar().setFocus()
    QTest.keyClick(dialog.tabs.tabBar(), Qt.Key.Key_Right)
    assert dialog.tabs.currentIndex() == 1
    dialog.close()


def test_hints_remain_off_after_translation_and_progress(qapp, profile):
    import vt_a11y
    from vid_trans_app import MainWindow
    vt_a11y.update(read_hints=False)
    window = MainWindow("en")
    assert window.open_button.accessibleName()
    assert window.open_button.accessibleDescription() == ""
    window.on_progress(25)
    window.interface_combo.setCurrentIndex(1)
    assert window.open_button.accessibleName()
    assert window.open_button.accessibleDescription() == ""
    assert window.progress_bar.accessibleDescription() == ""
    vt_a11y.update(read_hints=True)
    vt_a11y.apply(window)
    assert window.open_button.accessibleDescription()
    window.deleteLater()
    qapp.processEvents()


def test_save_preferences_and_reopen(qapp, profile, fake_secrets):
    import vt_a11y
    import vt_prefs
    import update_checker
    from vt_settings import SettingsDialog
    dialog = SettingsDialog()
    dialog.accessibility_checks["read_hints"].setChecked(False)
    dialog.auto_update_choice.setChecked(False)
    dialog.timestamps_choice.setChecked(False)
    dialog._on_save()
    assert vt_a11y.load()["read_hints"] is False
    assert vt_prefs.load()["show_timestamps"] == "false"
    assert update_checker.load_settings()["auto_check"] is False
    reopened = SettingsDialog()
    assert reopened.accessibility_checks["read_hints"].isChecked() is False
    assert reopened.save_button.accessibleName()
    assert reopened.save_button.accessibleDescription() == ""
    reopened.close()
