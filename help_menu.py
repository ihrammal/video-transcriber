"""
help_menu.py  (converted from wxPython to PySide6, the toolkit this program
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

from PySide6.QtCore import QObject, Signal, Qt, QUrl, QUrlQuery
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit,
    QMessageBox, QMenu, QPushButton, QVBoxLayout,
)

import update_checker as uc

HELP_FILE = "help/user_guide.html"
HELP_FILES = {"en": "help/user_guide.html", "ar": "help/user_guide_ar.html"}
CHECK_TITLE = "Check for Updates"
SUPPORT_EMAIL = "iman.rammal@gmail.com"


def problem_email_url(lang="en"):
    """Prepare a draft only; no files, logs or credentials are attached."""
    from vt_i18n import tr
    url = QUrl("mailto:" + SUPPORT_EMAIL)
    query = QUrlQuery()
    query.addQueryItem("subject", tr(lang, "report_subject", version=uc.APP_VERSION))
    url.setQuery(query)
    return url


class ProblemReportDialog(QDialog):
    def __init__(self, parent=None, lang="en"):
        super().__init__(parent)
        from vt_i18n import tr
        self.lang = lang
        self.t = lambda key: tr(lang, key)
        self.setWindowTitle(self.t("report_title"))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if lang == "ar" else Qt.LayoutDirection.LeftToRight)
        layout = QVBoxLayout(self)
        intro = QLabel(self.t("report_intro"), self)
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.address = QLineEdit(SUPPORT_EMAIL, self)
        self.address.setReadOnly(True)
        self.address.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.address.setAccessibleName(self.t("report_address"))
        layout.addWidget(self.address)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QVBoxLayout()
        layout.addLayout(row)
        for name, key, handler in (
            ("email_button", "report_email", self._email),
            ("copy_button", "report_copy", self._copy),
            ("github_button", "report_github", self._github),
            ("close_button", "report_close", self.reject),
        ):
            button = QPushButton(self.t(key), self)
            button.setAccessibleName(self.t(key).replace("&", ""))
            button.clicked.connect(handler)
            setattr(self, name, button)
            row.addWidget(button)
        self.email_button.setDefault(True)
        self.resize(640, self.sizeHint().height())

    def _status(self, key):
        message = self.t(key)
        self.status.setText(message)
        self.status.setAccessibleName(message)
        parent = self.parent()
        if parent is not None and hasattr(parent, "announce"):
            parent.announce(message)

    def _email(self):
        opened = QDesktopServices.openUrl(problem_email_url(self.lang))
        self._status("report_draft_opened" if opened else "report_email_failed")

    def _copy(self):
        QApplication.clipboard().setText(SUPPORT_EMAIL)
        self._status("report_copied")

    def _github(self):
        opened = webbrowser.open(uc.ISSUES_PAGE)
        self._status("report_github_opened" if opened else "report_github_failed")


def report_problem(window):
    lang = getattr(window, "current_lang", None) or getattr(window, "lang", "en")
    return ProblemReportDialog(window, lang).exec()


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

    make(menu, "act_user_guide", window.show_user_guide, "F1")
    make(menu, "act_shortcuts", window.show_shortcuts, "Ctrl+/")
    menu.addSeparator()

    make(menu, "act_check_updates", lambda: run_check(window, False), "Ctrl+U")
    auto = window._make_shortcut(
        "act_auto_update",
        lambda checked=False: uc.set_auto_check(bool(checked)),
        "Ctrl+Shift+U",
    )
    auto.setCheckable(True)
    auto.setChecked(bool(uc.load_settings()["auto_check"]))
    window._auto_update_action = auto
    make(
        menu,
        "act_release_notes",
        lambda: webbrowser.open(uc.RELEASES_PAGE),
        "Ctrl+Shift+R",
    )
    make(
        menu,
        "act_report_problem",
        lambda: report_problem(window),
        "Ctrl+Shift+B",
    )
    menu.addSeparator()

    make(menu, "act_license", window.show_license, "Ctrl+Shift+G")
    make(menu, "act_about", window.show_about, "F12")
    menu.addSeparator()

    make(menu, "act_open_log", window.open_log_folder, "Ctrl+Shift+V")
    return menu


class _Bridge(QObject):
    """Hands a result from the background thread back to the Qt main thread."""

    finished = Signal(object, object, bool)


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
    t = window.t
    try:
        if isinstance(payload, Exception):
            if not silent:
                QMessageBox.warning(window, t("update_title"), t("update_failed"))
            return

        info = payload
        if not info["available"]:
            if not silent:
                QMessageBox.information(
                    window,
                    t("update_title"),
                    t("update_current", version=info["current"]),
                )
            return

        message = t("update_offer", latest=info["latest"], current=info["current"])
        notes = info["notes"]
        if "## العربية" in notes:
            english, arabic = notes.split("## العربية", 1)
            notes = arabic if getattr(window, "current_lang", "en") == "ar" else english
        elif getattr(window, "current_lang", "en") == "ar":
            notes = ""
        if notes:
            message += "\n\n" + t("update_notes") + "\n" + notes[:1200]

        box = QMessageBox(window)
        box.setWindowTitle(t("update_available"))
        box.setText(message)
        box.setIcon(QMessageBox.Icon.Information)
        download = box.addButton(t("update_download"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(t("update_later"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(download)
        box.exec()
        if box.clickedButton() is download:
            webbrowser.open(info["download_url"] or info["page_url"])
    except RuntimeError:
        # The window was closed while the request was running.
        pass
