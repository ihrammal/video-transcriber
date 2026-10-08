"""The help window: topic files, search, shortcut list in words, dialogs.

The topics live as Markdown files in resources/help/<lang>/<topic>.md and
are shown by MainWindow._open_help() as a Contents list plus a read-only
plain text area.  The shortcut topic is completed at run time from the
actions of the running window and written in words, so the list can never
drift away from the program.
"""

from __future__ import annotations

import pytest

TOPICS = (
    "getting-started",
    "opening-a-video",
    "choosing-engine",
    "api-keys",
    "transcribing",
    "translating",
    "timestamps",
    "editing",
    "exporting",
    "accessibility",
    "troubleshooting",
    "shortcuts",
    "contact",
    "license",
    "about",
)


@pytest.fixture()
def window(qapp, profile):
    import vid_trans_app

    win = vid_trans_app.MainWindow("en")
    yield win
    win.deleteLater()
    qapp.processEvents()


def _contents_and_text(dialog, window):
    from PyQt6.QtWidgets import QListWidget, QPlainTextEdit

    contents = next(
        child
        for child in dialog.findChildren(QListWidget)
        if child.accessibleName() == window.t("help_contents_n")
    )
    text = next(
        child
        for child in dialog.findChildren(QPlainTextEdit)
        if child.accessibleName() == window.t("help_text_n")
    )
    return contents, text


def test_every_topic_file_exists_in_both_languages():
    import vt_help

    assert vt_help.TOPIC_ORDER == TOPICS
    for lang in ("en", "ar"):
        for topic_id in TOPICS:
            raw = vt_help.read_topic(lang, topic_id)
            assert raw.strip(), (lang, topic_id)
            assert raw.lstrip().startswith("# "), (lang, topic_id)


def test_topics_have_titles_and_stripped_markdown():
    import vt_help

    for lang in ("en", "ar"):
        for topic in vt_help.build_topics(lang):
            assert topic["title"].strip(), (lang, topic["id"])
            for line in topic["body"].splitlines():
                assert not line.startswith("#"), (lang, topic["id"], line)
                assert not line.startswith("- "), (lang, topic["id"], line)
                assert "**" not in line and "`" not in line, (lang, topic["id"])
            assert "](" not in topic["body"], (lang, topic["id"])


def test_both_languages_offer_the_same_topics_in_the_same_order():
    import vt_help

    en = [topic["id"] for topic in vt_help.build_topics("en")]
    ar = [topic["id"] for topic in vt_help.build_topics("ar")]
    assert en == ar == list(TOPICS)


def test_the_guide_is_a_detailed_document():
    import vt_help

    for lang in ("en", "ar"):
        total = sum(len(topic["body"]) for topic in vt_help.build_topics(lang))
        assert total >= 4000, (lang, total)


def test_search_finds_topics_and_reports_nothing():
    import vt_help

    topics = vt_help.build_topics("en")
    found = vt_help.search(topics, "API KEY")
    assert found, "search must find the api keys topic"
    assert "api-keys" in [topic_id for topic_id, _, _ in found]
    assert vt_help.search(topics, "") == []
    assert vt_help.search(topics, "zzzz-not-there") == []


def test_the_shortcut_list_covers_every_shortcut_of_the_program(window):
    import vt_help

    real = set()
    for menu_action in window.menuBar().actions():
        menu = menu_action.menu()
        if menu is None:
            continue
        for action in menu.actions():
            if action.isSeparator() or action.menu() is not None:
                continue
            key = action.shortcut().toString()
            if key:
                real.add(key)
    real.add(window.start_button.shortcut().toString())
    assert len(real) >= 30, real

    listed = set()
    for _heading, rows in vt_help.shortcut_groups(window):
        listed.update(words for _label, words in rows)
    for key in real:
        assert vt_help.key_words(key) in listed, key
    assert "Control plus O" in listed
    assert "Control plus Shift plus T" in listed
    assert "Alt plus F4" in listed
    assert not any(
        words.startswith("Ctrl") for words in listed
    ), "the list must speak words, not key notations"


