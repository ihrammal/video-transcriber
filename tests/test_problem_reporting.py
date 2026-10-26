"""Reporting contacts must open drafts without sending or sharing app data."""
from urllib.parse import parse_qs, urlsplit
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_email_draft_has_correct_recipient_and_localized_subject(lang):
    import help_menu
    from vt_i18n import tr
    url = urlsplit(bytes(help_menu.problem_email_url(lang).toEncoded()).decode("ascii"))
    assert url.scheme == "mailto"
    assert url.path == "iman.rammal@gmail.com"
    assert parse_qs(url.query) == {
        "subject": [tr(lang, "report_subject", version=help_menu.uc.APP_VERSION)]
    }


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_report_dialog_accessibility_and_copy(qapp, profile, monkeypatch, lang):
    import help_menu
    copied = []
    monkeypatch.setattr(help_menu.QApplication, "clipboard", lambda: SimpleNamespace(setText=copied.append))
    dialog = help_menu.ProblemReportDialog(lang=lang)
    assert dialog.address.text() == help_menu.SUPPORT_EMAIL
    assert dialog.address.isReadOnly() and dialog.address.accessibleName()
    assert dialog.layoutDirection() == (Qt.LayoutDirection.RightToLeft if lang == "ar" else Qt.LayoutDirection.LeftToRight)
    assert dialog.address.layoutDirection() == Qt.LayoutDirection.LeftToRight
    for button in (dialog.email_button, dialog.copy_button, dialog.github_button, dialog.close_button):
        assert button.accessibleName()
    dialog.copy_button.click()
    assert copied == ["iman.rammal@gmail.com"]
    assert dialog.status.text() == dialog.t("report_copied")
    dialog.deleteLater()


@pytest.mark.parametrize("opened", [True, False])
def test_email_launch_result_and_fallback(qapp, profile, monkeypatch, opened):
    import help_menu
    launched = []
    def open_draft(url):
        launched.append(url.toString())
        return opened
    monkeypatch.setattr(help_menu.QDesktopServices, "openUrl", open_draft)
    dialog = help_menu.ProblemReportDialog(lang="ar")
    dialog.email_button.click()
    assert len(launched) == 1 and launched[0].startswith("mailto:iman.rammal@gmail.com?")
    assert dialog.status.text() == dialog.t("report_draft_opened" if opened else "report_email_failed")
    dialog.deleteLater()


def test_menu_opens_reporting_choices_instead_of_browser(qapp, profile, monkeypatch):
    import help_menu
    from vid_trans_app import MainWindow
    window = MainWindow("en")
    calls = []
    monkeypatch.setattr(help_menu, "report_problem", calls.append)
    action = next(action for action, key in window._action_map if key == "act_report_problem")
    assert action.shortcut().toString() == "Ctrl+Shift+B"
    action.trigger()
    assert calls == [window]
    window.deleteLater()


def test_github_option_remains_available(qapp, profile, monkeypatch):
    import help_menu
    opened = []
    monkeypatch.setattr(help_menu.webbrowser, "open", lambda url: opened.append(url) or True)
    dialog = help_menu.ProblemReportDialog()
    dialog.github_button.click()
    assert opened == [help_menu.uc.ISSUES_PAGE]
    dialog.deleteLater()
