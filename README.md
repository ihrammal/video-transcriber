# Accessible Media Transcriber

A Windows desktop program by Iman Rammal that turns audio and video into transcripts and captions. It
hears the speech, writes it down with timestamps, translates it, lets you edit
every line in a plain text area, and burns the result back into the video.

The program is built for screen readers and keyboard-only use, with named
controls, visible focus, progress announcements and an English/Arabic interface.
Arabic uses a right-to-left layout. See the accessibility review for verified
coverage and the remaining reader-specific checks.

## What it does

Version 1.4 supports audio and video, batch transcription, recovery of unfinished
transcripts, adjustable text size, and optional welcome and farewell messages
that close within three seconds. Preferences share one tabbed window (Ctrl+,).
General, Speech and translation, API keys, and Accessibility pages work with
the mouse, arrow keys on the tabs, and Ctrl+Tab/Ctrl+Shift+Tab from any page.
Turn off **Read control hints and details** on the Accessibility page to
reduce screen-reader speech while keeping names, values and essential messages.
See [release notes](RELEASE_NOTES.md), the [accessibility review](ACCESSIBILITY_REVIEW.md),
and the [screen-reader test record](SCREEN_READER_TESTING.md).

Transcribe. The program extracts the audio with ffmpeg and writes timestamped
captions. The free offline Whisper engine needs no key and no account. You can
also use OpenAI, Groq or Google Gemini when you bring your own key.

Translate. The captions can be translated into another language, or you can
keep both lines stacked. The free online translator needs an internet
connection. A cloud engine uses your key instead.

Edit. The whole transcript sits in a plain text area, one caption per line.
Your caret and focus are never taken away while the text is redrawn, and
changing the number of lines asks for confirmation first.

Timestamps. Ctrl+Shift+T writes every segment as a timing line or as plain
text. The choice is remembered and decides what a text export contains. Real
`.srt` files always keep their timing.

Export. Ctrl+S saves a clean `.srt` or `.txt` file. Ctrl+E saves the captions
and burns them into a copy of the video. Ctrl+R renders the subtitles into a
new MP4.

Help. F1 opens the combined user guide in your browser: one document with a
contents list, the full shortcut list, installation and update-checking
topics, written in English or Arabic to match the interface
(`help\user_guide.html` and `help\user_guide_ar.html`). The Help menu also
offers Check for Updates (Ctrl+U), the detailed topic files under
`resources\help`, and Open Log Folder (Ctrl+Shift+V).
Report a Problem (Ctrl+Shift+B) offers email to iman.rammal@gmail.com,
copying the address, or GitHub reporting. Email opens a draft for review.

## Who it is for

People who need captions on a video and want to work entirely from the
keyboard: teachers and trainers making lessons accessible, translators and
transcribers, video creators adding subtitles, and anyone preparing material
for deaf or hard-of-hearing viewers. The program is also meant to be usable
without sight, so screen reader users can do the whole job alone.

## Accessibility

Every control has an accessible name and a description read by screen readers.
Keyboard focus is always visible and can be made thicker. Progress is
announced rather than only shown. Sound feedback can be turned off. High
contrast, a simpler main layout and larger interface text are available from
Ctrl+Shift+A. The interface language can be English or Arabic, and Arabic is
displayed right to left. Progress bars, tables and status messages are read
aloud in order.

## System requirements

Windows 10 or newer, 64 bit.

Python 3.11 to 3.14 if you run it from source. The installer carries its own
Python, so a released install does not need Python at all.

Allow disk space for the program, the selected model and each exported video.
Model sizes are approximately 75 MB (Tiny), 145 MB (Base), and 484 MB (Small).

Custom installation offers Tiny, Base and Small models for offline transcription,
or an API-only installation. Express installation selects Base automatically.
An internet connection is needed for optional model downloads, for the free
translation engine, and for any cloud engine. Transcription with the local
engine works offline as soon as its model is installed.

## Install

The easiest route is the installer from the GitHub Releases page. Download
`AccessibleMediaTranscriber_Setup_<version>.exe`, run it, and follow the
prompts. Express uses the default folder and a Start menu shortcut. Custom lets
you choose the destination, Start menu and desktop shortcuts, and an offline model.
It puts the program, the selected model, ffmpeg, the licence texts and both
help files into one folder, and it removes them cleanly on uninstall. Setup
finds an older 1.1 installation and offers to remove it; your settings,
sounds and downloaded models are kept.

Settings, logs, temporary files and downloaded models live together in
`%LOCALAPPDATA%\Accessible Video Transcriber`, which is writable for normal
users. Nothing is written next to the program.

The compiled program and the installer are shared through GitHub Releases,
not through the source code in this repository.

## Run from source

