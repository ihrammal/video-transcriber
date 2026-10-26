# Release checks for 1.3.1

Run the complete tests in `tests/`, build the application, verify packaged sources and run the packaged offline self-test. Compile the isolated QA installer and verify fresh installation, upgrade, shortcut choices and uninstall before compiling the public installer.

Verify English and Arabic Settings navigation: arrows select tabs; Tab and Shift+Tab reach controls; Space changes checkboxes. The automatic-check label must explicitly mention updates. Scroll containers must not take keyboard focus. Confirm the renamed application remains discoverable through the existing GitHub updater and retains the previous installation identity and profile.

Keep private recordings, transcripts, reader logs, test profiles, comparison dependencies and QA installers out of release assets. Publish only the public installer, checksum and release notes. Retain source and useful validation evidence locally until publication is verified.

Reader observations and their limits are recorded in SCREEN_READER_TESTING.md. Automated accessibility checks do not establish spoken-output compatibility with every reader.
