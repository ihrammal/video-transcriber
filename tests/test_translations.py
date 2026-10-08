"""Translation table integrity: nothing missing, nothing untranslated."""

from __future__ import annotations

import ast
import io
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load_tr(path: pathlib.Path) -> dict:
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "TR":
                    return ast.literal_eval(node.value)
    raise AssertionError("no TR table in %s" % path)


def test_english_and_arabic_have_the_same_keys():
    for name in ("vid_trans_app.py", "vt_i18n.py"):
        tr = _load_tr(ROOT / name)
        assert set(tr["en"]) == set(tr["ar"]), name


def test_no_duplicate_keys_in_the_source():
    for name in ("vid_trans_app.py", "vt_i18n.py"):
        tree = ast.parse(io.open(ROOT / name, encoding="utf-8").read())
        for node in tree.body:
            if not (
                isinstance(node, ast.Assign)
                and getattr(node.targets[0], "id", "") == "TR"
            ):
                continue
            for lang_node, table in zip(
                [k.value for k in node.value.keys], node.value.values
            ):
                if lang_node not in ("en", "ar"):
                    continue
                keys = [k.value for k in table.keys]
                dupes = sorted({k for k in keys if keys.count(k) > 1})
                assert not dupes, "%s/%s duplicates: %s" % (name, lang_node, dupes)


def test_placeholders_match_between_languages():
    for name in ("vid_trans_app.py", "vt_i18n.py"):
        tr = _load_tr(ROOT / name)
        for key, english in tr["en"].items():
            arabic = tr["ar"].get(key, "")
            if not isinstance(english, str) or not isinstance(arabic, str):
                continue
            if "<" in english:  # help pages are markup, wording differs
                continue
            want = set(re.findall(r"\{(\w+)\}", english))
            got = set(re.findall(r"\{(\w+)\}", arabic))
            assert want == got, "%s: %s placeholders en=%s ar=%s" % (name, key, want, got)


def test_every_referenced_key_exists():
    keys = set()
    simple = r"\"(\w+)\"\s*[,)]"  # a literal key, never a concatenated prefix
    for filename in ("vid_trans_app.py", "vt_a11y.py"):
        text = io.open(ROOT / filename, encoding="utf-8").read()
        keys.update(re.findall(r"\.t\(\s*" + simple, text))
        keys.update(re.findall(r"key_text\(\s*" + simple, text))
        keys.update(re.findall(r"_make_action\(\s*\w+\s*,\s*" + simple, text))
        keys.update(re.findall(r"QGroupBox\(self\.t\(\"(\w+)\"\)", text))

    merged = {}
    for name in ("vid_trans_app.py", "vt_i18n.py"):
        merged.update(_load_tr(ROOT / name)["en"])
    missing = sorted(k for k in keys if k and k not in merged)
    assert not missing, missing


def test_menu_mnemonics_are_unique():
    tr = _load_tr(ROOT / "vid_trans_app.py")["en"]
    menus = [
        tr[k]
        for k in tr
        if k.startswith("menu_") and isinstance(tr[k], str) and "&" in tr[k]
    ]
    letters = [m[m.index("&") + 1].lower() for m in menus if len(m) > m.index("&") + 1]
    assert len(letters) == len(set(letters)), letters


def test_welcome_and_exit_messages_are_exact():
    import vt_setup

    assert vt_setup.WELCOME_TEXT == (
        "Welcome to the Accessible Video Transcriber by Iman Rammal"
    )
    assert vt_setup.FAREWELL_TEXT == (
        "Thank you for using my program, Goodbye."
    )
