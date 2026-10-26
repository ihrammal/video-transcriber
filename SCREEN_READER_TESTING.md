# Screen-reader test record

## 26 October: user-reported Settings issue

The user reported unnamed “grouping” stops on Settings pages and an ambiguous startup-check label. Scroll areas and their content no longer take keyboard focus; both have localized page names. Instructions explain Tab/Shift+Tab for controls, Space for checkboxes, and arrows for tab selection. The automatic-check label explicitly mentions updates in both languages. All 159 regression tests passed, including focus traversal from the tab bar into General in English and Arabic and compatibility of the renamed installer with update checking.

Live Windows accessibility inspection exposed the corrected English and Arabic update labels and named General pages. The rebuilt application's eleven checked modules match current source, and its offline transcription/render self-test passed. The isolated 1.3.1 installer passed fresh install, upgrade, shortcuts, API-only installation and uninstall. Fresh NVDA speech for the reported issue remains pending: automatic approval review rejected replacing the active reader without explicit permission. No replacement was attempted after that rejection. These observations do not establish a new spoken-output pass.

## Verified in this continuation

All 146 automated tests passed in 28.97 seconds. Existing fixes and settings were preserved. The rebuilt executable also passed its packaged self-test with model downloads disabled, including offline model transcription and video rendering.

NVDA 2026.2 ran with a separate test profile. Its diagnostic log recorded these app-specific speech strings:

- English application title and the source-recording group.
- “Choose audio or video”, button role, and the hint describing the recording selection.
- “Preferences”, dialog role, its explanation, and tab-navigation instructions.
- General, Speech and translation, API keys, and Accessibility tab labels.
- Arabic open-media label «اختيار صوت أو فيديو» and ready-status message.
- Arabic Preferences dialog «التفضيلات», explanation and navigation instructions.
- Arabic Accessibility tab «إمكانية الوصول».

Windows accessibility inspection also exposed the Arabic contrast, focus, simplified layout, progress, sound, hint, welcome and farewell checkboxes. Both greeting labels specify a three-second maximum. Ctrl+, opened Preferences, and Ctrl+Shift+A opened its Accessibility page. Ctrl+Shift+1/2 switched the interface language.

The ignored local evidence is test-results/nvda-oct25.log. It also contains unrelated desktop events, so it must not be distributed as a public test artifact. This document intentionally records only app-related observations.

## Email-reporting addition

All 154 regression tests passed after adding email reporting. The tests check the recipient, encoded English/Arabic draft subjects, the no-email-app fallback, copying the address, the existing GitHub option, and the menu shortcut. Tests mock external launches and clipboard access; no message is sent.

A separate live NVDA 2026.2 check of the new dialog recorded its English and Arabic titles, support-email label and value, and email button. The Arabic copy-address button was also announced. Escape returned focus to the transcript editor, and the clean preview exited with Ctrl+Q. No email action was activated during the live test. Raw evidence remains in the ignored test-results/nvda-report-email.log.

TextBridge already has email reporting to iman.rammal@gmail.com. The published TextBridge.dll was inspected directly: its email-draft method targets that address and preserves Arabic text, and its compiled reporting form contains the address and Email Report button. Its existing form also provides Save and Copy. No changes to TextBridge were needed, and no draft was launched or sent during verification.

The Media Transcriber package check now includes help_menu as an eleventh module. All eleven modules match the updated source, and the rebuilt executable passed its offline self-test.

## Limits and remaining checks

- The log records text sent to the synthesizer; Arabic pronunciation and voice switching need a listening test. The test reader used an English default voice.
- The Windows automation tool reported stale focus and element indexes in the native file picker. Path entry did not verify successfully. This does not establish an application defect, but prevents claiming a complete keyboard/speech workflow.
- JAWS 2026 launched, but no reliable Speech History evidence was captured. JAWS remains unverified. Its documented history shortcut is INSERT+SPACE, then H: https://support.freedomscientific.com/teachers/lessons/5.5.1_SpeechHistory.htm
- Narrator, installed-wizard speech, cancellation, recovery, transcript editing/export and timed-greeting focus restoration still need spoken-output checks.
- Do not treat these results as accessibility conformance certification.

## Packaging check

A comparison of the previous package with current source found that its translation table lacked the newly added English/Arabic shortcut_hint label. The application was rebuilt, and the new verification script confirmed matching code for all ten checked modules, including both translation tables. The release build now runs this comparison before creating an installer so stale application code stops the build.

The refreshed AccessibleMediaTranscriber_Setup_1.4.0.exe compiled successfully. Both version-specific checksum files were updated to match it. The local release summary is test-results/release-screenreader-oct25.json.

## Updated author information and further reader attempts

The updated personal-information document was used only as factual source material. The public author profile includes the updated qualifications, email and five social links; the user's explicit instruction excludes the personal telephone number. The author changes were published to the video-transcriber and textbridge GitHub repositories. Both local applications and installers were rebuilt. Media Transcriber's 154 tests and packaged self-test passed; TextBridge's 20 focused English/Arabic author-panel checks passed.

On 25 October the user confirmed the braille-display test. Record this as user-confirmed, without inferring an unspecified reader version, hardware model, or broader test coverage.

The next JAWS attempt started a background process, but no targetable JAWS window or response to the documented Insert+J and numpad modifier command was obtained. Windows denied closing that test process through the connection. Narrator's computer-use app-access approval timed out. The user was asked to close JAWS manually and approve Narrator access. Neither attempt is counted as a reader pass.
