"""The two detailed HTML documents in resources/help/<lang>/.

The Help menu opens them in the browser: "Open guide file" (the long
guide) and "Open shortcut file" (every shortcut the program has).  They
are documents for readers, so they carry real headings and subheadings a
screen reader can jump between, no scripts at all, the author's contact
details, and a shortcut file whose key notation and interface-language
labels match the shortcuts the running program really has.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELP = ROOT / "resources" / "help"
DOCMENTS = ("guide.html", "shortcuts.html")
# Ctrl+O, Ctrl+Shift+T, Ctrl+, Ctrl+/ ... plus Alt+F4 and the F keys.
KEY_TOKEN = re.compile(r"Ctrl\+(?:Shift\+)?(?:[A-Z0-9]|,|/)|Alt\+F4|\bF[0-9]{1,2}\b")


def _read(lang: str, name: str) -> str:
    return (HELP / lang / name).read_text(encoding="utf-8")


def _visible(raw: str) -> str:
    """The text a reader gets from the page, with tags and entities removed."""
    text = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(html.unescape(text).split())


def _norm(text: str) -> str:
    """Ignore mnemonics (\"&&\") and runs of whitespace when comparing labels."""
    return " ".join(text.replace("&", "").split())


def _window(qapp, profile, lang: str):
    import vid_trans_app

    win = vid_trans_app.MainWindow(lang)
    return win


def _shortcuts_of(win) -> list[tuple[str, str]]:
    pairs = []
    for act, key in win._action_map:
        shortcut = act.shortcut().toString()
        if shortcut:
            pairs.append((shortcut, win.t(key)))
    pairs.append((win.start_button.shortcut().toString(), win.start_button.text()))
    return pairs


def _real_keys(win) -> set[str]:
    real = {shortcut for shortcut, _ in _shortcuts_of(win)}
    # Alt+F4 closes the window; Escape and F6 live in the help dialog.
    real.update({"Alt+F4", "Esc", "F6"})
    return real


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_two_documents_exist_and_look_like_documents(lang):
    for name in DOCMENTS:
        raw = _read(lang, name)
        assert raw.lstrip().startswith("<!DOCTYPE html>"), name
        assert '<meta charset="utf-8">' in raw, name
        assert "<title>" in raw
        title = raw.split("<title>", 1)[1].split("</title>", 1)[0]
        assert _visible(title), name
        assert "<script" not in raw.lower(), name


@pytest.mark.parametrize("name", DOCMENTS)
def test_language_and_direction_attributes(name):
    en = _read("en", name)
    ar = _read("ar", name)
    assert '<html lang="en">' in en
    assert "rtl" not in en
    assert '<html lang="ar" dir="rtl">' in ar


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_guide_has_real_headings_and_subheadings(lang):
    raw = _read(lang, "guide.html")
    assert len(re.findall(r"<h1\b", raw)) == 1
    assert len(re.findall(r"<h2\b", raw)) >= 10
    assert len(re.findall(r"<h3\b", raw)) >= 15
    for heading in re.findall(r"<h[123][^>]*>(.*?)</h[123]>", raw, re.S):
        assert _visible(heading), "every heading must carry text"


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_shortcut_file_has_a_heading_per_group(lang):
    raw = _read(lang, "shortcuts.html")
    assert len(re.findall(r"<h1\b", raw)) == 1
    assert len(re.findall(r"<h2\b", raw)) >= 8
    for heading in re.findall(r"<h[123][^>]*>(.*?)</h[123]>", raw, re.S):
        assert _visible(heading)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_internal_link_resolves_to_a_heading_id(lang):
    for name in DOCMENTS:
        raw = _read(lang, name)
        ids = set(re.findall(r'id="([^"]+)"', raw))
        hrefs = set(re.findall(r'href="#([^"]+)"', raw))
        assert hrefs <= ids, (name, sorted(hrefs - ids))


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_both_documents_are_detailed_not_stubs(lang):
    assert len(_visible(_read(lang, "guide.html"))) >= 12000, lang
    assert len(_visible(_read(lang, "shortcuts.html"))) >= 6000, lang


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_author_contact_details_are_in_the_guide(lang):
    raw = _read(lang, "guide.html")
    assert 'id="contact"' in raw
    visible = _visible(raw)
    assert "Iman Rammal" in visible
    assert "+974" in visible
    assert "iman.rammal@gmail.com" in visible
    for url in (
        "https://www.youtube.com/@Welcome2Sawa",
        "https://t.me/ImanSawa",
        "https://www.facebook.com/pretty.ammoona",
        "https://x.com/imanrammal",
    ):
        assert url in raw, url


def test_the_about_page_carries_the_contact_details():
    import vid_trans_app

    for lang in ("en", "ar"):
        about = vid_trans_app.TR[lang]["help_about"]
        assert "iman.rammal@gmail.com" in about, lang
        assert "+974" in about, lang
        assert "https://t.me/ImanSawa" in about, lang


def test_html_path_points_at_the_documents():
    import vt_help

    for lang in ("en", "ar"):
        for kind in ("guide", "shortcuts"):
            path = vt_help.html_path(lang, kind)
            assert path and Path(path).is_file(), (lang, kind)
            assert Path(path).name == vt_help.HTML_KINDS[kind]


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_shortcut_and_label_of_the_program_is_documented(lang, qapp, profile):
    win = _window(qapp, profile, lang)
    try:
        raw = _read(lang, "shortcuts.html")
        visible = _visible(raw)
        normed = _norm(visible)
        pairs = _shortcuts_of(win)
        assert len({shortcut for shortcut, _ in pairs}) >= 30, lang
        for shortcut, label in pairs:
            assert shortcut in visible, (lang, shortcut)
            assert _norm(label) in normed, (lang, label)
        assert "Alt+F4" in visible, lang
        assert "F5" in visible, lang
    finally:
        win.deleteLater()
        qapp.processEvents()


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_shortcut_file_lists_only_shortcuts_the_program_has(lang, qapp, profile):
    win = _window(qapp, profile, lang)
    try:
        real = _real_keys(win)
        assert len(real) >= 33, real
        tokens = set(KEY_TOKEN.findall(_visible(_read(lang, "shortcuts.html"))))
        assert tokens, "the file must show key notation"
        assert tokens <= real, sorted(tokens - real)
        assert {"Ctrl+O", "F5", "Alt+F4"} <= tokens, lang
    finally:
        win.deleteLater()
        qapp.processEvents()


def test_the_help_menu_offers_both_files_and_they_open(qapp, profile, monkeypatch):
    import vt_help
    import vid_trans_app

    win = vid_trans_app.MainWindow("en")
    try:
        texts = []
        for menu_action in win.menuBar().actions():
            menu = menu_action.menu()
            if menu is None:
                continue
            for action in menu.actions():
                if not action.isSeparator() and action.menu() is None:
                    texts.append(action.text())
        assert win.t("act_guide_file") in texts
        assert win.t("act_shortcuts_file") in texts

        opened = []
        announced = []
        monkeypatch.setattr(vt_help, "open_html", lambda path: opened.append(path) or True)
        monkeypatch.setattr(win, "announce", announced.append)

        assert win.open_guide_file() is True
        assert win.open_shortcut_file() is True
        assert len(opened) == 2
        for path in opened:
            assert path and Path(path).is_file(), path
        assert announced == [win.t("msg_help_file_open")] * 2

        # a document that cannot be found is announced, never raised
        monkeypatch.setattr(vt_help, "html_path", lambda lang, kind: None)
        assert win.open_guide_file() is False
        assert announced[-1] == win.t("msg_help_file_missing")
    finally:
        win.deleteLater()
        qapp.processEvents()
