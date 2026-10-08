# Changelog

All notable changes to Accessible Video Transcriber are listed here.
The format follows Keep a Changelog, and the project uses Calendar Versioning
numbers of the form major.minor.patch.

## 1.2 - 2026-10-07

Release tag: v1.2.0. Installer: AccessibleVideoTranscriber_Setup_1.2.0.exe.

### Added

- Check for Updates. The Help menu now checks the GitHub Releases page for a
  newer version, shows a clear message when the program is up to date, and
  offers to download a newer version when one exists (Ctrl+U).
- Check Automatically at Startup (Ctrl+Shift+U). When it is on, the program
  checks for a new version quietly once a day, a few seconds after the window
  opens, so startup is never slowed down and the screen reader is not
  interrupted. The setting can be turned off from the same menu.
- Installation in the Program Files folder. The new Inno Setup installer
  installs into the 64-bit Program Files folder and asks whether to install
  for all users or for the current user only.
- Removal of the older AppData copy. Setup finds the previous per-user
  installation, offers to remove it, and removes it through its own
  uninstaller so no old copy is left behind. Settings and saved files in the
  user data folder are kept.
- Reorganized Help menu. The items now appear in a fixed order: User Guide,
  Keyboard Shortcuts, Check for Updates, Check Automatically at Startup,
  Release Notes on GitHub, Report a Problem, License Agreement, About, then
  Open Guide File, Open Shortcut File and Open Log Folder. Every item has a
  different access letter and works with the keyboard alone.
- Combined help guide. The long user guide and the full shortcut list are
  merged into one document, help/user_guide.html with its Arabic twin
  help/user_guide_ar.html, with a table of contents at the
  top, a section for checking for updates, the automatic update setting,
  the installation options and the organized Help menu.

### Changed

- The version is now 1.2 (1.2.0 in the installer, the executable and the
  update checker).
- User Guide (F1), Keyboard Shortcuts (Ctrl+/) and License Agreement
  (Ctrl+Shift+G) open the right section of the combined help guide.
- Release Notes on GitHub (Ctrl+Shift+R) and Report a Problem (Ctrl+Shift+B)
  open the project's release and issue pages.
- Settings, accessibility flags, logs and the update preference are kept in
  one user data folder, %LOCALAPPDATA%\Accessible Video Transcriber, which is
  writable for normal users. Version 1.1 settings are read from their old
  location and moved there, so nothing is lost when upgrading.
- Downloaded Whisper models are stored under the user data folder instead of
  any program folder.
- The program is built as a folder build, so the help folder, Whisper, the
  libraries and ffmpeg travel together inside dist\AccessibleVideoTranscriber.

### Notes

- The program stays free for noncommercial use only. See the License
  Agreement in the Help menu.