Open a terminal in this folder, then:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python vid_trans_app.py
```

`requirements.txt` pins every library to the exact version the program was
tested with. Details about Python, ffmpeg, ffprobe, Inno Setup and the model
download are in `EXTERNAL-TOOLS.md`.

Useful flags:

`--welcome` shows the first-run welcome message again.

`--selftest` checks audio, model and translation without opening a window.
It needs the Whisper model to be present, so run it after the first
transcription, or copy a `models` folder next to the sources. On a fresh
clone it reports one failure, "bundled speech model", and passes everything
else.

`--e2e video [none|en|ar] [local|gemini|groq|openai]` runs the whole task
headless, writes `e2e-report.txt` into the user data folder, and exits 0 only
when it worked. With `none` no network is needed.

The test suite runs with `pytest tests -q`. It works headless, writes only
into temporary folders, and never touches your real API keys.

## Add an API key

Open Preferences with Ctrl+, then choose the API keys tab. Each
provider, OpenAI, Groq and Google Gemini, has its own row with a Key for box,
a Show key button, a Test key button and a Get API key button that opens the
provider's own key page.

Paste the key and save. The key goes into the Windows Credential Manager,
the same store Windows uses for saved passwords. It is never written into
`prefs.json` or printed into the log. Keys are hidden by default in the interface;
the Show key button lets you inspect a saved key.
Old copies left in a plain text preferences file are moved out automatically
the first time the program loads them.

You can also set a key for one engine only and keep the free local engine for
the other task. When a chosen engine has no key, the program names the
missing provider and offers to open the preferences for you. Nothing is sent
anywhere until you press Start.

If you prefer environment variables over a settings dialog, the program does
not read keys from them. Use the preferences screen instead.

## Build the program and the installer

Requirements: Python 3.11 or newer with `requirements.txt` installed, and
Inno Setup 6 or 7 for the installer step.

```
build.bat              full build: exe, self test, installer
build.bat --fast       skip the self test and the installer verification
build.bat --no-inno    build and test the exe only
build.bat --test       run the pytest suite only
```

Outputs:

`dist\AccessibleVideoTranscriber\AccessibleVideoTranscriber.exe` is the
application.

`installer_output\AccessibleVideoTranscriber_Setup_<version>.exe` is the
installer.

The installer ships the `models\tiny`, `models\base` and `models\small` recognition models, a standalone
`ffmpeg.exe`, both licence texts and the help folders, so the first
transcription works without a network connection.

## Keyboard shortcuts

Press F1 inside the program for the full guide, Ctrl+/ for the shortcut list,
Ctrl+Shift+G for the licence, and F12 for About.

The main shortcuts are:

Ctrl+O open a video

F5 start the task

Ctrl+S save the captions

Ctrl+E export subtitles and video

Ctrl+Shift+T show timestamps

Ctrl+R render a new video

Ctrl+, settings

Ctrl+Shift+A accessibility settings

Ctrl+Shift+V open the log folder

Ctrl+Q exit

Every shortcut is also listed in words and key notation behind
Help, then Open Shortcut File.

## Known issues

The program runs on Windows only. It uses the Windows Credential Manager,
Windows sounds and Windows fonts, so it does not run on macOS or Linux.

The installer bundles multilingual Whisper Tiny, Base and Small. Local
transcription works without an internet connection or API key.

The free translation engine needs an internet connection and has no offline
mode.

The local Whisper `base` model is small and fast, so background noise, music,
overlapping speakers and strong accents produce mistakes. Choose a different
model under Settings, or fix a line in the editor, or use a cloud engine.

Transcription runs on the CPU. Long videos take a long time, and the window
stays responsive while it works.

Rendering writes a copy of the video, so it needs as much free disk space as
the original file.

Cloud engines limit how much audio they accept in one upload. The program
compresses the audio before sending, but very long videos may still be
rejected by the provider.

## Report a problem

Write to iman.rammal@gmail.com, in English or Arabic.

Before you write, open Help then Open Log Folder with Ctrl+Shift+V and attach
the newest log file. Say which Windows version you use, whether you ran the
installer or the source, which engine was selected, and what you did before
the problem appeared. The About page on F12 has the program version.

Questions about shortcuts are answered in the Keyboard Shortcuts topic of the
help and in the shortcut file.

## Licence

Non-commercial only, in two places.

The source code in this repository is under the PolyForm Noncommercial
Licence 1.0.0, full text in `LICENSE`. In plain terms: you may read it,
change it, run it and share it for personal, educational, research or other
non-commercial use, as long as the copyright notice and the licence travel
with any copy you pass on. Commercial use of any kind is not allowed.

The built program additionally carries the end user agreement shown by the
installer: `resources/agreement_en.txt` in English and
`resources/agreement_ar.txt` in Arabic. Press Ctrl+Shift+G inside the program
to read it.

Other people's work used by this program keeps its own licence. The full list
is in `THIRD-PARTY-LICENSES.md`.

## Author

Iman Rammal

- Braille Training Specialist
- NVDA Certified Expert
- Microsoft Word with NVDA Certified Expert
- JAWS Certified
- Assistive technology trainer
- Translator / interpreter

Email: iman.rammal@gmail.com

- YouTube: https://www.youtube.com/@ihrammal
- Telegram: https://t.me/ihrammal
- Facebook: https://www.facebook.com/ihrammal
- X: https://x.com/ihrammal
- TikTok: https://tiktok.com/ihrammal