def test_key_words_reads_in_words():
    import vt_help

    assert vt_help.key_words("Ctrl+O") == "Control plus O"
    assert vt_help.key_words("Ctrl+Shift+N") == "Control plus Shift plus N"
    assert vt_help.key_words("Ctrl+,") == "Control plus comma"
    assert vt_help.key_words("Ctrl+/") == "Control plus slash"
    assert vt_help.key_words("F5") == "F5"
    assert vt_help.key_words("") == ""


def test_the_help_dialog_shows_contents_and_text(window):
    from PyQt6.QtGui import QShortcut
    from PyQt6.QtWidgets import QLabel, QApplication
    import vt_help

    dlg = window._open_help()
    try:
        assert dlg.windowTitle() == window.t("help_title_guide")
        assert dlg.isModal()
        contents, text = _contents_and_text(dlg, window)
        assert contents.count() == len(TOPICS)
        assert contents.currentRow() == 0
        assert text.isReadOnly()

        topics = vt_help.build_topics("en")
        titles = [contents.item(i).text() for i in range(contents.count())]
        assert titles == [topic["title"] for topic in topics]
        assert text.toPlainText() == topics[0]["body"]

        # selecting another topic loads it into the text
        contents.setCurrentRow(5)
        assert text.toPlainText() == topics[5]["body"]
        assert topics[5]["title"] not in ("",)

        # F6 moves the focus: from the contents to the text, and back
        f6 = next(s for s in dlg.findChildren(QShortcut) if s.key().toString() == "F6")
        contents.setFocus()
        f6.activated.emit()
        assert dlg.focusWidget() is text, "F6 must move to the text"
        f6.activated.emit()
        assert dlg.focusWidget() is contents, "F6 must come back to the contents"

        # the navigation hint is on screen
        hints = [
            label.text()
            for label in dlg.findChildren(QLabel)
            if label.accessibleName() == window.t("help_hint")
        ]
        assert hints == [window.t("help_hint")]
    finally:
        dlg.hide()
        dlg.deleteLater()
        QApplication.processEvents()


