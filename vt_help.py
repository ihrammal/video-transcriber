"""vt_help.py -- the in-app help: topic files, search and the shortcut list.

The help text lives in plain Markdown files next to the other resources::

    resources/help/en/<topic>.md
    resources/help/ar/<topic>.md

Each file starts with a level-one heading (the topic title) followed by
level-two headings and plain paragraphs.  Nothing of the markup reaches the
screen: the loader strips it before the text is shown, so the same files
stay easy to edit by hand.

The Keyboard Shortcuts topic is completed at run time from the actions the
program really has, so the list can never drift away from the shortcuts.

Next to the topics the folder also holds two detailed HTML documents with
real headings (``guide.html`` and ``shortcuts.html``, one pair per
language).  They are what Help -> Open Guide File shows in the browser,
where a screen reader can jump from heading to heading.
"""

from __future__ import annotations

import io
import os
import sys

# The order of the contents list; also the file names (without .md).
TOPIC_ORDER = (
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

# The two detailed HTML documents: kind -> file name.
HTML_KINDS = {
    "guide": "guide.html",
    "shortcuts": "shortcuts.html",
}

# "Ctrl+Shift+N" -> "Control plus Shift plus N"
_KEY_WORDS = {
    "ctrl": "Control",
    "control": "Control",
    "shift": "Shift",
    "alt": "Alt",
    "meta": "Windows",
    "super": "Windows",
    "del": "Delete",
    "delete": "Delete",
    "ins": "Insert",
    "insert": "Insert",
    "pgup": "Page Up",
    "pgdn": "Page Down",
    "left": "Left arrow",
    "right": "Right arrow",
    "up": "Up arrow",
    "down": "Down arrow",
    "esc": "Escape",
    "escape": "Escape",
    "return": "Enter",
    "enter": "Enter",
    "space": "Space bar",
    "tab": "Tab",
    "backspace": "Backspace",
    "home": "Home",
    "end": "End",
    ",": "comma",
    "/": "slash",
    ".": "period",
    "-": "minus",
    "=": "equal sign",
    ";": "semicolon",
    "'": "apostrophe",
    "[": "left bracket",
    "]": "right bracket",
    "\\": "backslash",
    "+": "plus",
}


def _help_dir(lang):
    lang = lang if lang in ("en", "ar") else "en"
    try:
        import vt_bootstrap

        return vt_bootstrap.resource_path("resources", "help", lang)
    except Exception:  # noqa: BLE001 - a source tree run without bootstrap
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "resources", "help", lang
        )


def html_path(lang, kind):
    """The absolute path of a detailed HTML help file ("" when it is missing).

    The installed program looks next to its own executable first, so the
    file the installer ships in ``help\\<lang>`` stays on disk for the
    user to open at any time; the bundled copy and the source tree are
    the fallbacks.
    """
    lang = lang if lang in ("en", "ar") else "en"
    if kind not in HTML_KINDS:
        return ""
    name = HTML_KINDS[kind]
    candidates = []
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(os.path.join(exe_dir, "help", lang, name))
    try:
        import vt_bootstrap

        candidates.append(vt_bootstrap.resource_path("resources", "help", lang, name))
    except Exception:  # noqa: BLE001 - a source tree run without bootstrap
        pass
    candidates.append(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "resources", "help", lang, name)
    )
    for path in candidates:
        if os.path.isfile(path):
            return path
    return ""


def open_html(path):
    """Show an HTML file in the system browser.  True when it was started."""
    if not path or not os.path.isfile(path):
        return False
    try:
        os.startfile(path)  # opens the document for the user
        return True
    except Exception:  # noqa: BLE001 - unusual systems fall back to a browser
        try:
            import webbrowser

            return bool(webbrowser.open("file:///" + path.replace("\\", "/")))
        except Exception:  # noqa: BLE001 - nothing left to try
            return False


def read_topic(lang, topic_id):
    """The raw Markdown of one topic file ("" when the file is missing)."""
    if topic_id not in TOPIC_ORDER:
        return ""
    path = os.path.join(_help_dir(lang), topic_id + ".md")
    try:
        with io.open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except Exception:  # noqa: BLE001 - a missing file shows an empty topic
        return ""


