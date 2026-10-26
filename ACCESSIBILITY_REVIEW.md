# Review for the 1.4 update

## Verification on 24–25 October 2026

- All 154 automated tests passed, including the language-switch fix and email-reporting checks. Coverage includes English/Arabic labels, preferences and tab navigation, optional three-second greetings and saved greeting checkboxes, a clean exit without an extra confirmation, recovery, batch processing, and real audio-to-video rendering.
- The new Report a Problem dialog was checked with NVDA in English and Arabic. Its speech log includes the dialog title, support-address label and value, and email action in both languages; the Arabic copy-address action was also announced. Draft generation, failure fallback and copy behavior were tested without opening an email app or sending a message.
- A live Windows accessibility-tree check found an English accessible name left on the drag-and-drop hint after switching to Arabic. The retranslation loop now refreshes explicit names as well as visible text; the language-switch regression test covers this.
- The visual Arabic check found an untranslated editor placeholder. Retranslation now updates it and localizes tooltips. Turning hints off suppresses tooltips too, since Qt can otherwise expose them as fallback accessible descriptions.
- Status messages now use real polite Qt announcement events. Consecutive repeated messages are suppressed, keyboard focus stays in the editor, and result dialogs do not queue a duplicate announcement.
- JAWS 2026 started during the 25 October continuation, but its Speech History could not be captured reliably. JAWS spoken output remains unverified.
- The final packaged executable passed its self-test with model downloads blocked, including actual Tiny, Base and Small transcription. Nine local audio/video recordings also completed transcription, subtitle export and captioned-video rendering with audio and duration checks.
- The isolated QA installer passed fresh installation, upgrade, shortcut selection, API-only installation without a model or unselected shortcuts, and uninstall cleanup. These checks do not replace spoken testing of the installer pages.
- Windows accessibility inspection exposed named main-window controls, including audio/video selection, task/language/engine choices, transcript editing, progress and export. Ctrl+, opened Preferences and exposed its four named tabs and settings controls.
- NVDA 2026.2 was tested on 25 October using an isolated profile. Its speech log confirms the English app title, source group and open-media button/hint; the Preferences dialog and all four tab labels; and Arabic open-media/status text, Preferences and Accessibility tab labels. These are speech-queue observations, not a listening test of Arabic pronunciation. The native file picker exposed stale focus information to the automation tool, so file selection, transcription/export, and the complete spoken workflow remain unverified. See SCREEN_READER_TESTING.md for evidence and limits. Narrator remains unverified. The user confirmed the braille-display test on 25 October; this was not an independent hardware test by the agent.
- Before release, complete spoken-output checks in both languages: open media, navigate every preference tab, choose a model, transcribe, edit, save, cancel, recover work, and exit. Check that focus returns correctly, status is announced once, and greeting dismissal does not strand focus.

Implemented since the previous review: text size choices, a scrollable main layout, optional short greetings, batch processing and transcript recovery. The historical review below records the earlier baseline.

## Previous review: 1.3

The source already provides labelled controls, keyboard shortcuts, editable
captions, visual progress, optional sounds, high contrast and Arabic support.
These features benefit people using a mouse, keyboard, magnification or screen
readers. This review is based on code and Qt tests; it does not certify WCAG
conformance or substitute for NVDA, JAWS and Narrator testing.

Implemented: unified tabbed settings, optional control descriptions, visible
tab-navigation help, saved preferences and removal of duplicate API-test
announcements. Essential labels and result/error messages remain available.
The screen reader controls its own verbosity, so the hints setting cannot
guarantee that every reader speaks identical information.

Recommended next changes:

- Add a saved text-size preference and make the main window scroll or reflow
  at 200% scaling and on small screens. Its current 1120 × 840 initial size
  and fixed font sizes deserve testing with magnification.
- Add a video/caption preview with playback and a highlighted current caption
  to help sighted editors check timing; provide equivalent keyboard controls.
- Keep a clear numbered Choose video → Transcribe → Edit → Export workflow,
  with a visible explanation when an action is unavailable.
- Review status announcements: communicate changed stages and completion,
  avoid repeating unchanged messages and unnecessary application alerts.
- Consider simplifying routine exit: the confirmation and farewell screen add
  steps even when there is no unsaved work.

Before shipping, manually check both languages with NVDA, JAWS and Narrator;
keyboard-only operation; Windows high contrast; 100%, 150% and 200% display
scaling; hints enabled/disabled; and mouse operation. Confirm tab focus and
the saved preference after restarting the installed app.