def test_enter_on_a_topic_keeps_the_focus_in_the_text(window):
    """Return must open the topic, not click a hidden default button.

    A QDialog turns Enter on a list into a click on its default push
    button; the help dialog's "back to contents" button used to win that
    race and yank the focus away from the topic the user had just asked
    to read.  No button in the dialog may be the default, and Enter on
    both lists must leave the focus in the text area.
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication, QLineEdit, QListWidget, QPushButton
    import vt_help

    dlg = window._open_help()
    try:
        contents, text = _contents_and_text(dlg, window)
        topics = vt_help.build_topics("en")

        for button in dlg.findChildren(QPushButton):
            assert not button.isDefault(), button.text()
            assert not button.autoDefault(), button.text()

        contents.setCurrentRow(3)
        contents.setFocus()
        QTest.keyClick(contents, Qt.Key.Key_Return)
        QApplication.processEvents()
        assert text.toPlainText() == topics[3]["body"], "the topic must open"
        assert dlg.focusWidget() is text, (
            "Enter must open the topic and keep the focus in the text"
        )

        # Escape inside the text still walks back to the contents
        QTest.keyClick(text, Qt.Key.Key_Escape)
        QApplication.processEvents()
        assert dlg.focusWidget() is contents

        # Enter on a search result behaves exactly like Enter on contents
        search = next(
            child
            for child in dlg.findChildren(QLineEdit)
            if child.accessibleName() == window.t("help_search_n")
        )
        button = next(
            child
            for child in dlg.findChildren(QPushButton)
            if child.text() == window.t("help_search_btn")
        )
        results = next(
            child
            for child in dlg.findChildren(QListWidget)
            if child.accessibleName() == window.t("help_results_n")
        )
        search.setText("engine")
        button.click()
        results.setCurrentRow(0)
        results.setFocus()
        QTest.keyClick(results, Qt.Key.Key_Return)
        QApplication.processEvents()
        assert dlg.focusWidget() is text, (
            "Enter on a search result must keep the focus in the text"
        )
        opened = [t for t in topics if t["body"] == text.toPlainText()]
        assert opened, "the selected result must be shown"
    finally:
        dlg.hide()
        dlg.deleteLater()
        QApplication.processEvents()


def test_the_search_reports_and_opens_results(window):
    from PyQt6.QtWidgets import (
        QApplication,
        QLabel,
        QLineEdit,
        QListWidget,
        QPushButton,
    )
    import vt_help

    dlg = window._open_help()
    try:
        search = next(
            child
            for child in dlg.findChildren(QLineEdit)
            if child.accessibleName() == window.t("help_search_n")
        )
        button = next(
            child
            for child in dlg.findChildren(QPushButton)
            if child.text() == window.t("help_search_btn")
        )
        results = next(
            child
            for child in dlg.findChildren(QListWidget)
            if child.accessibleName() == window.t("help_results_n")
        )
        count_label = next(
            child
            for child in dlg.findChildren(QLabel)
            if child.accessibleName() == window.t("help_results_n")
        )
        _, text = _contents_and_text(dlg, window)

        search.setText("engine")
        button.click()
        assert results.isVisibleTo(dlg), "matches must become visible"
        assert results.count() >= 1
        assert count_label.text() == window.t(
            "help_results_count", count=results.count()
        )

        # activating a result opens its topic
        results.setCurrentRow(0)
        results.itemActivated.emit(results.item(0))
        topics = vt_help.build_topics("en")
        opened = [
            topic for topic in topics if topic["body"] == text.toPlainText()
        ]
        assert opened, "the selected result must be shown"

        # a word that matches nothing is announced as such
        search.setText("zzzz-nothing")
        button.click()
        assert not results.isVisibleTo(dlg)
        assert count_label.text() == window.t("help_no_results")
    finally:
        dlg.hide()
        dlg.deleteLater()
        QApplication.processEvents()


def test_the_shortcut_dialog_opens_on_the_shortcut_topic_in_words(window):
    from PyQt6.QtWidgets import QApplication
    import vt_help

    dlg = window.show_shortcuts()
    try:
        assert dlg.windowTitle() == window.t("help_title_shortcuts")
        contents, text = _contents_and_text(dlg, window)
        expected = next(
            topic for topic in vt_help.build_topics("en", window)
            if topic["id"] == "shortcuts"
        )
        assert text.toPlainText() == expected["body"]
        assert "Control plus O" in text.toPlainText()
        assert "F5" in text.toPlainText()
        assert dlg.focusWidget() is text, "the shortcut list must be read first"
        shortcut_row = [
            i
            for i in range(contents.count())
            if contents.item(i).data(0x0100) == "shortcuts"  # Qt.UserRole
        ]
        assert shortcut_row == [contents.currentRow()]
    finally:
        dlg.hide()
        dlg.deleteLater()
        QApplication.processEvents()


def test_the_arabic_help_dialog_flips_to_right_to_left(qapp, profile):
    from PyQt6.QtWidgets import QApplication
    import vid_trans_app
    import vt_help

    win = vid_trans_app.MainWindow("ar")
    try:
        dlg = win._open_help()
        assert dlg.layoutDirection().value == 1  # RightToLeft
        contents, text = _contents_and_text(dlg, win)
        assert contents.count() == len(TOPICS)
        first = vt_help.build_topics("ar")[0]
        assert contents.item(0).text() == first["title"]
        assert text.toPlainText() == first["body"]
        assert any(ord(char) > 0x0600 for char in text.toPlainText()), (
            "the Arabic document must be shown, not the English one"
        )
        dlg.hide()
        dlg.deleteLater()
        QApplication.processEvents()
    finally:
        win.deleteLater()
        QApplication.processEvents()


def test_the_about_page_stays_a_single_page(window):
    from PyQt6.QtWidgets import QApplication, QListWidget, QTextBrowser

    dlg = window.show_about()
    try:
        assert dlg.findChild(QListWidget) is None, "About has no contents list"
        browser = dlg.findChild(QTextBrowser)
        assert browser is not None and "<h1" in browser.toHtml()
        assert browser.isReadOnly()
    finally:
        dlg.hide()
        dlg.deleteLater()
        QApplication.processEvents()
