"""The combined help guide in help/user_guide[_ar].html.

The Help menu opens it: F1 for the whole guide, Ctrl+/ for the Keyboard
Shortcuts section, Ctrl+Shift+G for the License Agreement section, so the
anchors help_menu.py jumps to must exist in both languages, the table of
contents must resolve, and the features new in 1.2 must be described.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELP = ROOT / "help"
GUIDES = ("user_guide.html", "user_guide_ar.html")

PHRASES = {
    "user_guide.html": (
        "Check for Updates",
        "Check Automatically at Startup",
        "Release Notes on GitHub",
        "Report a Problem",
        "Installing the program",
    ),
    "user_guide_ar.html": (
        "التحقق من التحديثات",
        "التحقق التلقائي عند بدء التشغيل",
        "ملاحظات الإصدار على GitHub",
        "الإبلاغ عن مشكلة",
        "تثبيت البرنامج",
    ),
}


def _read(name: str) -> str:
    return (HELP / name).read_text(encoding="utf-8")


def test_both_guides_exist_and_look_like_documents():
    for name in GUIDES:
        raw = _read(name)
        assert raw.lstrip().startswith("<!DOCTYPE html>"), name
        assert '<meta charset="utf-8">' in raw, name
        assert "<title>" in raw
        assert "<script" not in raw.lower(), name
        assert "1.2" in raw, name


def test_the_anchors_help_menu_jumps_to_exist():
    import help_menu

    for lang, name in (("en", "user_guide.html"), ("ar", "user_guide_ar.html")):
        raw = _read(name)
        assert 'id="shortcuts"' in raw, name
        assert 'id="license"' in raw, name
        path = help_menu.guide_path(lang)
        assert path and path.is_file(), lang
        assert path.name == name
        assert path.parent == HELP


def test_every_link_and_id_of_the_guides_resolves():
    for name in GUIDES:
        raw = _read(name)
        ids = re.findall(r'id="([^"]+)"', raw)
        assert len(ids) == len(set(ids)), (name, sorted(ids))
        hrefs = set(re.findall(r'href="#([^"]+)"', raw))
        assert hrefs <= set(ids), (name, sorted(hrefs - set(ids)))
        assert 'href="#shortcuts"' in raw, name
        assert 'href="#license"' in raw, name


def test_the_features_new_in_1_2_are_described():
    for name, phrases in PHRASES.items():
        raw = _read(name)
        for phrase in phrases:
            assert phrase in raw, (name, phrase)


def test_the_two_guides_link_to_each_other():
    assert 'href="user_guide_ar.html"' in _read("user_guide.html")
    assert 'href="user_guide.html"' in _read("user_guide_ar.html")
