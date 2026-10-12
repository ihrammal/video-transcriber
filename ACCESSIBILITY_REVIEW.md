# Review for the 1.3 update

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
