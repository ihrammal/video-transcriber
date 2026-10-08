"""
help_menu.py  (converted from wxPython to PyQt6, the toolkit this program
uses.  update_checker.py stays the same and is shared with this file.)

How to use in your main window class:

    import help_menu
    ...
    menu = help_menu.build_help_menu(self)
    self.menuBar().addMenu(menu)
    ...
    QTimer.singleShot(5000, lambda: help_menu.check_on_startup(self))  # quiet

Your help file must be saved as help/user_guide.html (English) with
help/user_guide_ar.html (Arabic) beside it, and both must contain these
anchors, so the menu can jump straight to them:
    <h2 id="shortcuts">Keyboard Shortcuts</h2>
    <h2 id="license">License Agreement</h2>
The language follows the window's own lang attribute; if the file for that
language is missing, the English guide is opened instead.
When building with PyInstaller, include the folder:
    --add-data "help;help"

Menu items are created through the window's own _make_action helper, so every
item gets its translated label, its mnemonic and its keyboard shortcut, and is
retranslated when the interface language changes.  The About item keeps using
the program's own About page, which carries the contact details.
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QMenu

import update_checker as uc

HELP_FILE = "help/user_guide.html"
HELP_FILES = {"en": "help/user_guide.html", "ar": "help/user_guide_ar.html"}
CHECK_TITLE = "Check for Updates"


def resource_path(relative):
    """Finds bundled files both from source and from the built program."""
    candidates = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates.append(Path(meipass) / relative)
        candidates.append(Path(sys.executable).resolve().parent / relative)
    candidates.append(Path(__file__).resolve().parent / relative)
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def guide_path(lang="en"):
    """Absolute path of the combined help guide for one interface language."""
    relative = HELP_FILES.get(lang) or HELP_FILE
    path = resource_path(relative)
    if not path.exists() and relative != HELP_FILE:
        path = resource_path(HELP_FILE)  # no guide in that language yet
    return path


def open_help(parent=None, anchor=""):
    """Open the combined help guide in the browser, at a section when given."""
    path = guide_path(getattr(parent, "lang", None) or "en")
    if not path.exists():
        QMessageBox.critical(
            parent,
            "Help file missing",
            "The help file could not be found on this computer:\n" + str(path),
        )
        return False
    url = path.as_uri() + (("#" + anchor) if anchor else "")
    webbrowser.open(url)
    return True


def build_help_menu(window):
    """Returns the ready Help menu.  Mnemonic letters are all different."""
    menu = QMenu(window.t("menu_help"), window)
    make = window._make_action

    make(menu, "act_user_guide", lambda: open_help(window), "F1")
    make(menu, "act_shortcuts", lambda: open_help(window, "shortcuts"), "Ctrl+/")
    menu.addSeparator()

    make(menu, "act_check_updates", lambda: run_check(window, False), "Ctrl+U")
    auto = make(
        menu,
        "act_auto_update",
        lambda checked=False: uc.set_auto_check(bool(checked)),
        "Ctrl+Shift+U",
    )
    auto.setCheckable(True)
    auto.setChecked(bool(uc.load_settings()["auto_check"]))
    make(
        menu,
        "act_release_notes",
        lambda: webbrowser.open(uc.RELEASES_PAGE),
        "Ctrl+Shift+R",
    )
    make(
        menu,
        "act_report_problem",
        lambda: webbrowser.open(uc.ISSUES_PAGE),
        "Ctrl+Shift+B",
    )
    menu.addSeparator()

    make(menu, "act_license", lambda: open_help(window, "license"), "Ctrl+Shift+G")
    make(menu, "act_about", window.show_about, "F12")
    menu.addSeparator()

    # Kept from the previous Help menu: not duplicates, they open the long
    # per-language documents themselves and the log folder.
    make(menu, "act_guide_file", window.open_guide_file)
    make(menu, "act_shortcuts_file", window.open_shortcut_file)
    make(menu, "act_open_log", window.open_log_folder, "Ctrl+Shift+V")
    return menu


class _Bridge(QObject):
    """Hands a result from the background thread back to the Qt main thread."""

    finished = pyqtSignal(object, object, bool)


_bridge = None


def _get_bridge():
    global _bridge
    if _bridge is None:
        _bridge = _Bridge()
        _bridge.finished.connect(_show_result)
    return _bridge


def check_on_startup(window):
    """Quiet check: speaks up only if a newer version exists."""
    if uc.should_auto_check():
        uc.mark_checked()
        run_check(window, True)


def run_check(window, silent=False):
    """Runs the web request in the background so the window never freezes."""
    bridge = _get_bridge()

    def worker():
        try:
            payload = uc.check_for_update()
        except RuntimeError as error:
            payload = error
        bridge.finished.emit(window, payload, silent)

    threading.Thread(target=worker, daemon=True).start()


def _show_result(window, payload, silent):
    try:
        if isinstance(payload, Exception):
            if not silent:
                QMessageBox.warning(window, CHECK_TITLE, str(payload))
            return

        info = payload
        if not info["available"]:
            if not silent:
                QMessageBox.information(
                    window,
                    CHECK_TITLE,
                    "You are up to date. You are using version %s, "
                    "which is the latest version." % info["current"],
                )
            return

        message = (
            "Version %s is available. "
            "You are using version %s.\n\n"
            "Would you like to download it now?" % (info["latest"], info["current"])
        )
        if info["notes"]:
            message += "\n\nWhat is new:\n" + info["notes"][:1200]

        box = QMessageBox(window)
        box.setWindowTitle("Update Available")
        box.setText(message)
        box.setIcon(QMessageBox.Icon.Information)
        download = box.addButton("Download", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(download)
        box.exec()
        if box.clickedButton() is download:
            webbrowser.open(info["download_url"] or info["page_url"])
    except RuntimeError:
        # The window was closed while the request was running.
        pass