def plain(text):
    """Markdown -> the plain text that is shown in the text area.

    Hashes, asterisks, backticks and link targets never reach the screen,
    so a screen reader reads sentences, not formatting symbols.
    """
    out = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            stripped = stripped[3:].strip()
            if out and out[-1] != "":
                out.append("")
            out.append(stripped)
            out.append("")
            continue
        if stripped.startswith("# "):
            stripped = stripped[2:].strip()
        if stripped.startswith(("- ", "* ")):
            stripped = stripped[2:].strip()
        # [label](target) -> label ; **bold** / *italic* / `code` -> plain
        while "[" in stripped and "](" in stripped:
            try:
                open_at = stripped.rindex("[", 0, stripped.index("]("))
                close_at = stripped.index("](", open_at)
                target_end = stripped.index(")", close_at + 2)
                label = stripped[open_at + 1:close_at]
                stripped = stripped[:open_at] + label + stripped[target_end + 1:]
            except ValueError:
                break
        for token in ("**", "*", "`"):
            stripped = stripped.replace(token, "")
        out.append(stripped)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out).strip()


def _split_title(raw):
    lines = (raw or "").splitlines()
    title = ""
    body_lines = lines
    if lines and lines[0].strip().startswith("# "):
        title = lines[0].strip()[2:].strip()
        body_lines = lines[1:]
    return title, "\n".join(body_lines).strip()


def key_words(sequence):
    """"Ctrl+Shift+N" -> "Control plus Shift plus N" (readable words)."""
    if not sequence:
        return ""
    parts = [part for part in str(sequence).split("+") if part != ""]
    words = []
    for part in parts:
        low = part.lower()
        if low in _KEY_WORDS:
            words.append(_KEY_WORDS[low])
        elif len(part) == 1:
            words.append(part)
        else:
            words.append(part)
    return " plus ".join(words)


def shortcut_groups(window):
    """[(group heading, [(action label, shortcut in words)])] from the menus.

    The groups and the shortcuts are read from the running program, so the
    help can never list a shortcut the program does not have.
    """
    groups = []
    for menu_action in window.menuBar().actions():
        menu = menu_action.menu()
        if menu is None:
            continue
        rows = []
        for action in menu.actions():
            if action.isSeparator() or action.menu() is not None:
                continue
            sequence = action.shortcut().toString()
            if not sequence:
                continue
            label = action.text().replace("&", "").replace("&&", "&")
            rows.append((label, key_words(sequence)))
        if rows:
            groups.append((menu_action.text().replace("&", ""), rows))
    extras = []
    start = getattr(window, "start_button", None)
    if start is not None and not start.shortcut().isEmpty():
        extras.append(
            (window.t("btn_start"), key_words(start.shortcut().toString()))
        )
    extras.append((window.t("act_close_window"), key_words("Alt+F4")))
    if extras:
        groups.append((window.t("short_group_main"), extras))
    return groups


def shortcuts_text(window):
    """The generated shortcut list, one shortcut per line, in words."""
    lines = []
    for heading, rows in shortcut_groups(window):
        if lines:
            lines.append("")
        lines.append(heading)
        for label, words in rows:
            lines.append("%s: %s" % (label, words))
    return "\n".join(lines)


def build_topics(lang, window=None):
    """Every topic as {"id", "title", "body"} with the markup stripped."""
    topics = []
    for topic_id in TOPIC_ORDER:
        title, body = _split_title(read_topic(lang, topic_id))
        if topic_id == "shortcuts" and window is not None:
            body = (body + "\n\n" + shortcuts_text(window)).strip()
        topics.append(
            {
                "id": topic_id,
                "title": title or topic_id,
                "body": plain(body),
            }
        )
    return topics


def search(topics, query):
    """[(topic id, title, matching line)] for a word, case insensitive."""
    query = (query or "").strip().lower()
    if not query:
        return []
    found = []
    for topic in topics:
        haystack = [topic["title"]] + topic["body"].splitlines()
        for line in haystack:
            if query in line.lower():
                snippet = " ".join(line.split())
                if len(snippet) > 110:
                    at = snippet.lower().find(query)
                    start = max(0, at - 40)
                    snippet = ("..." if start else "") + snippet[start:start + 110]
                found.append((topic["id"], topic["title"], snippet))
                break
    return found
