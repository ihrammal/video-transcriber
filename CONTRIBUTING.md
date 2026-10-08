# Contributing

Thank you for wanting to improve this program. It is written and maintained
by Iman Rammal, and it is built first for people who work with a screen
reader, a braille display or the keyboard alone. Anything that keeps that
promise is welcome.

## Getting started

You need Windows 10 or newer and Python 3.11 to 3.14.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python vid_trans_app.py
```

`requirements.txt` pins exact versions. Change a version only when the change
is part of what you are submitting, and say why in the description.

`EXTERNAL-TOOLS.md` explains ffmpeg, ffprobe, Inno Setup and the model
download.

## Running the checks

```
pytest tests -q
```

or `build.bat --test` for the same thing from a command prompt.

The suite runs headless with the Qt `offscreen` platform, writes only into
temporary folders, and replaces the Windows Credential Manager with an
in-memory stand-in, so your real API keys are never touched.

Run the full build before you hand work over:

```
build.bat
```

That produces the exe, runs its self test and compiles the installer.

## Rules that matter in this codebase

Keep the settings and preference modules importable with the standard
library only. `vt_prefs.py`, `vt_i18n.py` and friends must open even when
PyQt6 or the network packages are missing.

Every new control needs an accessible name and an accessible description,
in English and in Arabic. `vt_a11y.py` holds the helpers. A control without
a description is not finished.

Never take focus away from someone who is typing. Text redraws keep the
caret where it was, and a change in the number of caption lines asks first.

New strings go into the `TR` table in `vid_trans_app.py` or `vt_i18n.py`,
in both `en` and `ar`, with the same placeholders in both. The test suite
fails on a missing key, a duplicate key or a placeholder that only exists in
one language.

Help topics live in `resources\help\en` and `resources\help\ar` as Markdown
files with the same file names on both sides, plus the generated HTML files.
Write real headings so a screen reader can jump between them.

Keyboard shortcuts are described in words as well as in key notation, for
example "Control plus O".

API keys belong in the Windows Credential Manager through `vt_secrets.py`,
never in `prefs.json`, never in the log, never in a commit. If you need a
key for a test, use the `fake_secrets` fixture in `tests/conftest.py`.

## Writing a change

Small, focused changes are easier to review than a large one. Say what the
change does, why it is needed, and how you checked it. Include the output of
`pytest tests -q` when the tests are affected.

Style: follow the file you are editing. Modules carry a short docstring that
says what the file is for, constants are upper case, and error handling
reports problems instead of raising where the program must keep running.

## Licence

This project is under the PolyForm Noncommercial Licence 1.0.0, see
`LICENSE`. By sending a change you agree to place it under the same licence,
with the same copyright notice. Third-party components keep their own terms,
listed in `THIRD-PARTY-LICENSES.md`.

If your employer cannot accept a non-commercial licence, say so before you
start, so nothing has to be undone later.
