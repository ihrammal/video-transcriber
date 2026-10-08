"""vid_trans_app.py

Accessible Windows 11 desktop application (PyQt6 / WCAG 2.1 AA + Windows UI Automation)
that transcribes video audio with faster-whisper, translates subtitles with deep-translator,
lets users edit captions line by line, and either burns styled captions into the video
(moviepy) or exports a clean .srt file. The whole interface is available in English and
Arabic (with full right-to-left layout and translated screen-reader accessibility).

Install (Python 3.14 / Windows 11):

    pip install PyQt6 faster-whisper deep-translator srt moviepy

Run:

    python vid_trans_app.py

Notes:
- Uses moviepy 2.x (Python 3.14 + numpy 2 compatible). The 1.x `moviepy.editor`
  module does not exist in 2.x, so rendering uses the new API:
  `from moviepy import VideoFileClip, CompositeVideoClip, TextClip` and the
  `with_start` / `with_duration` / `with_position` methods.
- First run of faster-whisper downloads the "base" model automatically.
- Every interactive control exposes AccessibleName / AccessibleDescription so that
  NVDA, JAWS and Windows Narrator (and Braille displays) can operate the app fully,
  in the language the user chose (English or Arabic).
"""

import logging
import os
import re
import sys
import tempfile
import time
import traceback
from datetime import timedelta

import srt

TR = {
    "en": {
        "app_title": "Accessible Video Transcriber - Transcribe, translate and subtitle video",
        "grp_video": "1.  Choose a video file",
        "grp_lang": "2.  Languages and translation",
        "grp_process": "3.  Process",
        "grp_editor": "4.  Subtitle editor (line by line, keyboard accessible)",
        "grp_output": "5.  Output",
        "lbl_interface_lang": "Interface language:",
        "iface_en": "English",
        "iface_ar": "Arabic",
        "chk_high_contrast": "High &contrast mode (black and yellow, WCAG AAA)",
        "lbl_audio_lang": "Audio language:",
        "lbl_trans_mode": "Translation mode:",
        "lang_auto": "Automatic detection",
        "lang_en": "English",
        "lang_ar": "Arabic",
        "lang_zh": "Chinese",
        "lang_es": "Spanish",
        "lang_fr": "French",
        "lang_de": "German",
        "lang_hi": "Hindi",
        "lang_ja": "Japanese",
        "lang_pt": "Portuguese",
        "lang_ru": "Russian",
        "trans_ar_en": "Arabic \u2192 English",
        "trans_en_ar": "English \u2192 Arabic",
        "trans_bilingual": "Bilingual stacked (original above, translation below)",
        "lbl_task": "Task:",
        "acc_task_n": "Task",
        "acc_task_d": "Choose what Start does: transcribe the speech into captions, "
        "or translate the captions that are already in the table.",
        "task_transcribe": "Transcribe speech into captions",
        "task_translate": "Translate the captions",
        "lbl_source_lang": "Source language (spoken in the video):",
        "lbl_target_lang": "Target language:",
        "acc_target_n": "Target language",
        "acc_target_d": "The language the captions are translated into. Choose "
        "No translation to keep the original text.",
        "target_none": "No translation (keep the original language)",
        "lbl_engine": "Engine:",
        "acc_engine_n": "Speech engine",
        "acc_engine_d": "Which service does the work. Automatic uses your saved choice "
        "and falls back to the free offline engine when a key is missing.",
        "eng_auto": "Automatic (my saved choice, with automatic fallback)",
        "eng_local": "Local Whisper (free, offline)",
        "eng_openai": "OpenAI API (needs a key)",
        "eng_groq": "Groq API (needs a key)",
        "eng_gemini": "Google Gemini API (needs a key)",
        "btn_start": "&Start",
        "btn_save_results": "&Save results",
        "btn_copy": "&Copy results",
        "acc_start_n": "Start button",
        "acc_start_d": "Runs the task selected in the Task list. Shortcut F5.",
        "acc_cancel_run_n": "Cancel the running task button",
        "acc_save_results_n": "Save results button",
        "acc_save_results_d": "Writes the captions to a UTF-8 .srt subtitle file.",
        "acc_copy_n": "Copy results button",
        "acc_copy_d": "Copies every caption, with its times, to the Windows clipboard "
        "so it can be pasted anywhere.",
        "acc_run_n": "Run controls group",
        "acc_run_d": "Start and cancel the selected task.",
        "acc_progress_group_n": "Progress group",
        "acc_progress_group_d": "Shows the text status and the progress bar of the running task.",
        "acc_results_n": "Results group",
        "acc_results_d": "The finished captions. Edit cells with the arrow keys, then save "
        "or copy them.",
        "lbl_drop_hint": "You can also drag a video file onto this window.",
        "msg_dropped": "Selected video: {name} at {path}",
        "msg_copy_done": "Copied {count} caption(s) to the clipboard.",
        "msg_engine_chosen": "Engine for this run: {engine}",
        "msg_fallback_engine": "The {engine} key is missing, so the free offline engine "
        "was used instead.",
        "msg_task_cancelled": "No task was started.",
        "btn_open": "&Open Video\u2026",
        "btn_extract": "&Extract Audio",
        "btn_transcribe": "&Transcribe",
        "btn_translate": "&Translate",
        "btn_cancel": "Canc&el",
        "btn_add_row": "Add ro&w",
        "btn_delete_row": "&Delete selected row",
        "btn_import": "&Import .srt",
        "btn_render": "&Render Subtitled Video",
        "btn_open_folder": "&Open Output Folder",
        "hdr_no": "#",
        "hdr_start": "Start",
        "hdr_end": "End",
        "hdr_text": "Caption text",
        "lbl_no_video": "No video selected",
        "status_prefix": "Status:",
        "status_ready": "Ready. Press the Open V    ideo button and use Alt+O to open a video file.",
        "dlg_open_video"                        : "Select a video file",
                                "dlg_video_filter": "Video files (*.mp4 *.mov *.avi *.mkv *.wmv *.webm *.flv *.m4v *.mpeg *.mpg *.3gp *.3g2 *.ts *.mts *.m2ts *.ogv *.vob *.asf *.mxf);;All files (*.*)",
        "dlg_save_video": "Save subtitled video",
        "dlg_mp4_filter": "MP4 video (*.mp4)",
        "dlg_import_srt": "Import subtitle file",
        "dlg_srt_filter": "Subtitle files (*.srt);;All files (*.*)",
        "dlg_export_srt": "Export subtitle file",
        "title_no_video": "No video selected",
        "body_no_video": "Choose a supported video such as MP4, MOV, AVI, MKV, WebM, FLV, 3GP, or MPEG first.",
        "title_busy": "Busy",
        "body_busy": "A background task is already running.",
        "title_no_subs": "Nothing to translate",
        "body_no_subs": "There are no subtitles yet. Transcribe the audio or import an .srt file first.",
        "title_invalid": "Invalid subtitles",
        "body_ts_invalid": "Row {row} has an invalid timestamp. Use HH:MM:SS,mmm. Detail: {detail}",
        "body_ts_range": "Row {row}: the end timestamp must be later than the start timestamp.",
        "title_nothing_render": "Nothing to render",
        "title_nothing_export": "Nothing to export",
        "body_nothing_export": "There are no subtitles to export yet.",
        "title_import_failed": "Import failed",
        "body_import_failed": "Could not read the .srt file: {err}",
        "title_export_failed": "Export failed",
        "title_task_complete": "Task complete",
        "msg_video_select_cancel": "Video selection cancelled",
        "msg_video_selected": "Selected video: {name} at {path}",
        "msg_extract_start": "Extracting audio from the video in the background",
        "msg_extract_done": "Audio extraction finished and saved to {path}",
        "msg_transcribe_start": "Transcribing the audio in the background",
        "msg_transcribe_done": "Transcription finished: {count} captions created. Detected audio language: {language}.",
        "msg_translate_start": "Translating subtitles in the background",
        "msg_translate_done": "Translation finished. {count} captions updated.",
        "msg_render_start": "Rendering the subtitled video in the background",
        "msg_render_done": "Rendering finished. The subtitled video was saved to {path}",
        "msg_render_cancel": "Rendering cancelled",
        "msg_cancel_requested": "Cancellation requested; the task will stop at the next safe point.",
        "msg_row_added": "Added empty subtitle row number {num}",
        "msg_rows_deleted": "Deleted {count} selected row(s)",
        "msg_no_rows": "No rows selected to delete",
        "msg_import_done": "Imported {count} captions from {path}",
        "msg_export_done": "Exported {count} captions to {path}",
        "msg_folder_opened": "Opened output folder {path}",
        "msg_progress": "Progress {value} percent",
        "status_task_failed": "Task failed: {msg}",
        "msg_busy_lang": "Cannot change the interface language while a task is running.",
        "stage_extract": "Extracting audio with ffmpeg (moviepy)",
        "stage_extract2": "Extracting audio from video",
        "stage_whisper": "Loading faster-whisper base model (first run downloads it)",
        "stage_transcribing": "Transcribing audio to text",
        "stage_test_translator": "Testing translation service connection",
        "stage_translating": "Translating subtitles",
        "stage_loading_video": "Loading video for caption rendering",
        "stage_burning": "Burning {count} caption line(s) onto video",
        "err_extract": "Audio extraction failed: {msg}",
        "err_transcribe": "Transcription failed: {msg}",
        "err_translate": "Translation failed: {msg}",
        "err_render": "Rendering failed: {msg}",
        "acc_grp_input_n": "Input video group",
        "acc_grp_input_d": "Group for selecting the video file that will be processed.",
        "acc_open_n": "Open video file button",
        "acc_open_d": "Opens a file dialog to choose a supported video file, including MP4, MOV, AVI, MKV, WebM, FLV, 3GP, or MPEG. The chosen path is "
        "announced in the status area below.",
        "acc_path_n": "Selected video path",
        "acc_path_d": "Reports the full path of the currently selected video file.",
        "acc_grp_lang_n": "Languages and translation group",
        "acc_grp_lang_d": "Choose the audio language and translation mode.",
        "acc_audio_lang_n": "Audio language",
        "acc_audio_lang_d": "The language spoken in the video audio. Automatic lets Whisper detect it.",
        "acc_trans_mode_n": "Translation mode",
        "acc_trans_mode_d": "Arabic to English, English to Arabic, or stacked bilingual subtitles that show "
        "the original line and the translated line together.",
        "acc_lang_label_n": "Interface language label",
        "acc_iface_n": "Interface language",
        "acc_iface_d": "Switches the whole interface, including screen-reader descriptions, between "
        "English and Arabic. The layout flips right-to-left automatically.",
        "acc_high_n": "High contrast mode",
        "acc_high_d": "Toggles a black and yellow high contrast visual theme for low vision users.",
        "acc_grp_process_n": "Processing controls group",
        "acc_grp_process_d": "Buttons that extract audio, transcribe speech to text, and translate the captions.",
        "acc_extract_n": "Extract audio button",
        "acc_extract_d": "Extracts the audio track from the selected video with ffmpeg into a temporary file.",
        "acc_transcribe_n": "Transcribe button",
        "acc_transcribe_d": "Extracts audio if needed and transcribes it to timestamps subtitles with "
        "faster-whisper in the background. The interface stays responsive.",
        "acc_translate_n": "Translate button",
        "acc_translate_d": "Translates the caption text with Google Translate in the background using the "
        "chosen translation mode.",
        "acc_cancel_n": "Cancel current task button",
        "acc_cancel_d": "Requests cancellation of the current background job between units of work.",
        "acc_grp_editor_n": "Subtitle editor group",
        "acc_grp_editor_d": "Table of subtitles. Each row is one caption: number, start timestamp, end "
        "timestamp, and text. Use arrow keys to move between cells and type to edit. "
        "Braille displays follow the cell focus.",
        "acc_table_n": "Subtitles table",
        "acc_table_d": "Editable table of {count} subtitle rows with columns number, start timestamp, end "
        "timestamp, and caption text. Navigate with arrow keys and edit inside cells.",
        "acc_add_n": "Add subtitle row button",
        "acc_add_d": "Inserts an empty subtitle row after the last one with default timestamps.",
        "acc_delete_n": "Delete selected rows button",
        "acc_delete_d": "Removes every subtitle row that currently has a selected cell.",
        "acc_import_n": "Import srt file button",
        "acc_import_d": "Loads captions from an existing subtitle file into the editor.",
        "acc_grp_output_n": "Output group",
        "acc_grp_output_d": "Renders a new video with the captions burned in, or opens the output folder.",
        "acc_render_n": "Render subtitled video button",
        "acc_render_d": "Uses moviepy in a background thread to burn the styled white captions with black "
        "outline into the video and saves it as an MP4 file with AAC audio.",
        "acc_folder_n": "Open output folder button",
        "acc_folder_d": "Opens the folder containing the last exported or rendered file.",
        "acc_status_n": "Processing status",
        "acc_status_d": "Reports the current task and its progress.",
        "acc_progress_n": "Task progress bar",
        "acc_progress_d": "Percentage progress of the currently running background task: {value} percent. "
        "Percentage progress of the currently running background task.",
        "menu_file": "&File",
        "menu_edit": "&Edit",
        "menu_settings": "&Settings",
        "menu_accessibility": "&Accessibility",
        "menu_tools": "&Tools",
        "menu_models": "&Models",
        "menu_help": "&Help",
        "act_open_video": "&Open Video\u2026",
        "act_import_srt": "&Import .srt\u2026",
        "act_export_srt": "&Export .srt\u2026",
        "act_render": "&Render Subtitled Video\u2026",
        "act_open_folder": "&Open Output Folder",
        "act_exit": "E&xit",
        "act_add_row": "&Add Row",
        "act_delete_row": "&Delete Selected Row",
        "act_copy_results": "&Copy Results",
        "act_extract": "&Extract Audio",
        "act_cancel": "&Cancel Task",
        "act_iface_lang": "&Interface Language",
        "act_iface_en": "Interface in &English",
        "act_iface_ar": "الواجهة بالعربية",
        "act_a11y_settings": "&Accessibility Settings\u2026",
        "act_high_contrast": "High &Contrast Theme",
        "act_large_focus": "&Larger Focus Indicators",
        "act_simplified": "&Simplified Layout",
        "act_announce_progress": "&Announce Progress",
        "act_sounds": "Play &Sounds",
        "act_model_tiny": "Download &Tiny Model (fastest)",
        "act_model_base": "Download &Base Model (bundled)",
        "act_model_small": "Download &Small Model (most accurate)",
        "act_model_status": "Model &Status",
        "act_user_guide": "&User Guide",
        "act_shortcuts": "&Keyboard Shortcuts",
        "act_check_updates": "&Check for Updates\u2026",
        "act_auto_update": "Check Automatically at &Startup",
        "act_release_notes": "&Release Notes on GitHub",
        "act_report_problem": "Report a &Problem",
        "act_license": "&License Agreement",
        "act_open_log": "Open Log &Folder",
        "act_about": "&About",
        "act_guide_file": "Open &Guide File",
        "act_shortcuts_file": "&Open Shortcut File",
        "msg_help_file_open": "The file is open in your default web browser.",
        "msg_help_file_missing": "The help file was not found on this computer.",
        "act_preferences": "&Speech && Translation Settings\u2026",
        "trans_none": "Original (no translation)",
        "msg_no_translation": "No translation requested: the output language is set to Original.",
        "out_orig": "&Original only",
        "out_trans": "&Translated only (opposite of the video language)",
        "out_both": "&Both (original above, translated below)",
        "acc_menu_n": "Application menu bar",
        "acc_menu_d": "File, Edit, Settings, Accessibility, Tools, Models and Help menus. "
        "Press Alt to focus the menu bar, then the mnemonic letter or the arrow keys.",
        "settings_iface_d": "Interface Language: English or Arabic.",
        "settings_audio_d": "Video Language: Automatic, English, or Arabic.",
        "settings_output_d": "Output Language: Original, Translated, or Both.",
        "help_title_guide": "User Guide",
        "help_title_shortcuts": "Keyboard Shortcuts",
        "help_title_about": "About Accessible Video Transcriber",
        "btn_close": "Close",
        "help_contents_n": "Help contents",
        "help_details_n": "Details of the selected heading",
        "help_hint": (
            "Use the up and down arrows to move through the contents. "
            "Press Enter to open a topic and read it in the text area. "
            "Press Escape inside the text area to come back to the contents. "
            "Press F6 to jump between the contents and the text."
        ),
        "help_about": (
            "<h1>About Accessible Video Transcriber</h1>"
            "<h2>Version 1.2</h2>"
            "<p>Accessible desktop application by Iman Rammal for video work: transcribe "
            "speech to captions, translate them, edit the result and burn it back into the "
            "video.</p>"
            "<h2>Accessibility</h2>"
            "<p>Designed against WCAG 2.1 AA and Windows UI Automation: every control has a "
            "name and a description, the whole program is reachable with the keyboard, the "
            "focus is always visible, progress is announced, and the layout flips "
            "right-to-left for the Arabic interface. Tested with NVDA, JAWS, Narrator and "
            "braille displays.</p>"
            "<h2>Privacy</h2>"
            "<p>The free local engine keeps the audio on this computer. API keys are stored "
            "in the Windows Credential Manager and are only sent to the provider you chose. "
            "The log file never contains a key.</p>"
            "<h2>Libraries</h2>"
            "<p>PyQt6, faster-whisper, ctranslate2, deep-translator, moviepy, srt, "
            "requests.</p>"
            "<h2>License</h2>"
            "<p>Free for personal, educational, research and non-commercial use. See Help "
            "&rarr; License Agreement (Ctrl+Shift+G) for the full text.</p>"
            "<h2>Contact the author</h2>"
            "<p>Iman Rammal &mdash; Braille Training Specialist, NVDA Certified Expert, "
            "JAWS Certified, assistive technology trainer, translator and interpreter.</p>"
            "<p>Phone: <a href=\"tel:+97455485652\">+974 55485652</a><br>"
            "Email: <a href=\"mailto:iman.rammal@gmail.com\">iman.rammal@gmail.com</a><br>"
            "YouTube: <a href=\"https://www.youtube.com/@Welcome2Sawa\">@Welcome2Sawa</a><br>"
            "Telegram: <a href=\"https://t.me/ImanSawa\">t.me/ImanSawa</a><br>"
            "Facebook: <a href=\"https://www.facebook.com/pretty.ammoona\">pretty.ammoona</a><br>"
            "X: <a href=\"https://x.com/imanrammal\">x.com/imanrammal</a></p>"
        ),
        "grp_task": "2.  Task and languages",
        "grp_run": "3.  Run",
        "grp_progress": "4.  Progress",
        "grp_results": "5.  Results",
        "acc_main_n": "Main screen: choose a video, a task, the languages and an engine, then press Start.",
        "btn_ok_n": "OK",
        "model_installed": " (installed)",
        "model_missing": " not installed",
        "msg_model_cached": "{model} is already installed on this computer.",
        "msg_model_start": "Downloading the {model} recognition model. Progress is reported as it goes.",
        "msg_model_progress": "Downloading {model}: {percent} percent.",
        "msg_model_done": "The {model} model finished downloading and is ready to use.",
        "msg_model_fail": "The {model} model could not be downloaded: {error}",
        "msg_model_status_header": "Recognition models on this computer:",
        "msg_model_folder": "Installed models folder: {path}",
        "msg_a11y_large_focus_on": "Larger focus indicator on.",
        "msg_a11y_large_focus_off": "Larger focus indicator off.",
        "msg_a11y_simplified_on": "Simplified main layout on.",
        "msg_a11y_simplified_off": "Simplified main layout off.",
        "msg_a11y_announce_on": "Progress announcements on.",
        "msg_a11y_announce_off": "Progress announcements off.",
        "msg_a11y_sounds_on": "Sound feedback on.",
        "msg_a11y_sounds_off": "Sound feedback off.",
        "acc_title": "Accessibility Settings",
        "acc_intro": "Choose how the program looks and speaks. Move through the options with Tab and change one with the Space bar. The change is applied when you press OK.",
        "acc_lbl_hc": "High contrast mode",
        "acc_desc_hc": "Black and white theme with maximum contrast, easier to read in bright light or with low vision.",
        "acc_lbl_focus": "Larger focus indicator",
        "acc_desc_focus": "Thicker and brighter rectangle around the control that has the keyboard focus.",
        "acc_lbl_simple": "Simplified main layout",
        "acc_desc_simple": "Hide the advanced language and engine pickers, keeping only what a first run needs.",
        "acc_lbl_progress": "Announce progress",
        "acc_desc_progress": "Speak the percentage completed while a task is running.",
        "acc_lbl_sounds": "Sound feedback",
        "acc_desc_sounds": "Play a short tone when a task finishes or fails.",
    },
    "ar": {
        "app_title": "Accessible Video Transcriber - تفريغ الفيديو وترجمته وإنشاء التسميات التوضيحية مع دعم الوصولية",
        "grp_video": "١.  اختر ملف الفيديو",
        "grp_lang": "٢.  اللغات والترجمة",
        "grp_process": "٣.  المعالجة",
        "grp_editor": "٤.  محرر التسميات (سطرًا بسطر، متاح بلوحة المفاتيح)",
        "grp_output": "٥.  الإخراج",
        "lbl_interface_lang": "لغة الواجهة:",
        "iface_en": "English",
        "iface_ar": "العربية",
        "chk_high_contrast": "وضع التباين العالي (أسود وأصفر)",
        "lbl_audio_lang": "لغة الصوت:",
        "lbl_trans_mode": "نمط الترجمة:",
        "lang_auto": "كشف تلقائي",
        "lang_en": "الإنجليزية",
        "lang_ar": "العربية",
        "lang_zh": "الصينية",
        "lang_es": "الإسبانية",
        "lang_fr": "الفرنسية",
        "lang_de": "الألمانية",
        "lang_hi": "الهندية",
        "lang_ja": "اليابانية",
        "lang_pt": "البرتغالية",
        "lang_ru": "الروسية",
        "trans_ar_en": "العربية \u2192 الإنجليزية",
        "trans_en_ar": "الإنجليزية \u2192 العربية",
        "trans_bilingual": "ترجمة مزدوجة (الأصل بالأعلى والترجمة بالأسفل)",
        "lbl_task": "المهمة:",
        "acc_task_n": "المهمة",
        "acc_task_d": "يختار ما يفعله زر «بدء»: تفريغ الكلام إلى تسميات، أو ترجمة "
        "التسميات الموجودة في الجدول.",
        "task_transcribe": "تفريغ الكلام إلى تسميات",
        "task_translate": "ترجمة التسميات",
        "lbl_source_lang": "لغة المصدر (المنطوقة في الفيديو):",
        "lbl_target_lang": "لغة الهدف:",
        "acc_target_n": "لغة الهدف",
        "acc_target_d": "اللغة التي تُترجم إليها التسميات. اختر «بدون ترجمة» للإبقاء "
        "على النص الأصلي.",
        "target_none": "بدون ترجمة (إبقاء اللغة الأصلية)",
        "lbl_engine": "المحرك:",
        "acc_engine_n": "محرك التعرّف",
        "acc_engine_d": "الخدمة التي تنفّذ العمل. «تلقائي» يستخدم اختيارك المحفوظ ويرجع "
        "إلى المحرك المحلي المجاني عند غياب المفتاح.",
        "eng_auto": "تلقائي (اختياري المحفوظ مع رجوع تلقائي)",
        "eng_local": "Whisper المحلي (مجاني ودون اتصال)",
        "eng_openai": "واجهة OpenAI (تحتاج مفتاحًا)",
        "eng_groq": "واجهة Groq (تحتاج مفتاحًا)",
        "eng_gemini": "واجهة Google Gemini (تحتاج مفتاحًا)",
        "btn_start": "&بدء",
        "btn_save_results": "&حفظ النتائج",
        "btn_copy": "&نسخ النتائج",
        "acc_start_n": "زر البدء",
        "acc_start_d": "يُنفّذ المهمة المختارة في قائمة «المهمة». الاختصار F5.",
        "acc_cancel_run_n": "زر إلغاء المهمة الجارية",
        "acc_save_results_n": "زر حفظ النتائج",
        "acc_save_results_d": "يكتب التسميات في ملف .srt بترميز UTF-8.",
        "acc_copy_n": "زر نسخ النتائج",
        "acc_copy_d": "ينسخ كل التسميات مع أزمنتها إلى الحافظة للصقها في أي مكان.",
        "acc_run_n": "مجموعة بدء وإلغاء المهمة",
        "acc_run_d": "يبدأ المهمة المختارة أو يلغيها.",
        "acc_progress_group_n": "مجموعة التقدم",
        "acc_progress_group_d": " تعرض حالة النص وشريط تقدم المهمة الجارية.",
        "acc_results_n": "مجموعة النتائج",
        "acc_results_d": "التسميات النهائية حرّر الخلايا بمفاتيح الأسهم ثم احفظها أو انسخها.",
        "lbl_drop_hint": "يمكنك أيضًا سحب ملف فيديو وإفلاته داخل هذه النافذة.",
        "msg_dropped": "تم اختيار الفيديو: {name} في {path}",
        "msg_copy_done": "تم نسخ {count} تسمية إلى الحافظة.",
        "msg_engine_chosen": "محرك هذه المهمة: {engine}",
        "msg_fallback_engine": "مفتاح {engine} مفقود، لذلك استُخدم المحرك المحلي المجاني "
        "بدلاً منه.",
        "msg_task_cancelled": "لم تبدأ أي مهمة.",
        "btn_open": "&فتح الفيديو\u2026",
        "btn_extract": "&استخراج الصوت",
        "btn_transcribe": "&التفريغ الصوتي",
        "btn_translate": "&ترجمة",
        "btn_cancel": "&إلغاء",
        "btn_add_row": "إ&ضافة صف",
        "btn_delete_row": "&حذف الصف المحدد",
        "btn_import": "&استيراد .srt",
        "btn_render": "&إنشاء الفيديو بالتسميات",
        "btn_open_folder": "&فتح مجلد الإخراج",
        "hdr_no": "الرقم",
        "hdr_start": "البداية",
        "hdr_end": "النهاية",
        "hdr_text": "نص التسمية",
        "lbl_no_video": "لم يتم اختيار فيديو",
        "status_prefix": "الحالة:",
        "status_ready": "جاهز. اضغط زر فتح الفيديو واستخدم Alt+O لفتح ملف فيديو.",
        "dlg_open_video": "اختر ملف فيديو",
        "dlg_video_filter": "ملفات الفيديو (*.mp4 *.mov *.avi *.mkv *.wmv *.webm *.flv *.m4v *.mpeg *.mpg *.3gp *.3g2 *.ts *.mts *.m2ts *.ogv *.vob *.asf *.mxf);;كل الملفات (*.*)",
        "dlg_save_video": "احفظ الفيديو بالتسميات",
        "dlg_mp4_filter": "فيديو MP4 (*.mp4)",
        "dlg_import_srt": "استيراد ملف التسميات",
        "dlg_srt_filter": "ملفات التسميات (*.srt);;كل الملفات (*.*)",
        "dlg_export_srt": "تصدير ملف التسميات",
        "title_no_video": "لم يتم اختيار فيديو",
        "body_no_video": "اختر أولًا ملف فيديو مدعومًا مثل MP4 أو MOV أو AVI أو MKV أو WebM أو FLV أو 3GP أو MPEG.",
        "title_busy": "مشغول",
        "body_busy": "هناك مهمة قيد التشغيل في الخلفية بالفعل.",
        "title_no_subs": "لا يوجد شيء للترجمة",
        "body_no_subs": "لا توجد تسميات بعد. فُرِّغ الصوت أولًا أو استورد ملف .srt.",
        "title_invalid": "تسميات غير صالحة",
        "body_ts_invalid": "الصف {row} يحتوي على طابع زمني غير صالح. استخدم الصيغة HH:MM:SS,mmm. التفاصيل: {detail}",
        "body_ts_range": "الصف {row}: يجب أن يكون طابع النهاية أحدث من طابع البداية.",
        "title_nothing_render": "لا يوجد شيء للإنشاء",
        "title_nothing_export": "لا يوجد شيء للتصدير",
        "body_nothing_export": "لا توجد تسميات للتصدير بعد.",
        "title_import_failed": "فشل الاستيراد",
        "body_import_failed": "تعذّرت قراءة ملف .srt: {err}",
        "title_export_failed": "فشل التصدير",
        "title_task_complete": "اكتملت المهمة",
        "msg_video_select_cancel": "تم إلغاء اختيار الفيديو",
        "msg_video_selected": "الفيديو المحدد: {name} في {path}",
        "msg_extract_start": "يجري استخراج الصوت من الفيديو في الخلفية",
        "msg_extract_done": "اكتمل استخراج الصوت وحُفظ في {path}",
        "msg_transcribe_start": "يجري تفريغ الصوت في الخلفية",
        "msg_transcribe_done": "اكتمل التفريغ: أُنشئت {count} تسمية. لغة الصوت المكتشفة: {language}.",
        "msg_translate_start": "يجري ترجمة التسميات في الخلفية",
        "msg_translate_done": "اكتملت الترجمة: حُدِّثت {count} تسمية.",
        "msg_render_start": "يجري إنشاء الفيديو بالتسميات في الخلفية",
        "msg_render_done": "اكتمل الإنشاء: حُفظ الفيديو بالتسميات في {path}",
        "msg_render_cancel": "تم إلغاء الإنشاء",
        "msg_cancel_requested": "طُلب الإلغاء؛ ستتوقف المهمة عند أقرب نقطة آمنة.",
        "msg_row_added": "أُضيف صف فارغ رقم {num}",
        "msg_rows_deleted": "تم حذف {count} صف(وف) محددة",
        "msg_no_rows": "لم يتم تحديد أي صفوف للحذف",
        "msg_import_done": "تم استيراد {count} تسمية من {path}",
        "msg_export_done": "تم تصدير {count} تسمية إلى {path}",
        "msg_folder_opened": "تم فتح مجلد الإخراج {path}",
        "msg_progress": "التقدم {value} بالمئة",
        "status_task_failed": "فشلت المهمة: {msg}",
        "msg_busy_lang": "لا يمكن تغيير لغة الواجهة أثناء تشغيل مهمة.",
        "stage_extract": "يجري استخراج الصوت باستخدام ffmpeg (moviepy)",
        "stage_extract2": "يجري استخراج الصوت من الفيديو",
        "stage_whisper": "يجري تحميل نموذج faster-whisper الأساسي (يُنزَّل عند أول تشغيل)",
        "stage_transcribing": "يجري تحويل الصوت إلى نص",
        "stage_test_translator": "يجري اختبار الاتصال بخدمة الترجمة",
        "stage_translating": "يجري ترجمة التسميات",
        "stage_loading_video": "يجري تحميل الفيديو لتوليد التسميات",
        "stage_burning": "يجري حرق {count} سطر تسمية على الفيديو",
        "err_extract": "فشل استخراج الصوت: {msg}",
        "err_transcribe": "فشل التفريغ: {msg}",
        "err_translate": "فشلت الترجمة: {msg}",
        "err_render": "فشل الإنشاء: {msg}",
        "acc_grp_input_n": "مجموعة إدخال الفيديو",
        "acc_grp_input_d": "مجموعة لاختيار ملف الفيديو الذي ستتم معالجته.",
        "acc_open_n": "زر فتح ملف الفيديو",
        "acc_open_d": "يفتح مربع حوار لاختيار ملف فيديو مدعوم، مثل MP4 أو MOV أو AVI أو MKV أو WebM أو FLV أو 3GP أو MPEG. يُعلَن المسار المختار "
        "في منطقة الحالة بالأسفل.",
        "acc_path_n": "مسار الفيديو المحدد",
        "acc_path_d": "يعرض المسار الكامل لملف الفيديو المحدد حاليًا.",
        "acc_grp_lang_n": "مجموعة اللغات والترجمة",
        "acc_grp_lang_d": "اختر لغة الصوت ونمط الترجمة.",
        "acc_audio_lang_n": "لغة الصوت",
        "acc_audio_lang_d": "اللغة المنطوقة في صوت الفيديو. الخيار التلقائي يجعل Whisper يكتشفها.",
        "acc_trans_mode_n": "نمط الترجمة",
        "acc_trans_mode_d": "من العربية إلى الإنجليزية، أو من الإنجليزية إلى العربية، أو تسميات مزدوجة "
        "تعرض السطر الأصلي مع سطر الترجمة معًا.",
        "acc_lang_label_n": "تسمية لغة الواجهة",
        "acc_iface_n": "لغة الواجهة",
        "acc_iface_d": "تبدّل الواجهة كاملة، بما فيها وصف شاشات قراءة الشاشة، بين اللغة الإنجليزية "
        "والعربية. وينعكس الاتجاه تلقائيًا من اليمين إلى اليسار.",
        "acc_high_n": "وضع التباين العالي",
        "acc_high_d": "يبدّل مظهرًا أسود وأصفر عالي التباين للمستخدمين من ضعاف البصر.",
        "acc_grp_process_n": "مجموعة أدوات المعالجة",
        "acc_grp_process_d": "أزرار تستخرج الصوت وتفرِّغ الكلام إلى نص وتترجم التسميات.",
        "acc_extract_n": "زر استخراج الصوت",
        "acc_extract_d": "يستخرج المسار الصوتي من الفيديو المحدد باستخدام ffmpeg إلى ملف مؤقت.",
        "acc_transcribe_n": "زر التفريغ الصوتي",
        "acc_transcribe_d": "تستخرج الصوت إن لزم ثم تفرّغه إلى تسميات بزمن محدد باستخدام faster-whisper "
        "في الخلفية، مع بقاء الواجهة سريعة الاستجابة.",
        "acc_translate_n": "زر الترجمة",
        "acc_translate_d": "يترجم نص التسميات باستخدام Google Translate في الخلفية وفق نمط الترجمة المختار.",
        "acc_cancel_n": "زر إلغاء المهمة الحالية",
        "acc_cancel_d": "طلَب إلغاء المهمة الحالية التي تعمل في الخلفية عند أول فرصة آمنة.",
        "acc_grp_editor_n": "مجموعة محرر التسميات",
        "acc_grp_editor_d": "جدول التسميات. كل صف يمثل تسمية واحدة: الرقم، وطابع البداية، وطابع النهاية، "
        "والنص. استخدم أسهم لوحة المفاتيح للتنقل بين الخلايا واكتب للتعديل. وتتبع شاشات برايل "
        "موضع التركيز في الخلايا.",
        "acc_table_n": "جدول التسميات",
        "acc_table_d": "جدول قابل للتعديل يتكون من {count} صف تسمية بأعمدة الرقم وطابع البداية وطابع "
        "النهاية ونص التسمية. تنقّل بأسهم لوحة المفاتيح وعدّل داخل الخلايا مباشرة.",
        "acc_add_n": "زر إضافة صف تسمية",
        "acc_add_d": "يدرج صفًا فارغًا بعد آخر صف بطوابع زمنية افتراضية.",
        "acc_delete_n": "زر حذف الصفوف المحددة",
        "acc_delete_d": "يزيل كل صف ترجمة فيه خلية محددة حاليًا.",
        "acc_import_n": "زر استيراد ملف .srt",
        "acc_import_d": "يحمل التسميات من ملف تسميات موجود إلى المحرر.",
        "acc_grp_output_n": "مجموعة الإخراج",
        "acc_grp_output_d": "ينشئ فيديو جديدًا بالتسميات المدمجة فيه، أو يفتح مجلد الإخراج.",
        "acc_render_n": "زر إنشاء الفيديو بالتسميات",
        "acc_render_d": "يستخدم moviepy في خاصية خلفية لدمج التسميات البيضاء ذات الإطار الأسود داخل "
        "الفيديو وحفظه كملف MP4 بصوت AAC.",
        "acc_folder_n": "زر فتح مجلد الإخراج",
        "acc_folder_d": "يفتح المجلد الذي يحتوي على آخر ملف تم تصديره أو إنشاؤه.",
        "acc_status_n": "حالة المعالجة",
        "acc_status_d": "يعرض المهمة الحالية ومدى تقدمها.",
        "acc_progress_n": "شريط تقدم المهمة",
        "acc_progress_d": "نسبة تقدم المهمة الحالية التي تعمل في الخلفية: {value} بالمئة.",
        "menu_file": "&ملف",
        "menu_edit": "&تحرير",
        "menu_settings": "&الإعدادات",
        "menu_accessibility": "إ&تاحة الوصول",
        "menu_tools": "&أدوات",
        "menu_models": "ال&نماذج",
        "menu_help": "&مساعدة",
        "act_open_video": "&فتح الفيديو\u2026",
        "act_import_srt": "&استيراد .srt\u2026",
        "act_export_srt": "&تصدير .srt\u2026",
        "act_render": "&إنشاء الفيديو بالتسميات\u2026",
        "act_open_folder": "&فتح مجلد الإخراج",
        "act_exit": "&خروج",
        "act_add_row": "&إضافة صف",
        "act_delete_row": "&حذف الصف المحدد",
        "act_copy_results": "&نسخ النتائج",
        "act_extract": "&استخراج الصوت",
        "act_cancel": "إ&لغاء المهمة",
        "act_iface_lang": "&لغة الواجهة",
        "act_iface_en": "الواجهة بالإن&جليزية",
        "act_iface_ar": "الواجهة بالعربية",
        "act_a11y_settings": "&إعدادات إتاحة الوصول\u2026",
        "act_high_contrast": "سمة التباين ال&عالي",
        "act_large_focus": "&مؤشرات تركيز أكبر",
        "act_simplified": "&تخطيط مبسّط",
        "act_announce_progress": "الإ&علان عن التقدم",
        "act_sounds": "تشغيل ال&أصوات",
        "act_model_tiny": "تنزيل النموذج &الصغير (الأسرع)",
        "act_model_base": "تنزيل النموذج الأساسي (مضمّن)",
        "act_model_small": "تنزيل النموذج الأ&كبر (الأدق)",
        "act_model_status": "حالة ال&نماذج",
        "act_user_guide": "&دليل الاستخدام",
        "act_shortcuts": "&اختصارات لوحة المفاتيح",
        "act_check_updates": "التحقق من ال&تحديثات",
        "act_auto_update": "التحقق التلقائي عند &بدء التشغيل",
        "act_release_notes": "م&لاحظات الإصدار على GitHub",
        "act_report_problem": "الإبلاغ عن &مشكلة",
        "act_license": "اتفاقية ال&رخصة",
        "act_open_log": "فتح &مجلد السجل",
        "act_about": "&حول",
        "act_guide_file": "&فتح ملف الدليل",
        "act_shortcuts_file": "فتح ملف ال&اختصارات",
        "msg_help_file_open": "الملف مفتوح في متصفّحك الافتراضي.",
        "msg_help_file_missing": "لم يُعثر على ملف المساعدة على هذا الحاسوب.",
        "act_preferences": "إعدادات &التفريغ والترجمة…",
        "trans_none": "الأصل (بدون ترجمة)",
        "msg_no_translation": "لا توجد ترجمة مطلوبة: لغة الإخراج مضبوطة على «الأصل».",
        "out_orig": "الأصل &فقط",
        "out_trans": "الترجمة &فقط (عكس لغة الفيديو)",
        "out_both": "&الاثنتان (الأصل بالأعلى والترجمة بالأسفل)",
        "acc_menu_n": "شريط القوائم",
        "acc_menu_d": "قوائم ملف وتحرير وإعدادات وإتاحة الوصول والأدوات والنماذج ومساعدة. "
        "اضغط Alt للانتقال إلى شريط القوائم، ثم استخدم الحرف المظلل أو أسهم لوحة المفاتيح.",
        "settings_iface_d": "لغة الواجهة: الإنجليزية أو العربية.",
        "settings_audio_d": "لغة الفيديو: تلقائي أو الإنجليزية أو العربية.",
        "settings_output_d": "لغة الإخراج: الأصل أو الترجمة أو الاثنتان معًا.",
        "help_title_guide": "دليل الاستخدام",
        "help_title_shortcuts": "اختصارات لوحة المفاتيح",
        "help_title_about": "حول Accessible Video Transcriber",
        "btn_close": "إغلاق",
        "help_contents_n": "محتويات المساعدة",
        "help_details_n": "تفاصيل العنوان المحدد",
        "help_hint": (
            "استخدم السهمين الأعلى والأسفل للتنقل بين المحتويات. "
            "اضغط Enter لفتح موضوع وقراءته في منطقة النص. "
            "اضغط Escape داخل منطقة النص للعودة إلى المحتويات. "
            "واضغط F6 للتنقل بين المحتويات ومنطقة النص."
        ),
        "help_about": (
            "<h1>حول Accessible Video Transcriber</h1>"
            "<h2>الإصدار 1.2</h2>"
            "<p>تطبيق سطح مكتب من إعداد عُمر رمّال للعمل على الفيديو: تفريغ الكلام إلى "
            "تسميات، وترجمتها، وتعديل النتيجة، ودمجها داخل الفيديو.</p>"
            "<h2>الوصولية</h2>"
            "<p>مصمّم وفق معيار WCAG 2.1 AA وWindows UI Automation: لكل عنصر اسم ووصف، "
            "وكل البرنامج يمكن الوصول إليه بلوحة المفاتيح، ومؤشر التركيز دائم الظهور، "
            "والتقدم يُعلن، والتخطيط ينعكس من اليمين إلى اليسار في الواجهة العربية. جُرِّب "
            "مع NVDA وJAWS وNarrator وشاشات برايل.</p>"
            "<h2>الخصوصية</h2>"
            "<p>المحرك المجاني المحلي يُبقي الصوت على هذا الحاسوب. وتُحفظ مفاتيح API في "
            "Windows Credential Manager ولا تُرسل إلا إلى المزود الذي اخترته. ولا يحتوي "
            "ملف السجل على أي مفتاح.</p>"
            "<h2>المكتبات</h2>"
            "<p>PyQt6 وfaster-whisper وctranslate2 وdeep-translator وmoviepy وsrt "
            "وrequests.</p>"
            "<h2>الرخصة</h2>"
            "<p>مجاني للاستخدام الشخصي والتعليمي والبحثي وغير التجاري. انظر مساعد ← "
            "اتفاقية الرخصة (Ctrl+Shift+G) للنص الكامل.</p>"
            "<h2>التواصل مع المؤلف</h2>"
            "<p>Iman Rammal &mdash; أخصائي تدريب على برايل، وخبير NVDA معتمد، "
            "وحاصل على شهادة JAWS، ومدرّب تقنيات مساعدة، ومترجم ومترجم فوري.</p>"
            "<p>الهاتف: <a href=\"tel:+97455485652\">+974 55485652</a><br>"
            "البريد الإلكتروني: <a href=\"mailto:iman.rammal@gmail.com\">iman.rammal@gmail.com</a><br>"
            "يوتيوب: <a href=\"https://www.youtube.com/@Welcome2Sawa\">@Welcome2Sawa</a><br>"
            "تيليجرام: <a href=\"https://t.me/ImanSawa\">t.me/ImanSawa</a><br>"
            "فيسبوك: <a href=\"https://www.facebook.com/pretty.ammoona\">pretty.ammoona</a><br>"
            "إكس: <a href=\"https://x.com/imanrammal\">x.com/imanrammal</a></p>"
        ),
        "grp_task": "٢.  المهمة واللغات",
        "grp_run": "٣.  التشغيل",
        "grp_progress": "٤.  التقدم",
        "grp_results": "٥.  النتائج",
        "acc_main_n": "الشاشة الرئيسية: اختر فيديو ومهمة ولغات ومحركًا ثم اضغط ابدأ.",
        "btn_ok_n": "موافق",
        "model_installed": " (مثبّت)",
        "model_missing": " غير مثبّت",
        "msg_model_cached": "{model} مثبّت بالفعل على هذا الحاسوب.",
        "msg_model_start": "جارٍ تنزيل نموذج التعرّف على {model}. سيُبلَّغ عن التقدّم أثناء التنزيل.",
        "msg_model_progress": "تنزيل {model}: {percent} بالمئة.",
        "msg_model_done": "اكتمل تنزيل نموذج {model} وأصبح جاهزًا للاستخدام.",
        "msg_model_fail": "تعذّر تنزيل نموذج {model}: {error}",
        "msg_model_status_header": "نماذج التعرّف على هذا الحاسوب:",
        "msg_model_folder": "مجلد النماذج المثبّتة: {path}",
        "msg_a11y_large_focus_on": "تم تفعيل مؤشر التركيز الكبير.",
        "msg_a11y_large_focus_off": "تم إيقاف مؤشر التركيز الكبير.",
        "msg_a11y_simplified_on": "تم تفعيل التخطيط المبسّط.",
        "msg_a11y_simplified_off": "تم إيقاف التخطيط المبسّط.",
        "msg_a11y_announce_on": "تم تفعيل الإعلان عن التقدّم.",
        "msg_a11y_announce_off": "تم إيقاف الإعلان عن التقدّم.",
        "msg_a11y_sounds_on": "تم تفعيل التنبيهات الصوتية.",
        "msg_a11y_sounds_off": "تم إيقاف التنبيهات الصوتية.",
        "acc_title": "إعدادات الوصول",
        "acc_intro": "اختر شكل البرنامج وطريقة كلامه. انتقل بين الخيارات بمفتاح Tab وغيّر أحدها بمفتاح المسافة. يُطبَّق التغيير عند ضغط موافق.",
        "acc_lbl_hc": "وضع التباين العالي",
        "acc_desc_hc": "سمة أسود وأبيض بأقصى تباين، أسهل للقراءة في الإضاءة الساطعة أو مع ضعف البصر.",
        "acc_lbl_focus": "مؤشر تركيز أكبر",
        "acc_desc_focus": "إطار أسمق وأبرز حول العنصر الذي يحتفظ بتركيز لوحة المفاتيح.",
        "acc_lbl_simple": "تخطيط مبسّط للشاشة الرئيسية",
        "acc_desc_simple": "إخفاء اختياري اللغة والمحرك المتقدّمين والاكتفاء بما يلزم أول تشغيل.",
        "acc_lbl_progress": "الإعلان عن التقدّم",
        "acc_desc_progress": "النطق بالنسبة المئوية للإنجاز أثناء تشغيل المهمة.",
        "acc_lbl_sounds": "التنبيهات الصوتية",
        "acc_desc_sounds": "تشغيل نغمة قصيرة عند انتهاء المهمة أو فشلها.",
    },
}

LANG_COMBO_ITEMS = [
    ("lang_auto", "auto"),
    ("lang_en", "en"),
    ("lang_ar", "ar"),
]

TRANS_COMBO_ITEMS = [
    ("trans_none", ("", "none")),
    ("trans_ar_en", ("ar", "en")),
    ("trans_en_ar", ("en", "ar")),
    ("trans_bilingual", ("auto", "bilingual")),
]

TASK_COMBO_ITEMS = [
    ("task_transcribe", "transcribe"),
    ("task_translate", "translate"),
]

# Target language of the captions: "none" keeps the original text.
TARGET_COMBO_ITEMS = [
    ("target_none", "none"),
    ("lang_en", "en"),
    ("lang_ar", "ar"),
    ("lang_fr", "fr"),
    ("lang_es", "es"),
    ("lang_de", "de"),
    ("lang_zh", "zh"),
    ("lang_hi", "hi"),
    ("lang_ja", "ja"),
    ("lang_pt", "pt"),
    ("lang_ru", "ru"),
    ("trans_bilingual", "bilingual"),
]

ENGINE_COMBO_ITEMS = [
    ("eng_auto", "auto"),
    ("eng_local", "local"),
    ("eng_openai", "openai"),
    ("eng_groq", "groq"),
    ("eng_gemini", "gemini"),
]

IFACE_COMBO_ITEMS = [
    ("iface_en", "en"),
    ("iface_ar", "ar"),
]

LANG_NAMES = {
    "auto": "lang_auto",
    "en": "lang_en",
    "ar": "lang_ar",
    "zh": "lang_zh",
    "es": "lang_es",
    "fr": "lang_fr",
    "de": "lang_de",
    "hi": "lang_hi",
    "ja": "lang_ja",
    "pt": "lang_pt",
    "ru": "lang_ru",
}


def tr(lang, key, **kwargs):
    table = TR.get(lang, TR["en"])
    text = table.get(key, TR["en"].get(key))
    if text is None:
        # Fall back to the shared string table (settings, API errors, stages)
        # so every module can share one translation of the same message.
        try:
            from vt_i18n import tr as shared_tr

            return shared_tr(lang, key, **kwargs)
        except Exception:  # noqa: BLE001 - never fail over a missing string
            return key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def _pick_font():
    """Caption font: the shared helper knows about the bundled fallback too."""
    try:
        import vt_install

        path = vt_install.caption_font()
        if path:
            return path
    except Exception:
        pass
    candidates = (
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), r"Fonts\tahoma.ttf"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), r"Fonts\arial.ttf"),
        "DejaVuSans.ttf",
    )
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


FONT_PATH = _pick_font()


def format_timestamp(td):
    td = max(td, timedelta(0))
    ms = td.microseconds // 1000
    total = int(td.total_seconds())
    secs = total % 60
    mins = (total // 60) % 60
    hours = total // 3600
    return "{0:02d}:{1:02d}:{2:02d},{3:03d}".format(hours, mins, secs, ms)


def parse_timestamp(text):
    raw = text.strip().replace(",", ".")
    if " --> " in raw:
        raw = raw.split(" --> ")[0].strip()
    if ":" not in raw:
        raise ValueError("Timestamp must look like HH:MM:SS,mmm")
    pieces = raw.split(":")
    if len(pieces) != 3:
        raise ValueError("Timestamp must look like HH:MM:SS,mmm")
    hours = int(pieces[0].strip())
    minutes = int(pieces[1].strip())
    sec_parts = pieces[2].strip().split(".")
    seconds = int(sec_parts[0])
    fraction = 0
    if len(sec_parts) > 1 and sec_parts[1]:
        fraction = int(float("0." + sec_parts[1][:3]) * 1000)
    return timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=fraction)


def trim_subtitles(subtitles):
    return [
        srt.Subtitle(
            index=item.index,
            start=item.start - timedelta(microseconds=item.start.microseconds % 1000),
            end=item.end - timedelta(microseconds=item.end.microseconds % 1000),
            content=item.content,
            proprietary="",
        )
        for item in subtitles
    ]


from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal

from PyQt6.QtGui import QAction, QActionGroup, QFont, QIcon, QKeySequence, QShortcut

QAccessible = None

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class ExtractAudioThread(QThread):
    progress = pyqtSignal(int)
    stages = pyqtSignal(str)
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, video_path, audio_path, lang="en", parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.audio_path = audio_path
        self.lang = lang

    def run(self):
        from moviepy import VideoFileClip

        try:
            os.makedirs(os.path.dirname(self.audio_path), exist_ok=True)
            self.stages.emit(tr(self.lang, "stage_extract"))
            clip = VideoFileClip(self.video_path)
            try:
                clip.audio.write_audiofile(
                    self.audio_path,
                    fps=16000,
                    nbytes=2,
                    codec="pcm_s16le",
                    logger=None,
                )
            finally:
                if clip.audio is not None:
                    try:
                        clip.audio.close()
                    except Exception:
                        pass
                clip.close()
            self.progress.emit(100)
            self.completed.emit(self.audio_path)
        except Exception as exc:
            self.failed.emit(tr(self.lang, "err_extract", msg=str(exc)))


class TranscriptionThread(QThread):
    progress = pyqtSignal(int)
    stages = pyqtSignal(str)
    completed = pyqtSignal(list, str, str)
    failed = pyqtSignal(str)

    def __init__(self, video_path, audio_path, language, temp_dir, lang="en", parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.audio_path = audio_path
        self.language = language
        self.temp_dir = temp_dir
        self.lang = lang

    def _extract_audio(self):
        from moviepy import VideoFileClip

        os.makedirs(self.temp_dir, exist_ok=True)
        target = os.path.join(self.temp_dir, "audio.wav")
        if os.path.exists(target):
            return target
        self.stages.emit(tr(self.lang, "stage_extract2"))
        clip = VideoFileClip(self.video_path)
        try:
            clip.audio.write_audiofile(
                target,
                fps=16000,
                nbytes=2,
                codec="pcm_s16le",
                logger=None,
            )
        finally:
            if clip.audio is not None:
                try:
                    clip.audio.close()
                except Exception:
                    pass
            clip.close()
        return target

    def run(self):
        try:
            audio = self.audio_path or self._extract_audio()
            if not os.path.exists(audio):
                raise RuntimeError("Audio file does not exist")

            from faster_whisper import WhisperModel

            import vt_install

            self.stages.emit(tr(self.lang, "stage_whisper"))
            # Hand faster-whisper the model folder shipped with the program
            # when there is one: a path skips its download step, so this path
            # never touches the network.
            local_base = vt_install.model_dir("base")
            model = WhisperModel(local_base or "base", device="cpu", compute_type="int8")
            language = None if self.language == "auto" else self.language
            self.stages.emit(tr(self.lang, "stage_transcribing"))
            segments, info = model.transcribe(
                audio,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 400},
            )
            subtitles = []
            detected = info.language if info.language else "auto"
            total_duration = float(info.duration or 1.0)
            for seg in segments:
                if self.isInterruptionRequested():
                    break
                text = (seg.text or "").strip()
                if not text:
                    continue
                start = timedelta(seconds=float(seg.start))
                end = timedelta(seconds=float(seg.end))
                if end <= start:
                    end = start + timedelta(milliseconds=120)
                subtitles.append(
                    srt.Subtitle(
                        index=len(subtitles) + 1,
                        start=start,
                        end=end,
                        content=text,
                    )
                )
                pct = int((float(seg.end) / max(total_duration, 0.001)) * 100)
                self.progress.emit(min(99, pct))
            if subtitles:
                last_end = subtitles[-1].end
            else:
                last_end = timedelta(seconds=1)
            self.progress.emit(100)
            self.completed.emit(subtitles, detected, audio)
        except Exception as exc:
            self.failed.emit(tr(self.lang, "err_transcribe", msg=str(exc)))


class TranslationThread(QThread):
    progress = pyqtSignal(int)
    stages = pyqtSignal(str)
    completed = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, subtitles, source, target, bilateral, lang="en", parent=None):
        super().__init__(parent)
        self.subtitles = subtitles
        self.source = source
        self.target = target
        self.bilateral = bilateral
        self.lang = lang

    def _translate_line(self, line, source, target):
        from deep_translator import GoogleTranslator

        for attempt in range(3):
            try:
                result = GoogleTranslator(source=source, target=target).translate(line)
                if result:
                    return result.strip()
            except Exception:
                time.sleep(0.8 * (attempt + 1))
        return None

    def run(self):
        try:
            from deep_translator import GoogleTranslator

            self.stages.emit(tr(self.lang, "stage_test_translator"))
            probe = GoogleTranslator(source=self.source, target=self.target)
            probe.translate("ok")
            self.stages.emit(tr(self.lang, "stage_translating"))
            output = []
            total = max(len(self.subtitles), 1)
            for idx, sub in enumerate(self.subtitles, start=1):
                if self.isInterruptionRequested():
                    break
                lines = sub.content.splitlines()
                if self.bilateral:
                    if len(lines) >= 2:
                        original = lines[0]
                        translated = lines[-1]
                    else:
                        original = lines[0] if lines else ""
                        translated = self._translate_line(original, "auto", self.target)
                    new_content = "\n".join(
                        part for part in (original, translated) if part
                    )
                else:
                    combined = "\n".join(lines) if lines else ""
                    translated = self._translate_line(combined, self.source, self.target)
                    new_content = translated if translated else combined
                output.append(
                    srt.Subtitle(
                        index=sub.index,
                        start=sub.start,
                        end=sub.end,
                        content=new_content,
                    )
                )
                self.progress.emit(min(99, int(idx / total * 100)))
            self.progress.emit(100)
            self.completed.emit(output)
        except Exception as exc:
            self.failed.emit(tr(self.lang, "err_translate", msg=str(exc)))


# Keep the UI wired to the shared workers.  The older local worker classes
# above are retained for compatibility with old bundled builds, but the shared
# implementations handle more containers and provide actionable errors.
from vt_workers import (  # noqa: E402
    ExtractAudioThread,
    RenderThread,
    TranscriptionThread,
    TranslationThread,
)

import vt_setup  # noqa: E402


class MainWindow(QMainWindow):
    def __init__(self, language=None):
        super().__init__()
        if language in ("en", "ar"):
            self.current_lang = language
        else:
            self.current_lang = vt_setup.saved_language() or "en"
        self.video_path = ""
        self.audio_path = ""
        self.subtitles = []
        self.show_timestamps = True
        try:
            import vt_prefs

            self.show_timestamps = (
                vt_prefs.load().get("show_timestamps", "true") != "false"
            )
        except Exception:  # noqa: BLE001 - the default is always acceptable
            pass
        self._help_dlg = None
        self.detected_language = "auto"
        self.worker_thread = None
        self.temp_dir = tempfile.mkdtemp(prefix="vidtrans_")
        self.high_contrast = False
        self._last_announced = -1
        self._text_map = []
        self._acc_map = []
        self._title_map = []
        self._menu_map = []
        self._action_map = []
        self._iface_actions = {}
        self._view_high_act = None
        self._a11y_actions = {}
        self._model_actions = {}
        self._model_busy = False
        self._model_thread = None
        self._model_timer = None
        self._model_name = ""
        self._model_result = [None]
        self._model_milestone = 0
        self.accessibility_settings = {}

        # Created here, filled in by _build_ui: the menus drive both even
        # though they no longer appear on the main screen.
        self.interface_combo = QComboBox()
        for item_key, item_data in IFACE_COMBO_ITEMS:
            self.interface_combo.addItem(tr(self.current_lang, item_key), item_data)
        self.interface_combo.currentIndexChanged.connect(self._on_interface_lang)
        self.high_contrast_check = None

        self.resize(1120, 840)
        self.center_on_screen()
        self._build_ui()
        self._build_menus()
        self.apply_theme()
        try:
            # Restore what the user chose in the Accessibility menu the last
            # time: theme, focus size, simplified layout and the check marks.
            import vt_a11y

            vt_a11y.apply(self)
        except Exception:  # noqa: BLE001 - defaults are always acceptable
            logging.exception("accessibility settings could not be restored")
        self.interface_combo.setCurrentIndex(IFACE_COMBO_ITEMS.index(
            next(item for item in IFACE_COMBO_ITEMS if item[1] == self.current_lang)
        ))
        # Sets the window title, the RTL direction and every translated string
        # for the language that the setup wizard chose.
        self._retranslate_ui()

    def t(self, key, **kwargs):
        return tr(self.current_lang, key, **kwargs)

    def lang_name(self, code):
        return self.t(LANG_NAMES.get(code, code))

    # ------------------------------------------------------------------ UI
    def center_on_screen(self):
        screen = self.screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(
            area.x() + max(0, (area.width() - self.width()) // 2),
            area.y() + max(0, (area.height() - self.height()) // 2),
        )

    def _build_ui(self):
        """Essential controls only; everything else lives in the menu bar.

        Main screen, top to bottom: choose or drop a video file, choose the
        task and the source language, the target language and the engine, the
        Start button, the progress area with a text status, and the results
        area with the Save and Copy buttons.
        """
        central = QWidget()
        central.setAccessibleName(self.t("acc_main_n"))
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setSpacing(10)

        # ------------------------------------------------- 1. video file
        input_group = QGroupBox(self.t("grp_video"))
        input_group.setAccessibleName(self.t("acc_grp_input_n"))
        input_group.setAccessibleDescription(self.t("acc_grp_input_d"))
        in_layout = QVBoxLayout(input_group)
        file_row = QHBoxLayout()
        self.open_button = QPushButton(self.t("btn_open"))
        self.open_button.setAccessibleName(self.t("acc_open_n"))
        self.open_button.setAccessibleDescription(self.t("acc_open_d"))
        self.open_button.setToolTip("Keyboard: Ctrl+O")
        self.open_button.clicked.connect(self.select_video)
        self.path_label = QLabel(self.t("lbl_no_video"))
        self.path_label.setAccessibleName(self.t("acc_path_n"))
        self.path_label.setAccessibleDescription(self.t("acc_path_d"))
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        file_row.addWidget(self.open_button, 0)
        file_row.addWidget(self.path_label, 1)
        in_layout.addLayout(file_row)
        self.drop_hint = QLabel(self.t("lbl_drop_hint"))
        self.drop_hint.setAccessibleName(self.t("lbl_drop_hint"))
        self.drop_hint.setWordWrap(True)
        in_layout.addWidget(self.drop_hint)
        outer.addWidget(input_group)

        # ------------------------------------- 2. task, languages, engine
        options_group = QGroupBox(self.t("grp_task"))
        options_group.setAccessibleName(self.t("acc_grp_lang_n"))
        options_group.setAccessibleDescription(self.t("acc_grp_lang_d"))
        form = QFormLayout(options_group)

        self.task_combo = QComboBox()
        self.task_combo.setAccessibleName(self.t("acc_task_n"))
        self.task_combo.setAccessibleDescription(self.t("acc_task_d"))
        self.task_combo.setToolTip(self.t("acc_task_d"))
        for key, data in TASK_COMBO_ITEMS:
            self.task_combo.addItem(self.t(key), data)
        form.addRow(self.t("lbl_task"), self.task_combo)

        self.language_combo = QComboBox()
        self.language_combo.setAccessibleName(self.t("acc_audio_lang_n"))
        self.language_combo.setAccessibleDescription(self.t("acc_audio_lang_d"))
        self.language_combo.setToolTip(self.t("acc_audio_lang_d"))
        for key, data in LANG_COMBO_ITEMS:
            self.language_combo.addItem(self.t(key), data)
        self.language_combo.currentIndexChanged.connect(self._sync_settings_menus)
        form.addRow(self.t("lbl_source_lang"), self.language_combo)

        self.target_combo = QComboBox()
        self.target_combo.setAccessibleName(self.t("acc_target_n"))
        self.target_combo.setAccessibleDescription(self.t("acc_target_d"))
        self.target_combo.setToolTip(self.t("acc_target_d"))
        for key, data in TARGET_COMBO_ITEMS:
            self.target_combo.addItem(self.t(key), data)
        self.target_combo.setCurrentIndex(0)
        self.target_combo.currentIndexChanged.connect(self._sync_settings_menus)
        form.addRow(self.t("lbl_target_lang"), self.target_combo)

        self.engine_combo = QComboBox()
        self.engine_combo.setAccessibleName(self.t("acc_engine_n"))
        self.engine_combo.setAccessibleDescription(self.t("acc_engine_d"))
        self.engine_combo.setToolTip(self.t("acc_engine_d"))
        for key, data in ENGINE_COMBO_ITEMS:
            self.engine_combo.addItem(self.t(key), data)
        self.engine_combo.currentIndexChanged.connect(self._on_engine_combo)
        form.addRow(self.t("lbl_engine"), self.engine_combo)

        outer.addWidget(options_group)

        # --------------------------------------------------- 3. run task
        run_group = QGroupBox(self.t("grp_run"))
        run_group.setAccessibleName(self.t("acc_run_n"))
        run_group.setAccessibleDescription(self.t("acc_run_d"))
        run_layout = QHBoxLayout(run_group)
        self.start_button = QPushButton(self.t("btn_start"))
        self.start_button.setAccessibleName(self.t("acc_start_n"))
        self.start_button.setAccessibleDescription(self.t("acc_start_d"))
        self.start_button.setToolTip("Keyboard: F5")
        self.start_button.setShortcut(QKeySequence("F5"))
        self.start_button.clicked.connect(self.start_task)
        self.start_button.setDefault(True)

        self.cancel_button = QPushButton(self.t("btn_cancel"))
        self.cancel_button.setAccessibleName(self.t("acc_cancel_n"))
        self.cancel_button.setAccessibleDescription(self.t("acc_cancel_d"))
        self.cancel_button.clicked.connect(self.cancel_work)
        self.cancel_button.setEnabled(False)

        run_layout.addWidget(self.start_button)
        run_layout.addWidget(self.cancel_button)
        run_layout.addStretch(1)
        outer.addWidget(run_group)

        # ---------------------------------------------------- 4. progress
        progress_group = QGroupBox(self.t("grp_progress"))
        progress_group.setAccessibleName(self.t("acc_progress_group_n"))
        progress_group.setAccessibleDescription(self.t("acc_progress_group_d"))
        progress_layout = QVBoxLayout(progress_group)
        self.status_label = QLabel(self.t("status_prefix") + " " + self.t("status_ready"))
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAccessibleName(self.t("acc_status_n"))
        self.status_label.setAccessibleDescription(self.t("acc_status_d"))
        self.status_label.setWordWrap(True)
        self.status_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        progress_layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        # Focusable on purpose: a keyboard user can park on it and the screen
        # reader reads the percentage back at any time.
        self.progress_bar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.progress_bar.setAccessibleName(self.t("acc_progress_n"))
        self.progress_bar.setAccessibleDescription(self.t("acc_progress_d", value=0))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        outer.addWidget(progress_group)

        # ----------------------------------------------------- 5. results
        results_group = QGroupBox(self.t("grp_results"))
        results_group.setAccessibleName(self.t("acc_results_n"))
        results_group.setAccessibleDescription(self.t("acc_results_d"))
        results_layout = QVBoxLayout(results_group)
        # A plain, fully editable multiline text control: every standard
        # Windows editing key works, one subtitle segment per line, and the
        # caret is never moved or taken away from the user.
        self.editor = QPlainTextEdit()
        self.editor.setAccessibleName(self.t("acc_editor_n"))
        self.editor.setAccessibleDescription(self.t("acc_editor_d", count=0))
        self.editor.setPlaceholderText(self.t("editor_placeholder"))
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.setTabChangesFocus(True)
        results_layout.addWidget(self.editor, 1)

        result_buttons = QHBoxLayout()
        self.save_button = QPushButton(self.t("btn_save_results"))
        self.save_button.setAccessibleName(self.t("acc_save_results_n"))
        self.save_button.setAccessibleDescription(self.t("acc_save_results_d"))
        self.save_button.setToolTip("Keyboard: Ctrl+S")
        self.save_button.clicked.connect(self.export_srt)
        self.copy_button = QPushButton(self.t("btn_copy"))
        self.copy_button.setAccessibleName(self.t("acc_copy_n"))
        self.copy_button.setAccessibleDescription(self.t("acc_copy_d"))
        self.copy_button.setToolTip("Keyboard: Ctrl+Shift+C")
        self.copy_button.clicked.connect(self.copy_results)
        self.export_button = QPushButton(self.t("btn_export"))
        self.export_button.setAccessibleName(self.t("acc_export_n"))
        self.export_button.setAccessibleDescription(self.t("acc_export_d"))
        self.export_button.setToolTip("Keyboard: Ctrl+E")
        self.export_button.clicked.connect(self.export_results)
        self.timestamps_check = QCheckBox(self.t("chk_show_timestamps"))
        self.timestamps_check.setAccessibleName(self.t("acc_timestamps_n"))
        self.timestamps_check.setAccessibleDescription(self.t("acc_timestamps_d"))
        self.timestamps_check.setToolTip("Keyboard: Ctrl+Shift+T")
        self.timestamps_check.setChecked(self.show_timestamps)
        self.timestamps_check.toggled.connect(self._on_timestamps_toggled)
        result_buttons.addWidget(self.save_button)
        result_buttons.addWidget(self.copy_button)
        result_buttons.addWidget(self.export_button)
        result_buttons.addWidget(self.timestamps_check)
        result_buttons.addStretch(1)
        results_layout.addLayout(result_buttons)
        outer.addWidget(results_group, 3)

        self.statusBar().setAccessibleName(self.t("acc_status_n"))
        self.statusBar().showMessage(self.t("status_ready"))

        # Controls that live only in the menu bar now.  They stay alive as
        # objects (the menus and the translation code drive them) but are
        # hidden, so neither the tab order nor a screen reader ever meets
        # them on the main screen.
        self.interface_label = QLabel(self)
        self.interface_label.hide()
        if self.interface_combo.parent() is None:
            self.interface_combo.setParent(self)
        self.interface_combo.hide()
        if self.high_contrast_check is None:
            self.high_contrast_check = QCheckBox(self.t("chk_high_contrast"), self)
            self.high_contrast_check.toggled.connect(self.apply_theme)
        self.high_contrast_check.hide()

        previous = None
        for widget in (
            self.open_button,
            self.task_combo,
            self.language_combo,
            self.target_combo,
            self.engine_combo,
            self.start_button,
            self.cancel_button,
            self.status_label,
            self.progress_bar,
            self.editor,
            self.save_button,
            self.copy_button,
            self.export_button,
            self.timestamps_check,
        ):
            if previous is not None:
                self.setTabOrder(previous, widget)
            previous = widget

        self._title_map = [
            (input_group, "grp_video"),
            (options_group, "grp_task"),
            (run_group, "grp_run"),
            (progress_group, "grp_progress"),
            (results_group, "grp_results"),
        ]
        self._text_map = [
            (self.open_button, "btn_open"),
            (self.start_button, "btn_start"),
            (self.cancel_button, "btn_cancel"),
            (self.save_button, "btn_save_results"),
            (self.copy_button, "btn_copy"),
            (self.export_button, "btn_export"),
            (self.timestamps_check, "chk_show_timestamps"),
            (self.drop_hint, "lbl_drop_hint"),
            (self.high_contrast_check, "chk_high_contrast"),
        ]
        self._acc_map = [
            (self.open_button, "acc_open_n", "acc_open_d"),
            (self.path_label, "acc_path_n", "acc_path_d"),
            (self.task_combo, "acc_task_n", "acc_task_d"),
            (self.language_combo, "acc_audio_lang_n", "acc_audio_lang_d"),
            (self.target_combo, "acc_target_n", "acc_target_d"),
            (self.engine_combo, "acc_engine_n", "acc_engine_d"),
            (self.start_button, "acc_start_n", "acc_start_d"),
            (self.cancel_button, "acc_cancel_n", "acc_cancel_d"),
            (self.editor, "acc_editor_n", "acc_editor_d"),
            (self.save_button, "acc_save_results_n", "acc_save_results_d"),
            (self.copy_button, "acc_copy_n", "acc_copy_d"),
            (self.export_button, "acc_export_n", "acc_export_d"),
            (self.timestamps_check, "acc_timestamps_n", "acc_timestamps_d"),
            (self.status_label, "acc_status_n", "acc_status_d"),
            (self.progress_bar, "acc_progress_n", "acc_progress_d"),
            (self.interface_combo, "acc_iface_n", "acc_iface_d"),
            (self.high_contrast_check, "acc_high_n", "acc_high_d"),
        ]
        self._label_map = [
            (form, self.task_combo, "lbl_task"),
            (form, self.language_combo, "lbl_source_lang"),
            (form, self.target_combo, "lbl_target_lang"),
            (form, self.engine_combo, "lbl_engine"),
        ]
        self.setAcceptDrops(True)

    def _on_interface_lang(self, index):
        data = self.interface_combo.itemData(index)
        lang = data if data in ("en", "ar") else "en"
        if lang == self.current_lang:
            return
        if self.worker_thread is not None and self.worker_thread.isRunning():
            block = self.interface_combo.blockSignals(True)
            self.interface_combo.setCurrentIndex(
                IFACE_COMBO_ITEMS.index(
                    next(item for item in IFACE_COMBO_ITEMS if item[1] == self.current_lang)
                )
            )
            self.interface_combo.blockSignals(block)
            self._sync_settings_menus()
            QMessageBox.warning(
                self,
                self.t("title_busy"),
                self.t("msg_busy_lang"),
            )
            return
        self.current_lang = lang
        self._retranslate_ui()

    def _retranslate_ui(self):
        self.setWindowTitle(self.t("app_title"))
        for menu, key in self._menu_map:
            menu.setTitle(self.t(key))
        for act, key in self._action_map:
            act.setText(self.t(key))
            try:
                act.setAccessibleText(self.t(key))
            except Exception:
                pass
        for widget, key in self._title_map:
            widget.setTitle(self.t(key))
        for widget, key in self._text_map:
            widget.setText(self.t(key))
        for widget, name_key, desc_key in self._acc_map:
            widget.setAccessibleName(self.t(name_key))
            if desc_key == "acc_editor_d":
                widget.setAccessibleDescription(
                    self.t(desc_key, count=len(self.subtitles))
                )
            elif desc_key == "acc_progress_d":
                widget.setAccessibleDescription(
                    self.t(desc_key, value=self.progress_bar.value())
                )
            else:
                widget.setAccessibleDescription(self.t(desc_key))
        self.interface_label.setText(self.t("lbl_interface_lang"))
        self.interface_label.setAccessibleName(self.t("acc_lang_label_n"))
        for i, (key, _data) in enumerate(IFACE_COMBO_ITEMS):
            self.interface_combo.setItemText(i, self.t(key))
        for i, (key, _data) in enumerate(LANG_COMBO_ITEMS):
            self.language_combo.setItemText(i, self.t(key))
        for i, (key, _data) in enumerate(TARGET_COMBO_ITEMS):
            self.target_combo.setItemText(i, self.t(key))
        for i, (key, _data) in enumerate(TASK_COMBO_ITEMS):
            self.task_combo.setItemText(i, self.t(key))
        for i, (key, _data) in enumerate(ENGINE_COMBO_ITEMS):
            self.engine_combo.setItemText(i, self.t(key))
        form = self.language_combo.parentWidget().layout()
        if isinstance(form, QFormLayout):
            for field, label_key in (
                (self.task_combo, "lbl_task"),
                (self.language_combo, "lbl_source_lang"),
                (self.target_combo, "lbl_target_lang"),
                (self.engine_combo, "lbl_engine"),
            ):
                label = form.labelForField(field)
                if label is not None:
                    label.setText(self.t(label_key))
                    label.setAccessibleName(self.t(label_key))
                    label.setBuddy(field)
        if not self.video_path:
            self.path_label.setText(self.t("lbl_no_video"))
        self.status_label.setText(self.t("status_prefix") + " " + self.t("status_ready"))
        self.statusBar().showMessage(self.t("status_ready"))
        self.statusBar().setAccessibleName(self.t("acc_status_n"))

        direction = (
            Qt.LayoutDirection.RightToLeft
            if self.current_lang == "ar"
            else Qt.LayoutDirection.LeftToRight
        )
        QApplication.setLayoutDirection(direction)
        if self.subtitles:
            self.populate_editor()
        if self.interface_combo.count() > 0:
            self.interface_combo.setCurrentIndex(
                IFACE_COMBO_ITEMS.index(
                    next(item for item in IFACE_COMBO_ITEMS if item[1] == self.current_lang)
                )
            )
        self._sync_settings_menus()
        QApplication.processEvents()
        self.announce(self.t("status_ready"))

    # ---------------------------------------------------------------- theme
    def apply_theme(self):
        self.high_contrast = self.high_contrast_check.isChecked()
        try:
            import vt_a11y

            a11y = vt_a11y.load()
        except Exception:  # noqa: BLE001 - the theme must always be applied
            a11y = {}
        large_focus = bool(a11y.get("large_focus", False))
        if self.high_contrast:
            stylesheet = (
                "QMainWindow, QWidget { background-color: #000000; color: #FFFFFF; font-size: 12pt; }"
                "QGroupBox { border: 2px solid #FFFF00; border-radius: 4px; margin-top: 10px; "
                "background-color: #000000; }"
                "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; "
                "color: #FFFF00; font-weight: bold; }"
                "QPushButton, QComboBox, QCheckBox { background-color: #000080; color: #FFFF00; "
                "border: 2px solid #FFFF00; padding: 6px 10px; min-height: 20px; }"
                "QPushButton:focus, QComboBox:focus, QCheckBox:focus, QPlainTextEdit:focus { "
                "border: 3px solid #00FFFF; }"
                "QPushButton:hover { background-color: #0000B0; }"
                "QPushButton:disabled { color: #888888; border-color: #888888; "
                "background-color: #101010; }"
                "QPlainTextEdit { background-color: #FFFFFF; color: #000000; border: 2px solid "
                "#FFFF00; }"
                "QPlainTextEdit::selection { background-color: #000080; color: #FFFFFF; }"
                "QProgressBar { border: 2px solid #FFFF00; background-color: #000000; "
                "color: #FFFFFF; text-align: center; }"
                "QProgressBar::chunk { background-color: #00FF00; }"
                'QLabel#statusLabel { background-color: #000000; color: #FFFF00; '
                "border: 2px solid #FFFF00; padding: 6px; font-weight: bold; }"
            )
        else:
            stylesheet = (
                "QMainWindow, QWidget { background-color: #1e1e1e; color: #e8e8e8; font-size: 11pt; }"
                "QGroupBox { border: 1px solid #555555; border-radius: 4px; margin-top: 10px; "
                "background-color: #252526; }"
                "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; "
                "color: #FFC107; font-weight: bold; }"
                "QPushButton, QComboBox, QCheckBox { background-color: #3c3c3c; color: #e8e8e8; "
                "border: 1px solid #666666; padding: 6px 10px; min-height: 20px; border-radius: 3px; }"
                "QPushButton:focus, QComboBox:focus, QCheckBox:focus, QPlainTextEdit:focus, "
                "QLabel#statusLabel:focus { border: 2px solid #FFC107; }"
                "QPushButton:hover { background-color: #505050; }"
                "QPushButton:disabled { color: #777777; border-color: #3a3a3a; }"
                "QPlainTextEdit { background-color: #1f1f1f; color: #e8e8e8; border: 1px solid "
                "#555555; }"
                "QPlainTextEdit::selection { background-color: #094771; color: #ffffff; }"
                "QProgressBar { border: 1px solid #555555; background-color: #101010; "
                "color: #e8e8e8; text-align: center; border-radius: 3px; }"
                "QProgressBar::chunk { background-color: #2d8cff; }"
                'QLabel#statusLabel { background-color: #121212; color: #FFC107; '
                "border: 1px solid #555555; padding: 6px; font-weight: bold; }"
            )
        if large_focus:
            # Thicker focus rectangle everywhere, including the controls whose
            # focus style the two themes above leave at their default width.
            stylesheet += (
                "QPushButton:focus, QComboBox:focus, QCheckBox:focus, "
                "QRadioButton:focus, QLineEdit:focus, QPlainTextEdit:focus, "
                "QLabel:focus, QMenuBar:focus, QMenu:focus, QTabBar:focus, "
                "QListWidget:focus, QTextBrowser:focus {"
                " border: 5px solid #00FFFF; outline: 5px solid #00FFFF; }"
            )
        self.setStyleSheet(stylesheet)
        self._sync_settings_menus()
        QApplication.processEvents()

    # ---------------------------------------------------------------- menus
    def _build_menus(self):
        """File, Edit, Settings, Accessibility, Tools, Models and Help.

        Every item carries a mnemonic (Alt + letter) and a shortcut that Qt
        prints next to it, and every one of them is reachable with the keyboard
        alone through the Alt key and the arrow keys.
        """
        mb = self.menuBar()
        mb.setNativeMenuBar(False)
        try:
            mb.setAccessibleName(self.t("acc_menu_n"))
            mb.setAccessibleDescription(self.t("acc_menu_d"))
        except Exception:
            pass
        self._iface_actions = {}
        self._view_high_act = None
        self._a11y_actions = {}
        self._model_actions = {}

        def top_menu(key):
            menu = QMenu(self.t(key), self)
            mb.addMenu(menu)
            self._menu_map.append((menu, key))
            return menu

        # ------------------------------------------------------------- File
        file_menu = top_menu("menu_file")
        self._make_action(file_menu, "act_open_video", self.select_video, "Ctrl+O")
        self._make_action(file_menu, "act_import_srt", self.import_srt, "Ctrl+I")
        self._make_action(file_menu, "act_export_srt", self.export_srt, "Ctrl+S")
        self._make_action(file_menu, "act_export", self.export_results, "Ctrl+E")
        self._make_action(file_menu, "act_render", self.render_video, "Ctrl+R")
        self._make_action(
            file_menu, "act_open_folder", self.open_output_folder, "Ctrl+Shift+W"
        )
        file_menu.addSeparator()
        self._make_action(file_menu, "act_exit", self.close, "Ctrl+Q")

        # ------------------------------------------------------------- Edit
        edit_menu = top_menu("menu_edit")
        self._make_action(edit_menu, "act_add_row", self.add_row, "Ctrl+Shift+N")
        self._make_action(
            edit_menu, "act_delete_row", self.delete_selected_rows, "Ctrl+Shift+D"
        )
        self._make_action(
            edit_menu, "act_copy_results", self.copy_results, "Ctrl+Shift+C"
        )

        # --------------------------------------------------------- Settings
        settings_menu = top_menu("menu_settings")
        self._make_action(
            settings_menu, "act_preferences", self.open_preferences, "Ctrl+,"
        )
        settings_menu.addSeparator()
        iface_group = QActionGroup(self)
        iface_group.setExclusive(True)
        for shortcut, lang in (("Ctrl+Shift+1", "en"), ("Ctrl+Shift+2", "ar")):
            act = self._make_action(
                settings_menu,
                "act_iface_" + lang,
                lambda checked, l=lang: self._on_iface_menu(l, checked),
                shortcut,
            )
            act.setCheckable(True)
            iface_group.addAction(act)
            self._iface_actions[lang] = act
        self._iface_group = iface_group

        # ----------------------------------------------------- Accessibility
        a11y_menu = top_menu("menu_accessibility")
        self._make_action(
            a11y_menu, "act_a11y_settings", self.open_accessibility, "Ctrl+Shift+A"
        )
        self._timestamps_act = self._make_action(
            a11y_menu, "act_timestamps", self._on_timestamps_action, "Ctrl+Shift+T"
        )
        self._timestamps_act.setCheckable(True)
        self._timestamps_act.setChecked(self.show_timestamps)
        a11y_menu.addSeparator()
        self._view_high_act = self._make_action(
            a11y_menu, "act_high_contrast", self._on_view_high_contrast, "Ctrl+Shift+H"
        )
        self._view_high_act.setCheckable(True)
        for key, shortcut, slot in (
            ("act_large_focus", "Ctrl+Shift+L", self._on_large_focus),
            ("act_simplified", "Ctrl+Shift+S", self._on_simplified),
            ("act_announce_progress", "Ctrl+Shift+P", self._on_announce_progress),
            ("act_sounds", "Ctrl+Shift+M", self._on_sounds),
        ):
            act = self._make_action(a11y_menu, key, slot, shortcut)
            act.setCheckable(True)
            self._a11y_actions[key] = act

        # ----------------------------------------------------------- Tools
        tools_menu = top_menu("menu_tools")
        self._make_action(tools_menu, "act_extract", self.extract_audio, "Ctrl+Shift+E")
        self._make_action(tools_menu, "act_cancel", self.cancel_work, "Ctrl+Shift+X")

        # ---------------------------------------------------------- Models
        models_menu = top_menu("menu_models")
        for key, name, shortcut in (
            ("act_model_tiny", "tiny", "Ctrl+1"),
            ("act_model_base", "base", "Ctrl+2"),
            ("act_model_small", "small", "Ctrl+3"),
        ):
            act = self._make_action(
                models_menu,
                key,
                lambda checked=False, model=name: self.download_model(model),
                shortcut,
            )
            self._model_actions[name] = (act, key)
        models_menu.addSeparator()
        self._make_action(
            models_menu, "act_model_status", self.show_model_status, "Ctrl+0"
        )

        # ------------------------------------------------------------- Help
        # The whole menu comes from help_menu.py: the combined guide, the
        # update checker, then the items the previous menu already had.
        import help_menu as help_menu_module

        help_menu = help_menu_module.build_help_menu(self)
        mb.addMenu(help_menu)
        self._menu_map.append((help_menu, "menu_help"))

        self._sync_settings_menus()

    def _make_action(self, menu, key, callback, shortcut=None):
        act = QAction(self.t(key), self)
        if shortcut:
            try:
                act.setShortcut(QKeySequence(shortcut))
            except Exception:
                pass
        act.triggered.connect(callback)
        try:
            act.setAccessibleText(self.t(key))
        except Exception:
            pass
        menu.addAction(act)
        self._action_map.append((act, key))
        return act

    def _sync_settings_menus(self, *_args):
        for lang, act in self._iface_actions.items():
            act.setChecked(lang == self.current_lang)
        if self._view_high_act is not None and self.high_contrast_check is not None:
            self._view_high_act.setChecked(self.high_contrast_check.isChecked())
        try:
            import vt_a11y

            settings = vt_a11y.load()
        except Exception:  # noqa: BLE001 - menus must always render
            settings = {}
        flags = {
            "act_large_focus": settings.get("large_focus", False),
            "act_simplified": settings.get("simplified_layout", False),
            "act_announce_progress": settings.get("announce_progress", True),
            "act_sounds": settings.get("sounds", True),
        }
        for key, checked in flags.items():
            act = self._a11y_actions.get(key)
            if act is not None:
                act.setChecked(bool(checked))
        timestamps_act = getattr(self, "_timestamps_act", None)
        if timestamps_act is not None and getattr(self, "timestamps_check", None) is not None:
            timestamps_act.setChecked(self.timestamps_check.isChecked())
        for name, (act, key) in getattr(self, "_model_actions", {}).items():
            text = self.t(key)
            try:
                import vt_install

                if vt_install.model_is_cached(name):
                    text += self.t("model_installed")
            except Exception:  # noqa: BLE001 - status text is best effort
                pass
            act.setText(text)

    def _output_key(self):
        data = self.target_combo.currentData()
        if data == "none":
            return "out_orig"
        if data == "bilingual":
            return "out_both"
        return "out_trans"

    def _settings_busy_guard(self):
        if self.worker_thread is not None and self.worker_thread.isRunning():
            QMessageBox.warning(self, self.t("title_busy"), self.t("body_busy"))
            self._sync_settings_menus()
            return True
        return False

    def _set_combo_by_data(self, combo, options, data):
        for i, (key, value) in enumerate(options):
            if value == data:
                combo.setCurrentIndex(i)
                return

    def _on_iface_menu(self, lang, checked):
        if not checked:
            return
        idx = IFACE_COMBO_ITEMS.index(
            next(item for item in IFACE_COMBO_ITEMS if item[1] == lang)
        )
        self.interface_combo.setCurrentIndex(idx)
        self._sync_settings_menus()

    def _on_view_high_contrast(self, checked):
        if self.high_contrast_check.isChecked() != checked:
            self.high_contrast_check.setChecked(checked)
        self._set_a11y("high_contrast", checked)
        self.apply_theme()

    def _on_large_focus(self, checked):
        self._set_a11y("large_focus", checked)
        self.apply_theme()
        self.announce(
            self.t("msg_a11y_large_focus_on") if checked else self.t("msg_a11y_large_focus_off")
        )

    def _on_simplified(self, checked):
        self._set_a11y("simplified_layout", checked)
        self.apply_layout_mode()
        self.announce(
            self.t("msg_a11y_simplified_on") if checked else self.t("msg_a11y_simplified_off")
        )

    def _on_announce_progress(self, checked):
        self._set_a11y("announce_progress", checked)
        self.announce(
            self.t("msg_a11y_announce_on") if checked else self.t("msg_a11y_announce_off")
        )

    def _on_sounds(self, checked):
        self._set_a11y("sounds", checked)
        self.announce(
            self.t("msg_a11y_sounds_on") if checked else self.t("msg_a11y_sounds_off")
        )

    # ---------------------------------------------------------- timestamps
    def _on_timestamps_action(self, checked):
        """Accessibility -> Show timestamps (Ctrl+Shift+T)."""
        if self.timestamps_check.isChecked() != checked:
            self.timestamps_check.setChecked(checked)  # runs the shared path
        else:
            self._apply_timestamps(checked)

    def _on_timestamps_toggled(self, checked):
        self._apply_timestamps(checked)

    def _apply_timestamps(self, checked):
        """Switch the editor between timestamped and plain caption lines.

        Whatever the user has typed is read back first, so turning the
        timestamps on or off never throws an edit away, and neither the
        caret nor the focus is moved while the text is redrawn.
        """
        try:
            subs = self.read_subtitles_from_editor(confirm=False)
            if subs is not None:
                self.subtitles = subs
        except ValueError:
            pass  # malformed text stays untouched until it is fixed
        self.show_timestamps = bool(checked)
        block = self.timestamps_check.blockSignals(True)
        self.timestamps_check.setChecked(bool(checked))
        self.timestamps_check.blockSignals(block)
        act = getattr(self, "_timestamps_act", None)
        if act is not None:
            block = act.blockSignals(True)
            act.setChecked(bool(checked))
            act.blockSignals(block)
        try:
            import vt_prefs

            vt_prefs.save({"show_timestamps": "true" if checked else "false"})
        except Exception:  # noqa: BLE001 - the toggle still applies this run
            logging.exception("the timestamp preference could not be saved")
        self.populate_editor()
        self.announce(
            self.t("msg_timestamps_on") if checked else self.t("msg_timestamps_off")
        )

    def _set_a11y(self, key, value):
        try:
            import vt_a11y

            vt_a11y.update(**{key: bool(value)})
        except Exception:  # noqa: BLE001 - never block the toggle itself
            logging.exception("accessibility setting could not be saved")

    # ------------------------------------------------------- preferences / engines
    def open_preferences(self):
        """Settings -> Speech && Translation Settings (Ctrl+,)."""
        try:
            import vt_settings
        except Exception as exc:  # noqa: BLE001 - optional module must not crash us
            QMessageBox.warning(
                self, self.t("title_settings_error"), str(exc)
            )
            return
        if self._settings_busy_guard():
            return
        data = vt_settings.open_settings(lang=self.current_lang, parent=self)
        if data:
            self.announce(self.t("msg_settings_saved"))

    def _engine_choice(self, task):
        """Return ``(engine, key, model_ok)`` for a task, or ``None`` to abort.

        Popups appear when a cloud engine is selected without a usable key, and
        the user can fall back to the free local engine in one click instead of
        the task failing later with a raw error.
        """
        import vt_prefs

        chosen = "auto"
        if getattr(self, "engine_combo", None) is not None:
            chosen = self.engine_combo.currentData() or "auto"
        automatic = chosen in ("auto", "", None)
        prefs = vt_prefs.normalized(vt_prefs.load())
        if not automatic and chosen in vt_prefs.ENGINES:
            # The list on the main screen wins over the stored preference, so
            # what the user sees is always what runs.
            engine = chosen
        elif task == "transcribe":
            engine = prefs["transcribe_engine"]
        else:
            engine = prefs["translate_engine"]
        if not vt_prefs.needs_key(engine):
            return engine, "", True
        key = prefs.get(engine + "_api_key", "")
        bad_key = [
            message
            for field, message in vt_prefs.validate(prefs, self.current_lang)
            if field == engine + "_api_key"
        ]
        if not key or bad_key:
            key = ""
        if key:
            return engine, key, True

        if automatic:
            # Task 6: with "Automatic" the program picks the free local
            # engine on its own instead of stopping to ask, and says so.
            self.announce(
                self.t(
                    "msg_fallback_engine",
                    engine=vt_prefs.ENGINE_LABELS.get(engine, engine),
                )
            )
            return "local", "", True

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(self.t("msg_api_fallback_title"))
        box.setText(
            self.t(
                "msg_api_fallback",
                msg=self.t("err_api_key_missing", engine=vt_prefs.ENGINE_LABELS.get(engine, engine)),
            )
        )
        use_local = box.addButton(self.t("btn_use_local"), QMessageBox.ButtonRole.AcceptRole)
        open_settings = box.addButton(self.t("btn_open_settings"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(open_settings)
        box.exec()
        if box.clickedButton() is use_local:
            return "local", "", True
        if box.clickedButton() is open_settings:
            self.open_preferences()
            return self._engine_choice_retry(task)
        return None

    def _engine_choice_retry(self, task):
        """Re-read the preferences after the user closed the settings dialog."""
        import vt_prefs

        prefs = vt_prefs.normalized(vt_prefs.load())
        chosen = "auto"
        if getattr(self, "engine_combo", None) is not None:
            chosen = self.engine_combo.currentData() or "auto"
        if chosen in vt_prefs.ENGINES:
            engine = chosen
        else:
            engine = (
                prefs["transcribe_engine"]
                if task == "transcribe"
                else prefs["translate_engine"]
            )
        if vt_prefs.needs_key(engine) and not prefs.get(engine + "_api_key", ""):
            return None
        return engine, prefs.get(engine + "_api_key", ""), True

    # ------------------------------------------------------------ help menu
    def _open_help(self, topic_id=None, focus_text=False):
        """Help -> User Guide (F1) and Keyboard Shortcuts (Ctrl+/).

        The topics come from resources/help/<lang>/<topic>.md through
        vt_help: a Contents list on the left, a read-only text area on the
        right, and a search that announces how many topics matched.  The
        shortcut topic is completed from the actions of this window, so the
        list always matches the shortcuts the program really has.
        """
        import vt_help

        title = self.t(
            "help_title_shortcuts" if topic_id == "shortcuts" else "help_title_guide"
        )
        topics = vt_help.build_topics(self.current_lang, self)
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setAccessibleName(title)
        dlg.setModal(True)
        if self.current_lang == "ar":
            dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QVBoxLayout(dlg)
        body = QHBoxLayout()

        left = QVBoxLayout()
        search_row = QHBoxLayout()
        search_label = QLabel(self.t("help_search_n"))
        search_edit = QLineEdit()
        search_edit.setAccessibleName(self.t("help_search_n"))
        search_edit.setAccessibleDescription(self.t("help_search_d"))
        search_button = QPushButton(self.t("help_search_btn"))
        search_button.setAccessibleName(self.t("help_search_btn"))
        search_row.addWidget(search_label)
        search_row.addWidget(search_edit, 1)
        search_row.addWidget(search_button)
        left.addLayout(search_row)

        results_label = QLabel("")
        results_label.setAccessibleName(self.t("help_results_n"))
        left.addWidget(results_label)
        results = QListWidget()
        results.setAccessibleName(self.t("help_results_n"))
        results.setAccessibleDescription(self.t("help_results_d", count=0))
        results.hide()
        left.addWidget(results, 1)

        contents_label = QLabel(self.t("help_contents_n"))
        contents = QListWidget()
        contents.setAccessibleName(self.t("help_contents_n"))
        contents.setAccessibleDescription(self.t("help_hint"))
        for topic in topics:
            item = QListWidgetItem(topic["title"])
            item.setData(Qt.ItemDataRole.UserRole, topic["id"])
            contents.addItem(item)
        left.addWidget(contents_label)
        left.addWidget(contents, 1)

        hint = QLabel(self.t("help_hint"))
        hint.setWordWrap(True)
        hint.setAccessibleName(self.t("help_hint"))
        left.addWidget(hint)
        back_button = QPushButton(self.t("help_back"))
        back_button.setAccessibleName(self.t("help_back"))
        left.addWidget(back_button)
        close_button = QPushButton(self.t("btn_close"))
        close_button.setAccessibleName(title + " " + self.t("btn_close"))
        close_button.clicked.connect(dlg.accept)
        left.addWidget(close_button)
        # Enter on a contents or result list activates the item and then
        # keeps travelling to the dialog, where a default push button would
        # swallow it, click itself and pull the focus away from the text the
        # user just asked to read.  No button in this dialog may act as the
        # default.
        for button in (search_button, back_button, close_button):
            button.setAutoDefault(False)
            button.setDefault(False)

        right = QVBoxLayout()
        heading = QLabel("")
        heading.setWordWrap(True)
        right.addWidget(heading)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setAccessibleName(self.t("help_text_n"))
        text.setAccessibleDescription(self.t("help_text_d"))
        text.setFont(QFont("Consolas", 10))
        right.addWidget(text, 1)

        body.addLayout(left, 1)
        body.addLayout(right, 2)
        layout.addLayout(body, 1)

        def open_topic(tid, focus=False):
            topic = next((entry for entry in topics if entry["id"] == tid), None)
            if topic is None:
                return
            heading.setText(topic["title"])
            heading.setAccessibleName(topic["title"])
            text.setPlainText(topic["body"])
            text.verticalScrollBar().setValue(0)
            for row in range(contents.count()):
                if contents.item(row).data(Qt.ItemDataRole.UserRole) == tid:
                    blocked = contents.blockSignals(True)
                    contents.setCurrentRow(row)
                    contents.blockSignals(blocked)
                    break
            if focus:
                text.setFocus(Qt.FocusReason.ShortcutFocusReason)

        def on_row_changed(row):
            item = contents.item(row)
            if item is not None:
                open_topic(item.data(Qt.ItemDataRole.UserRole))

        def on_topic_activated(item):
            open_topic(item.data(Qt.ItemDataRole.UserRole), focus=True)

        contents.currentRowChanged.connect(on_row_changed)
        contents.itemActivated.connect(on_topic_activated)

        def do_search():
            query = search_edit.text().strip()
            found = vt_help.search(topics, query) if query else []
            results.clear()
            for tid, topic_title, snippet in found:
                row_text = (
                    topic_title + " - " + snippet if snippet else topic_title
                )
                item = QListWidgetItem(row_text)
                item.setData(Qt.ItemDataRole.UserRole, tid)
                results.addItem(item)
            results.setVisible(bool(found))
            if query:
                if found:
                    message = self.t("help_results_count", count=len(found))
                else:
                    message = self.t("help_no_results")
                results_label.setText(message)
                self.announce(message)
            else:
                results_label.setText("")

        search_button.clicked.connect(do_search)
        search_edit.returnPressed.connect(do_search)
        results.itemActivated.connect(on_topic_activated)

        def back_to_contents():
            contents.setFocus(Qt.FocusReason.ShortcutFocusReason)

        back_button.clicked.connect(back_to_contents)

        escape_text = QShortcut(QKeySequence("Escape"), text)
        escape_text.setContext(Qt.ShortcutContext.WidgetShortcut)
        escape_text.activated.connect(back_to_contents)
        escape_search = QShortcut(QKeySequence("Escape"), search_edit)
        escape_search.setContext(Qt.ShortcutContext.WidgetShortcut)

        def clear_search():
            search_edit.clear()
            do_search()

        escape_search.activated.connect(clear_search)

        def toggle_focus():
            if dlg.focusWidget() is text:
                back_to_contents()
            else:
                text.setFocus(Qt.FocusReason.ShortcutFocusReason)

        f6 = QShortcut(QKeySequence("F6"), dlg)
        f6.activated.connect(toggle_focus)

        dlg.resize(980, 640)
        if topic_id is None:
            if contents.count():
                contents.setCurrentRow(0)
        else:
            open_topic(topic_id, focus=focus_text)
        if focus_text:
            text.setFocus(Qt.FocusReason.ShortcutFocusReason)
        else:
            contents.setFocus(Qt.FocusReason.OtherFocusReason)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        self._help_dlg = dlg
        return dlg

    def show_user_guide(self):
        return self._open_help()

    def show_shortcuts(self):
        return self._open_help("shortcuts", focus_text=True)

    def open_guide_file(self):
        return self._open_help_file("guide")

    def open_shortcut_file(self):
        return self._open_help_file("shortcuts")

    def _open_help_file(self, kind):
        """Help -> Open Guide/Shortcut File: the detailed HTML documents.

        The files carry real headings, so a screen reader can jump from
        heading to heading while the same page stays readable for everyone
        in an ordinary browser.
        """
        import vt_help

        path = vt_help.html_path(self.current_lang, kind)
        if path and vt_help.open_html(path):
            self.announce(self.t("msg_help_file_open"))
            return True
        self.announce(self.t("msg_help_file_missing"))
        return False

    def show_about(self):
        """F12: the About page, the only help dialog without contents."""
        title = self.t("help_title_about")
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setAccessibleName(title)
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(True)
        browser.setHtml(self.t("help_about"))
        browser.setAccessibleName(title)
        layout.addWidget(browser, 1)
        close_button = QPushButton(self.t("btn_close"))
        close_button.setAccessibleName(title + " " + self.t("btn_close"))
        close_button.clicked.connect(dlg.accept)
        layout.addWidget(close_button)
        dlg.resize(780, 640)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        browser.setFocus(Qt.FocusReason.OtherFocusReason)
        self._help_dlg = dlg
        return dlg

    # ---------------------------------------------------------- accessibility
    def announce(self, text, show_box=False, kind=None):
        self.status_label.setText(self.t("status_prefix") + " " + text)
        self.status_label.setAccessibleName(self.t("acc_status_n") + ": " + text)
        self.statusBar().showMessage(text)
        if QAccessible is not None:
            try:
                QAccessible.updateAccessibility()
            except Exception:
                pass
        try:
            QApplication.alert(self)
        except Exception:
            pass
        if show_box:
            self.feedback(kind or "ok")
            QMessageBox.information(self, self.t("title_task_complete"), text)

    def feedback(self, kind="ok"):
        """Short audible confirmation, honouring the Sounds accessibility flag."""
        try:
            import vt_a11y

            if not vt_a11y.load().get("sounds", True):
                return
        except Exception:  # noqa: BLE001 - no settings, no sound
            return
        try:
            import winsound

            alias = "SystemAsterisk" if kind == "ok" else "SystemExclamation"
            winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception:  # noqa: BLE001 - sound is never essential
            pass

    def set_busy(self, busy):
        for widget in (
            self.open_button,
            self.task_combo,
            self.language_combo,
            self.target_combo,
            self.engine_combo,
            self.start_button,
            self.save_button,
            self.copy_button,
            self.export_button,
            self.timestamps_check,
        ):
            widget.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.editor.setEnabled(not busy)

    def _start_thread(self, thread, on_completed):
        if self.worker_thread is not None and self.worker_thread.isRunning():
            QMessageBox.information(self, self.t("title_busy"), self.t("body_busy"))
            return False
        self.worker_thread = thread
        thread.progress.connect(self.on_progress)
        thread.stages.connect(self._announce_stage)
        thread.completed.connect(on_completed)
        thread.failed.connect(self.on_failed)
        self._last_announced = -1
        thread.start()
        self.set_busy(True)
        self.announce(self.t("msg_progress", value=0))
        return True

    def on_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_bar.setAccessibleDescription(
            self.t("acc_progress_d", value=value)
        )
        # Progress is spoken at the frequency the user chose in the
        # Accessibility settings (every 1, 5, 10, 25 percent or never);
        # 0 and 100 are always announced so start and finish are never lost.
        step = self._announce_step()
        if value in (0, 100) or value >= self._last_announced + step:
            self._last_announced = value
            self.announce(self.t("msg_progress", value=value))

    def _announce_stage(self, text):
        """Stage messages follow the "announce progress" accessibility flag."""
        try:
            import vt_a11y

            if not vt_a11y.load().get("announce_progress", True):
                return
        except Exception:  # noqa: BLE001 - no settings, no announcement
            return
        self.announce(text)

    def _announce_step(self):
        try:
            import vt_a11y

            settings = vt_a11y.load()
            if not settings.get("announce_progress", True):
                return 101
            return max(1, int(settings.get("announce_every", 5)))
        except Exception:  # noqa: BLE001 - progress must never fail
            return 5

    def on_failed(self, message):
        self.set_busy(False)
        self.announce(self.t("status_task_failed", msg=message), show_box=True, kind="error")
        logging.error(message)
        logging.error(traceback.format_exc())

    def _release_thread(self):
        self.worker_thread = None

    # ---------------------------------------------------------------- tasks
    def select_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.t("dlg_open_video"),
            "",
            self.t("dlg_video_filter"),
        )
        if not path:
            self.announce(self.t("msg_video_select_cancel"))
            return
        self.video_path = path
        self.audio_path = ""
        self.detected_language = "auto"
        self.path_label.setText(path)
        name = os.path.basename(path)
        self.announce(self.t("msg_video_selected", name=name, path=path))
        self.path_label.setAccessibleName(self.t("acc_path_n") + ": " + path)

    def extract_audio(self):
        if not self._require_video():
            return
        audio = os.path.join(self.temp_dir, "audio.wav")
        thread = ExtractAudioThread(self.video_path, audio, lang=self.current_lang)
        if self._start_thread(thread, self._on_extract_done):
            self.announce(self.t("msg_extract_start"))

    def _on_extract_done(self, audio_path):
        self.audio_path = audio_path
        self.set_busy(False)
        self._release_thread()
        self.announce(self.t("msg_extract_done", path=audio_path), show_box=True)

    def _selected_model(self):
        """Recognition model from the preferences (Settings dialog)."""
        try:
            import vt_prefs

            return vt_prefs.normalized(vt_prefs.load())["whisper_model"]
        except Exception:  # noqa: BLE001 - never block transcription on this
            return "base"

    def transcribe(self):
        if not self._require_video():
            return
        choice = self._engine_choice("transcribe")
        if choice is None:
            self.announce(self.t("msg_task_cancelled"))
            return
        engine, api_key, _ok = choice
        language = self.language_combo.currentData()
        model = self._selected_model()
        if engine != "local":
            # Cloud engines use their own model ids (whisper-1, gemini-...).
            try:
                import vt_prefs

                model = vt_prefs.normalized(vt_prefs.load()).get(engine + "_model", model)
            except Exception:  # noqa: BLE001
                pass
        thread = TranscriptionThread(
            self.video_path,
            self.audio_path,
            language,
            self.temp_dir,
            model_name=model,
            lang=self.current_lang,
            engine=engine,
            api_key=api_key,
        )
        if self._start_thread(thread, self._on_transcribe_done):
            self.announce(self.t("msg_transcribe_start"))

    def _on_transcribe_done(self, subtitles, detected, audio_path):
        self.subtitles = subtitles
        self.detected_language = detected
        self.audio_path = audio_path
        self.populate_editor()
        lang_name = self.lang_name(detected)
        self.set_busy(False)
        self._release_thread()
        message = self.t("msg_transcribe_done", count=len(subtitles), language=lang_name)
        if (self.target_combo.currentData() or "none") != "none":
            # A target language was chosen: the translation starts right after
            # the transcription, without stopping for an extra dialog.
            self.feedback("ok")
            self.announce(message)
            self.announce(self.t("msg_translate_start"))
            QTimer.singleShot(0, self.translate)
            return
        self.feedback("ok")
        self.announce(message, show_box=True)

    def translate(self):
        try:
            subtitles = self.read_subtitles_from_editor()
        except ValueError as exc:
            QMessageBox.warning(self, self.t("title_invalid"), str(exc))
            return
        if subtitles is None:
            return
        if not subtitles:
            QMessageBox.warning(
                self,
                self.t("title_no_subs"),
                self.t("body_no_subs"),
            )
            return
        target = self.target_combo.currentData() or "none"
        if target == "none":
            self.announce(self.t("msg_no_translation"))
            return
        bilateral = target == "bilingual"
        source = self.detected_language
        if source in ("", "auto", None):
            source = self.language_combo.currentData() or "auto"
        source = source if isinstance(source, str) else "auto"
        if bilateral:
            detected = self.detected_language
            if detected == "ar":
                target = "en"
            elif detected in ("en", ""):
                target = "ar"
            else:
                target = "en"
        choice = self._engine_choice("translate")
        if choice is None:
            self.announce(self.t("msg_task_cancelled"))
            return
        engine, api_key, _ok = choice
        try:
            import vt_prefs

            translate_model = vt_prefs.normalized(vt_prefs.load()).get(
                engine + "_translate_model", ""
            )
        except Exception:  # noqa: BLE001
            translate_model = ""
        thread = TranslationThread(
            subtitles,
            source,
            target,
            bilateral,
            lang=self.current_lang,
            engine=engine,
            api_key=api_key,
            translate_model=translate_model,
        )
        if self._start_thread(thread, self._on_translate_done):
            self.announce(self.t("msg_translate_start"))

    def _on_translate_done(self, subtitles):
        self.subtitles = subtitles
        self.populate_editor()
        self.set_busy(False)
        self._release_thread()
        self.announce(
            self.t("msg_translate_done", count=len(subtitles)), show_box=True
        )

    def render_video(self):
        if not self._require_video():
            return
        try:
            subtitles = self.read_subtitles_from_editor()
        except ValueError as exc:
            QMessageBox.warning(self, self.t("title_invalid"), str(exc))
            return
        if subtitles is None:
            return
        if not subtitles:
            QMessageBox.warning(
                self,
                self.t("title_nothing_render"),
                self.t("body_no_subs"),
            )
            return

        default_name = os.path.splitext(os.path.basename(self.video_path))[0] + "_subtitled.mp4"
        default_dir = os.path.dirname(self.video_path)
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            self.t("dlg_save_video"),
            os.path.join(default_dir, default_name),
            self.t("dlg_mp4_filter"),
        )
        if not output_path:
            self.announce(self.t("msg_render_cancel"))
            return
        self.last_output_folder = os.path.dirname(output_path)
        thread = RenderThread(
            self.video_path,
            subtitles,
            output_path,
            self.temp_dir,
            font_path=FONT_PATH,
            lang=self.current_lang,
        )
        if self._start_thread(thread, self._on_render_done):
            self.announce(self.t("msg_render_start"))

    def _on_render_done(self, output_path):
        self.set_busy(False)
        self._release_thread()
        self.last_output_folder = os.path.dirname(output_path)
        self.announce(
            self.t("msg_render_done", path=output_path),
            show_box=True,
        )

    def cancel_work(self):
        if self.worker_thread is not None and self.worker_thread.isRunning():
            self.worker_thread.requestInterruption()
            self.announce(self.t("msg_cancel_requested"))

    # ------------------------------------------------------- run / clipboard
    def start_task(self):
        """F5: run whichever task is selected in the Task list."""
        if self._settings_busy_guard():
            return
        task = self.task_combo.currentData() or "transcribe"
        if task == "translate":
            self.translate()
        else:
            self.transcribe()

    def _on_engine_combo(self, *_args):
        """Remember an explicit engine choice in the preferences."""
        engine = self.engine_combo.currentData() or "auto"
        if engine == "auto":
            return
        try:
            import vt_prefs

            vt_prefs.save({"transcribe_engine": engine, "translate_engine": engine})
        except Exception:  # noqa: BLE001 - the choice still applies this run
            logging.exception("engine choice could not be saved")
        self.announce(self.t("msg_engine_chosen", engine=self.t("eng_" + engine)))

    def copy_results(self):
        """Ctrl+Shift+C: put every caption on the clipboard."""
        try:
            subtitles = self.read_subtitles_from_editor()
        except ValueError as exc:
            QMessageBox.warning(self, self.t("title_invalid"), str(exc))
            return
        if subtitles is None:
            return
        if not subtitles:
            QMessageBox.warning(
                self, self.t("title_nothing_export"), self.t("body_nothing_export")
            )
            return
        lines = []
        for s in subtitles:
            if self.show_timestamps:
                lines.append(
                    "[%s --> %s] %s"
                    % (format_timestamp(s.start), format_timestamp(s.end), s.content)
                )
            else:
                lines.append(s.content)
        QApplication.clipboard().setText("\n".join(lines))
        self.announce(self.t("msg_copy_done", count=len(subtitles)))

    # ------------------------------------------------------------- drag & drop
    def dragEnterEvent(self, event):
        if event is not None and event.mimeData() is not None:
            urls = event.mimeData().urls()
            if urls and os.path.splitext(urls[0].toLocalFile())[1]:
                event.acceptProposedAction()
                return
        if event is not None:
            event.ignore()

    def dropEvent(self, event):
        try:
            path = event.mimeData().urls()[0].toLocalFile()
        except Exception:  # noqa: BLE001 - a malformed drop simply does nothing
            return
        if not path or not os.path.isfile(path):
            self.announce(self.t("body_no_video"))
            return
        self.video_path = path
        self.audio_path = ""
        self.detected_language = "auto"
        self.path_label.setText(path)
        self.path_label.setAccessibleName(self.t("acc_path_n") + ": " + path)
        event.acceptProposedAction()
        self.announce(self.t("msg_dropped", name=os.path.basename(path), path=path))

    # ------------------------------------------------------------- help / logs
    def open_log_folder(self):
        """Help -> Open Log Folder (Ctrl+Shift+V)."""
        folder = ""
        try:
            import vt_bootstrap

            folder = os.path.dirname(vt_bootstrap.log_path())
        except Exception:  # noqa: BLE001 - fall back to the profile folder
            folder = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        try:
            os.makedirs(folder, exist_ok=True)
            os.startfile(folder)
            self.announce(self.t("msg_folder_opened", path=folder))
        except Exception as exc:  # noqa: BLE001 - reported, never raised
            QMessageBox.warning(self, self.t("title_settings_error"), str(exc))

    # ------------------------------------------------------- layout / a11y
    def apply_layout_mode(self):
        """Simplified layout hides the advanced pickers on the main screen."""
        try:
            import vt_a11y

            simplified = bool(vt_a11y.load().get("simplified_layout", False))
        except Exception:  # noqa: BLE001 - keep the normal layout on error
            simplified = False
        self.language_combo.setVisible(not simplified)
        self.engine_combo.setVisible(not simplified)
        self.drop_hint.setVisible(not simplified)
        form = self.language_combo.parentWidget().layout()
        if isinstance(form, QFormLayout):
            for field in (self.language_combo, self.engine_combo):
                label = form.labelForField(field)
                if label is not None:
                    label.setVisible(not simplified)
        if simplified:
            self.engine_combo.setCurrentIndex(0)

    # ---------------------------------------------------------- accessibility
    def open_accessibility(self):
        """Accessibility -> Accessibility Settings (Ctrl+Shift+A)."""
        try:
            import vt_a11y
        except Exception as exc:  # noqa: BLE001 - optional module must not crash us
            QMessageBox.warning(self, self.t("title_settings_error"), str(exc))
            return
        if self._settings_busy_guard():
            return
        vt_a11y.open_dialog(parent=self, lang=self.current_lang)
        self._sync_settings_menus()

    # -------------------------------------------------------------- models
    MODEL_EXPECTED_BYTES = {
        "tiny": 75_000_000,
        "base": 145_000_000,
        "small": 484_000_000,
    }

    def download_model(self, name):
        """Models -> Download the ... recognition model."""
        import vt_install

        if getattr(self, "_model_busy", False):
            return
        if vt_install.model_is_cached(name):
            self.announce(self.t("msg_model_cached", model=name))
            self._sync_settings_menus()
            return
        self._model_busy = True
        self._model_name = name
        self._model_result = [None]
        self._model_milestone = 0
        self.start_button.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.announce(self.t("msg_model_start", model=name))

        def worker():
            try:
                import vt_install as _install

                self._model_result[0] = _install.download_model(name)
            except Exception as exc:  # noqa: BLE001 - reported to the user below
                self._model_result[0] = "download failed: %s" % str(exc)[:120]

        import threading

        self._model_thread = threading.Thread(target=worker, daemon=True)
        self._model_thread.start()
        if self._model_timer is None:
            from PyQt6.QtCore import QTimer

            self._model_timer = QTimer(self)
            self._model_timer.setInterval(800)
            self._model_timer.timeout.connect(self._poll_model_download)
        self._model_timer.start()

    def _model_cache_bytes(self, name):
        roots = [
            os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"),
            os.path.join(os.environ.get("HF_HOME") or "", "hub"),
        ]
        folder_name = "models--Systran--faster-whisper-" + name
        total = 0
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(os.path.join(root, folder_name)):
                for filename in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, filename))
                    except OSError:
                        pass
        return total

    def _poll_model_download(self):
        name = self._model_name
        expected = self.MODEL_EXPECTED_BYTES.get(name) or 1
        done = self._model_cache_bytes(name)
        percent = max(0, min(99, int(done * 100 / expected)))
        self.progress_bar.setValue(percent)
        milestone = percent // 25
        if milestone > self._model_milestone:
            self._model_milestone = milestone
            self.announce(self.t("msg_model_progress", model=name, percent=percent))
        if not self._model_thread.is_alive():
            self._model_timer.stop()
            self._finish_model_download()

    def _finish_model_download(self):
        name = self._model_name
        result = self._model_result[0] or ""
        self._model_busy = False
        self.start_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self._sync_settings_menus()
        if str(result).startswith("download failed"):
            self.announce(
                self.t("msg_model_fail", model=name, error=str(result)),
                show_box=True,
                kind="error",
            )
            return
        self.progress_bar.setValue(100)
        self.feedback("ok")
        self.announce(self.t("msg_model_done", model=name))

    def show_model_status(self):
        """Models -> Model Status (Ctrl+0): plain text, easy to read aloud."""
        import vt_install

        lines = [self.t("msg_model_status_header")]
        for name in ("tiny", "base", "small"):
            cached = vt_install.model_is_cached(name)
            state = self.t("model_installed") if cached else self.t("model_missing")
            lines.append("%s: %s" % (name, state))
        try:
            folder = vt_install.model_dir("base") or ""
            if folder:
                lines.append(self.t("msg_model_folder", path=folder))
        except Exception:  # noqa: BLE001 - the folder line is optional
            pass
        QMessageBox.information(self, self.t("act_model_status"), "\n".join(lines))

    # ------------------------------------------------------------- license
    def show_license(self):
        """Help -> License Agreement (Ctrl+Shift+G)."""
        try:
            import vt_bootstrap

            filename = "agreement_ar.txt" if self.current_lang == "ar" else "agreement_en.txt"
            path = vt_bootstrap.resource_path("resources", filename)
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except Exception as exc:  # noqa: BLE001 - reported, never raised
            QMessageBox.warning(self, self.t("title_settings_error"), str(exc))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(self.t("act_license"))
        dlg.setAccessibleName(self.t("act_license"))
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setPlainText(text)
        browser.setAccessibleName(self.t("act_license"))
        layout.addWidget(browser, 1)
        close_button = QPushButton(self.t("btn_close"))
        close_button.setAccessibleName(self.t("btn_close"))
        close_button.setDefault(True)
        close_button.clicked.connect(dlg.accept)
        layout.addWidget(close_button)
        dlg.resize(720, 620)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    # ------------------------------------------------------------ subtitles
    # One caption per line: "[start --> end] text" while the timestamps are
    # shown, exactly the caption text on its own line while they are hidden.
    TIMESTAMP_LINE = re.compile(
        r"^\[([0-9]{1,2}:[0-9]{2}:[0-9]{2}[,.][0-9]{1,3}) --> "
        r"([0-9]{1,2}:[0-9]{2}:[0-9]{2}[,.][0-9]{1,3})\] ?(.*)$"
    )

    def _render_editor(self):
        parts = []
        for sub in self.subtitles:
            content = sub.content
            if not self.show_timestamps:
                # one line per caption: embedded line breaks (bilingual
                # captions) are folded into the line
                content = " / ".join(
                    line.strip() for line in content.splitlines() if line.strip()
                )
            if self.show_timestamps:
                parts.append(
                    "[%s --> %s] %s"
                    % (format_timestamp(sub.start), format_timestamp(sub.end), content)
                )
            else:
                parts.append(content)
        return "\n".join(parts)

    def populate_editor(self):
        """Show self.subtitles in the editor without stealing the caret."""
        text = self._render_editor()
        if self.editor.toPlainText() != text:
            position = self.editor.textCursor().position()
            scroll = self.editor.verticalScrollBar().value()
            self.editor.setPlainText(text)
            cursor = self.editor.textCursor()
            cursor.setPosition(min(position, len(text)))
            self.editor.setTextCursor(cursor)
            self.editor.verticalScrollBar().setValue(scroll)
        self.editor.setAccessibleDescription(
            self.t("acc_editor_d", count=len(self.subtitles))
        )

    def _editor_segments(self):
        """Parse the editor text into [{line, line_end, start, end, lines}]."""
        text = self.editor.toPlainText()
        segments = []
        current = None

        def finish(segment):
            lines = list(segment["lines"])
            while lines and not lines[-1].strip():
                lines.pop()
            segment["lines"] = lines or [""]
            segments.append(segment)

        if not self.show_timestamps:
            if not text.strip():
                return []
            for lineno, line in enumerate(text.split("\n")):
                segments.append(
                    {"line": lineno, "line_end": lineno,
                     "start": None, "end": None, "lines": [line]}
                )
            return segments

        for lineno, line in enumerate(text.split("\n")):
            match = self.TIMESTAMP_LINE.match(line)
            if match:
                if current is not None:
                    current["line_end"] = lineno - 1
                    finish(current)
                current = {
                    "line": lineno,
                    "line_end": lineno,
                    "start": match.group(1),
                    "end": match.group(2),
                    "lines": [match.group(3)],
                }
                continue
            if line.startswith("[") and "-->" in line:
                raise ValueError(
                    self.t("body_ts_invalid", row=lineno + 1, detail=line.strip()[:48])
                )
            if current is None:
                if not line.strip():
                    continue
                # A caption typed without a timestamp: it gets a time slot
                # after the previous one so the export still works.
                current = {
                    "line": lineno,
                    "line_end": lineno,
                    "start": None,
                    "end": None,
                    "lines": [line],
                }
            else:
                current["lines"].append(line)
                current["line_end"] = lineno
        if current is not None:
            finish(current)
        return segments

    def _segments_to_subtitles(self, segments):
        subs = []
        last_end = timedelta(0)
        for number, seg in enumerate(segments, start=1):
            lines = list(seg["lines"])
            while lines and not lines[-1].strip():
                lines.pop()
            content = "\n".join(lines)
            start = end = None
            if seg["start"] is not None:
                try:
                    start = parse_timestamp(seg["start"])
                    end = parse_timestamp(seg["end"])
                except ValueError as exc:
                    raise ValueError(
                        self.t("body_ts_invalid", row=seg["line"] + 1, detail=str(exc))
                    )
                if end <= start:
                    raise ValueError(self.t("body_ts_range", row=seg["line"] + 1))
            if start is None:
                # No timestamp (hidden mode, or a line typed by hand): keep
                # the timing that used to sit on this line, or give a new
                # two second slot after the last one.
                original = (
                    self.subtitles[number - 1]
                    if number - 1 < len(self.subtitles)
                    else None
                )
                if original is not None:
                    start, end = original.start, original.end
                else:
                    start = last_end
                    end = start + timedelta(seconds=2)
            last_end = max(last_end, end)
            subs.append(
                srt.Subtitle(index=number, start=start, end=end, content=content)
            )
        return subs

    def read_subtitles_from_editor(self, confirm=True):
        """Editor text -> subtitles.

        When the number of caption lines changed and ``confirm`` is set the
        user is asked first; None means the change was declined.
        """
        segments = self._editor_segments()
        if confirm and self.subtitles and len(segments) != len(self.subtitles):
            answer = QMessageBox.question(
                self,
                self.t("title_line_count"),
                self.t(
                    "body_line_count",
                    old=len(self.subtitles),
                    new=len(segments),
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return None
        return self._segments_to_subtitles(segments)

    def add_row(self):
        """Edit -> Add caption line (Ctrl+Shift+N)."""
        try:
            subs = self.read_subtitles_from_editor(confirm=False) or []
        except ValueError as exc:
            QMessageBox.warning(self, self.t("title_invalid"), str(exc))
            return
        start = subs[-1].end if subs else timedelta(0)
        subs.append(
            srt.Subtitle(
                index=len(subs) + 1, start=start, end=start + timedelta(seconds=2),
                content="",
            )
        )
        self.subtitles = subs
        self.populate_editor()
        cursor = self.editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus(Qt.FocusReason.OtherFocusReason)
        self.announce(self.t("msg_row_added", num=len(subs)))

    def delete_selected_rows(self):
        """Edit -> Delete caption lines (Ctrl+Shift+D): the selected lines."""
        if not self.editor.toPlainText().strip():
            self.announce(self.t("msg_no_rows"))
            return
        try:
            segments = self._editor_segments()
            subs = self._segments_to_subtitles(segments)
        except ValueError as exc:
            QMessageBox.warning(self, self.t("title_invalid"), str(exc))
            return
        cursor = self.editor.textCursor()
        first = self.editor.document().findBlock(cursor.selectionStart()).blockNumber()
        last = self.editor.document().findBlock(cursor.selectionEnd()).blockNumber()
        if not cursor.hasSelection():
            last = first
        kept = [
            (seg, sub)
            for seg, sub in zip(segments, subs)
            if not (seg["line"] <= last and seg["line_end"] >= first)
        ]
        removed = len(segments) - len(kept)
        if removed <= 0:
            self.announce(self.t("msg_no_rows"))
            return
        self.subtitles = [
            srt.Subtitle(index=i, start=sub.start, end=sub.end, content=sub.content)
            for i, (_seg, sub) in enumerate(kept, start=1)
        ]
        self.populate_editor()
        self.announce(self.t("msg_rows_deleted", count=removed))

    def import_srt(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.t("dlg_import_srt"),
            "",
            self.t("dlg_srt_filter"),
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                content = handle.read()
            parsed = list(srt.parse(content))
        except Exception as exc:
            QMessageBox.warning(
                self,
                self.t("title_import_failed"),
                self.t("body_import_failed", err=str(exc)),
            )
            return
        self.subtitles = trim_subtitles(parsed)
        self.populate_editor()
        self.announce(
            self.t("msg_import_done", count=len(self.subtitles), path=path),
            show_box=True,
        )

    def _plain_text_export(self, subtitles):
        """The text written for a .txt export (honours Show timestamps)."""
        lines = []
        for sub in subtitles:
            if self.show_timestamps:
                lines.append(
                    "[%s --> %s] %s"
                    % (
                        format_timestamp(sub.start),
                        format_timestamp(sub.end),
                        sub.content,
                    )
                )
            else:
                lines.append(sub.content)
        return "\n".join(lines) + "\n"

    def _write_caption_file(self, path, subtitles):
        """Write subtitles as .srt (timing always kept) or .txt."""
        if os.path.splitext(path)[1].lower() == ".txt":
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self._plain_text_export(subtitles))
        else:
            with open(path, "w", encoding="utf-8-sig") as handle:
                handle.write(srt.compose(trim_subtitles(subtitles)))

    def export_srt(self):
        try:
            subtitles = self.read_subtitles_from_editor()
        except ValueError as exc:
            QMessageBox.warning(self, self.t("title_invalid"), str(exc))
            return
        if subtitles is None:
            return
        if not subtitles:
            QMessageBox.warning(
                self,
                self.t("title_nothing_export"),
                self.t("body_nothing_export"),
            )
            return

        default_name = os.path.splitext(os.path.basename(self.video_path))[0] + "_captions.srt" if self.video_path else "captions.srt"
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.t("dlg_export_srt"),
            os.path.join(os.path.expanduser("~"), default_name),
            self.t("dlg_export_filter"),
        )
        if not path:
            return
        try:
            self._write_caption_file(path, subtitles)
        except Exception as exc:
            QMessageBox.warning(self, self.t("title_export_failed"), str(exc))
            return
        self.last_output_folder = os.path.dirname(path)
        self.announce(
            self.t("msg_export_done", count=len(subtitles), path=path),
            show_box=True,
        )

    def export_results(self):
        """File -> Export subtitles and video (Ctrl+E).

        The edited transcript is written to a subtitle file first; when a
        video is loaded the user can also burn the same captions into a copy
        of it.  Start and finish of the export are announced.
        """
        try:
            subtitles = self.read_subtitles_from_editor()
        except ValueError as exc:
            QMessageBox.warning(self, self.t("title_invalid"), str(exc))
            return
        if subtitles is None:
            return
        if not subtitles:
            QMessageBox.warning(
                self,
                self.t("title_nothing_export"),
                self.t("body_nothing_export"),
            )
            return
        self.announce(self.t("msg_export_start"))
        default_name = (
            os.path.splitext(os.path.basename(self.video_path))[0] + "_captions.srt"
            if self.video_path
            else "captions.srt"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.t("dlg_export_srt"),
            os.path.join(os.path.expanduser("~"), default_name),
            self.t("dlg_export_filter"),
        )
        if not path:
            return
        try:
            self._write_caption_file(path, subtitles)
        except Exception as exc:
            QMessageBox.warning(self, self.t("title_export_failed"), str(exc))
            return
        self.last_output_folder = os.path.dirname(path)
        subtitles_done = self.t("msg_export_done", count=len(subtitles), path=path)
        if not self.video_path:
            self.announce(subtitles_done, show_box=True)
            return
        answer = QMessageBox.question(
            self,
            self.t("msg_export_video_title"),
            self.t("msg_export_video", path=path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            self.announce(subtitles_done, show_box=True)
            return
        default_video = (
            os.path.splitext(os.path.basename(self.video_path))[0] + "_subtitled.mp4"
        )
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            self.t("dlg_save_video"),
            os.path.join(os.path.dirname(self.video_path), default_video),
            self.t("dlg_mp4_filter"),
        )
        if not output_path:
            self.announce(subtitles_done, show_box=True)
            return
        self.last_output_folder = os.path.dirname(output_path)
        thread = RenderThread(
            self.video_path,
            subtitles,
            output_path,
            self.temp_dir,
            font_path=FONT_PATH,
            lang=self.current_lang,
        )
        if self._start_thread(thread, self._on_render_done):
            self.announce(subtitles_done)
            self.announce(self.t("msg_render_start"))

    def open_output_folder(self):
        folder = getattr(self, "last_output_folder", None)
        if not folder or not os.path.isdir(folder):
            folder = os.path.dirname(self.video_path) if self.video_path else os.path.expanduser("~")
        if not os.path.isdir(folder):
            folder = os.path.expanduser("~")
        os.startfile(folder)
        self.announce(self.t("msg_folder_opened", path=folder))

    def _require_video(self):
        if not self.video_path:
            QMessageBox.warning(
                self,
                self.t("title_no_video"),
                self.t("body_no_video"),
            )
            return False
        return True

    def closeEvent(self, event):
        if getattr(self, "_exit_started", False):
            event.accept()
            return
        # Exit confirmation: the user can still cancel before the goodbye
        # panel, the farewell chime and the final shutdown.
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(self.t("title_exit_confirm"))
        box.setText(self.t("body_exit_confirm", text=vt_setup.FAREWELL_TEXT))
        yes = box.addButton(self.t("btn_exit_yes"), QMessageBox.ButtonRole.AcceptRole)
        no = box.addButton(self.t("btn_exit_no"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(no)
        box.exec()
        if box.clickedButton() is not yes:
            self.announce(self.t("msg_exit_cancelled"))
            event.ignore()
            return

        if self.worker_thread is not None and self.worker_thread.isRunning():
            self.worker_thread.requestInterruption()
            self.worker_thread.wait(4000)
        self.worker_thread = None

        app = QApplication.instance()
        started = False
        if app is not None:
            try:
                started = vt_setup.show_exit_screen(app, app.quit)
            except Exception:
                started = False
        if started:
            self._exit_started = True
            self.hide()
            event.ignore()
        else:
            event.accept()


def _crash_log_path():
    """Fallback crash file inside the app data folder (never the program folder)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "Accessible Video Transcriber")
    try:
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "crash.log")
    except OSError:
        return os.path.join(tempfile.gettempdir(), "crash.log")


def _install_crash_log():
    import datetime as _dt

    def _hook(exc_type, exc_value, exc_tb):
        crash_path = _crash_log_path()
        try:
            with open(crash_path, "a", encoding="utf-8") as fh:
                fh.write("\n=== {} ===\n".format(_dt.datetime.now()))
                fh.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        except Exception:
            pass
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance() or QApplication([])
            QMessageBox.critical(
                None,
                "Accessible Video Transcriber error",
                "A problem occurred. Details were saved to:\n{}\n\n{}".format(
                    crash_path, exc_value
                ),
            )
        except Exception:
            pass
        sys.exit(1)

    sys.excepthook = _hook


def _run_frozen_self_test():
    lines = []
    ok = True

    def check(label, fn):
        nonlocal ok
        try:
            fn()
            lines.append("PASS  " + label)
        except Exception as exc:
            ok = False
            lines.append("FAIL  {}: {!r}".format(label, exc))

    def _faster_whisper():
        from faster_whisper import WhisperModel  # noqa: F401

    def _moviepy():
        from moviepy import VideoFileClip  # noqa: F401

    def _ffmpeg():
        import vt_install

        exe = vt_install.ffmpeg_exe()
        here = vt_install.app_dir()
        lines.append("      ffmpeg exe: " + str(exe))
        lines.append("      ffmpeg exists: " + str(bool(exe) and os.path.exists(exe)))
        if not (exe and os.path.exists(exe)):
            raise RuntimeError("ffmpeg could not be located")
        # A frozen build must use the standalone copy that travels beside the
        # executable, never the one unpacked into the temporary folder, which
        # disappears as soon as the program exits.
        resolved_here = os.path.dirname(os.path.abspath(exe)) == here
        lines.append("      ffmpeg from program folder: " + str(resolved_here))
        if getattr(sys, "frozen", False) and not resolved_here:
            raise RuntimeError("ffmpeg was not resolved from the program folder: %r" % exe)

    def _av():
        import av  # noqa: F401

    def _ctranslate2():
        import ctranslate2  # noqa: F401

    def _srt():
        import srt  # noqa: F401

    def _translator():
        from deep_translator import GoogleTranslator  # noqa: F401

    def _numpy():
        import numpy

        lines.append("      numpy " + numpy.__version__)

    def _qt():
        import os as _os

        if "QT_QPA_PLATFORM" not in _os.environ:
            _os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PyQt6.QtWidgets import QApplication

        app = QApplication([])
        lines.append("      QApplication offscreen OK (style: " + str(app.style().objectName()) + ")")

    def _model():
        from huggingface_hub import try_to_load_from_cache  # noqa: F401

    def _bundled_model():
        import vt_bootstrap
        import vt_install

        folder = vt_install.model_dir("base")
        lines.append("      model folder: " + (folder or "(none)"))
        if not folder:
            raise RuntimeError("the recognition model is not bundled with the program")
        names = set(os.listdir(folder))
        missing = [n for n in ("config.json", "model.bin", "tokenizer.json") if n not in names]
        if missing:
            raise RuntimeError("the bundled model is incomplete: missing %r" % missing)
        total = sum(os.path.getsize(os.path.join(folder, n)) for n in names)
        lines.append("      model size: %.1f MB" % (total / (1024 * 1024)))

        # Prove the folder is self-contained: make every hub download explode,
        # then open the model anyway.  A path is handed to faster-whisper, so
        # no cache and no network may be involved.
        import huggingface_hub

        def _blocked(*args, **kwargs):
            raise RuntimeError("snapshot_download was called: the model is not self-contained")

        real_hub = huggingface_hub.snapshot_download
        huggingface_hub.snapshot_download = _blocked
        try:
            import faster_whisper.utils as fwu

            real_fw = getattr(fwu, "snapshot_download", None)
            if real_fw is not None:
                fwu.snapshot_download = _blocked
            try:
                from faster_whisper import WhisperModel

                opened = WhisperModel(folder, device="cpu", compute_type="int8")
                # ... and actually run it, on real speech, with every download
                # path still poisoned.  Proving the model opens is not the same
                # as proving transcription works on the user's machine.
                speech = vt_bootstrap.resource_path("resources", "selftest-speech.wav")
                if not os.path.isfile(speech):
                    raise RuntimeError("the self test speech sample is missing: %r" % speech)
                segments, _info = opened.transcribe(
                    speech, language="en", beam_size=5, vad_filter=False
                )
                heard = " ".join((s.text or "").strip() for s in segments).strip()
                lines.append("      transcribed: " + repr(heard))
                if "welcome" not in heard.lower():
                    raise RuntimeError(
                        "offline transcription returned the wrong text: %r" % heard
                    )
            finally:
                if real_fw is not None:
                    fwu.snapshot_download = real_fw
        finally:
            huggingface_hub.snapshot_download = real_hub
        lines.append("      transcribed offline (no download path touched)")

    def _video_tools():
        import vt_install

        report = vt_install.check_video_tools()
        for key in ("ffmpeg", "pillow", "font", "model"):
            lines.append("      %-8s %s" % (key + ":", report[key]))
        if not report["ok"]:
            raise RuntimeError("the video tool chain is incomplete: %r" % report)
        if getattr(sys, "frozen", False) and report["model"] != "bundled":
            raise RuntimeError("the recognition model is not bundled: %r" % report["model"])

    def _install_helpers():
        import shutil

        import vt_install

        vi = vt_install
        sandbox = os.path.join(tempfile.gettempdir(), "VT_selftest_install")
        shutil.rmtree(sandbox, ignore_errors=True)
        os.makedirs(sandbox, exist_ok=True)
        fake = os.path.join(sandbox, "AccessibleVideoTranscriber.exe")
        # A real executable, not a stub: WScript.Shell reads the icon out of the
        # target while saving a .lnk and refuses to save when it cannot.
        shutil.copyfile(sys.executable, fake)
        # Never touch the real desktop or Start menu during a self test.
        vi.start_menu_link = lambda uninstall_exe="": os.path.join(sandbox, "sm", "Accessible Video Transcriber.lnk")
        vi.start_menu_uninstall_link = lambda: os.path.join(sandbox, "sm", "Uninstall.lnk")
        vi.desktop_link = lambda: os.path.join(sandbox, "desktop", "Accessible Video Transcriber.lnk")
        vi.desktop_dir = lambda: os.path.join(sandbox, "desktop")
        links = vi.create_shortcuts(fake, "", start_menu=True, desktop=True)
        made = [p for p in links if str(p).endswith(".lnk")]
        lines.append("      shortcuts: " + ", ".join(os.path.basename(p) for p in links))
        problems = [p for p in links if not str(p).endswith(".lnk")]
        if problems or len(made) != 2:
            raise RuntimeError("expected a Start menu and a desktop shortcut: %r" % (links,))
        desktop_only = [
            p for p in vi.create_shortcuts(fake, "", start_menu=False, desktop=True) if str(p).endswith(".lnk")
        ]
        if any("sm" in str(path) for path in desktop_only) or len(desktop_only) != 1:
            raise RuntimeError("the Start menu shortcut was created although it was not wanted")
        shutil.rmtree(sandbox, ignore_errors=True)

    def _render():
        import shutil

        out = os.path.join(tempfile.gettempdir(), "VT_selftest.mp4")
        if os.path.exists(out):
            os.remove(out)
        from moviepy import AudioClip, ColorClip, CompositeVideoClip, TextClip

        clip = ColorClip(size=(320, 240), color=(40, 60, 80), duration=1).with_fps(10)
        txt = (
            TextClip(
                text="Test",
                font=FONT_PATH or None,
                font_size=24,
                color="white",
                duration=1,
            )
            .with_position(("center", "center"))
        )
        comp = CompositeVideoClip([clip, txt])
        audio = AudioClip(lambda t: 0.05, duration=1).with_fps(22050)
        comp = comp.with_audio(audio)
        comp.write_videofile(
            out,
            codec="libx264",
            audio_codec="aac",
            fps=10,
            preset="ultrafast",
            logger=None,
        )
        lines.append("      wrote render test video: " + str(os.path.exists(out) and os.path.getsize(out) > 1000))
        if os.path.exists(out):
            os.remove(out)

    check("faster_whisper", _faster_whisper)
    check("moviepy", _moviepy)
    check("imageio_ffmpeg", _ffmpeg)
    check("bundled speech model", _bundled_model)
    check("av", _av)
    check("ctranslate2", _ctranslate2)
    check("srt", _srt)
    check("deep_translator", _translator)
    check("numpy", _numpy)
    check("PyQt6/QApplication", _qt)
    check("huggingface_hub", _model)
    check("video tool chain", _video_tools)
    check("install helpers", _install_helpers)
    check("moviepy render (ffmpeg burn)", _render)

    result_path = sys.argv[2] if len(sys.argv) > 2 else ""
    try:
        with open(result_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\nRESULT: " + ("OK" if ok else "FAIL") + "\n")
    except Exception:
        pass
    sys.exit(0 if ok else 1)


def _bootstrap_runtime():
    """Install the log streams and the exception hooks before Qt starts.

    ``vt_bootstrap`` replaces the ``None`` stdout/stderr handles a windowed
    PyInstaller build leaves behind, so background workers (tqdm, huggingface)
    cannot die with ``AttributeError: 'NoneType' object has no attribute
    'write'``.  When it cannot be imported the small temp file based hook is
    installed instead so crashes are still recorded.
    """
    try:
        import vt_bootstrap

        vt_bootstrap.install()
        try:
            import vt_migrate

            vt_migrate.migrate_once()
        except Exception:
            logging.getLogger("vidtrans").exception("settings migration failed")
        return True
    except Exception:
        return False


def main():
    # Before any mode runs (window, --selftest, --e2e): temp files and model
    # downloads must land in the per-user data folder, never next to the
    # program and never in the system temp folder.
    try:
        import vt_bootstrap

        vt_bootstrap.setup_runtime_dirs()
    except Exception:  # noqa: BLE001 - the program still works with system temp
        pass

    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        # available in the source tree too, so the tool chain can be checked
        # without waiting for a ten minute PyInstaller build
        _run_frozen_self_test()

    if len(sys.argv) >= 3 and sys.argv[1] == "--e2e":
        # Headless end-to-end run of the real pipeline (used to verify the
        # installed program): AccessibleVideoTranscriber.exe --e2e video.mp4 [en|ar]
        import vt_e2e

        sys.exit(vt_e2e.run(sys.argv[2:]))

    force_welcome = "--welcome" in sys.argv[1:]

    if not _bootstrap_runtime():
        try:
            _install_crash_log()
        except Exception:
            pass

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("Accessible Video Transcriber")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 11))
    try:
        import vt_bootstrap as _vt_bootstrap

        # The drawn "I" icon is used for the window, the taskbar button and
        # every message box the program owns.
        app.setWindowIcon(
            QIcon(_vt_bootstrap.resource_path("resources", "app-icon.ico"))
        )
    except Exception:  # noqa: BLE001 - a missing icon must not stop the app
        pass

    # First-run greeting: the exact welcome sentence is announced and focus
    # lands on the Continue button.  It is shown once per installation; pass
    # --welcome to see it again.  No licence is presented here -- that belongs
    # to the installer, which asks for it once.
    language = vt_setup.show_welcome_screen(app, force=force_welcome)
    # Belt and braces: if the greeting could not be built the boot splash was
    # never told to close, so make sure it is gone either way.
    vt_setup.close_boot_splash()

    window = MainWindow(language if language in ("en", "ar") else None)
    window.setWindowIcon(app.windowIcon())
    window.show()
    window.raise_()
    window.activateWindow()

    def _land_on_first_action():
        # Land on the first real control so a screen reader user arrives on
        # something that can be used, not on an empty window.
        target = getattr(window, "open_button", None)
        if target is not None and target.isEnabled():
            target.setFocus(Qt.FocusReason.OtherFocusReason)
        else:
            window.setFocus(Qt.FocusReason.OtherFocusReason)

    from PyQt6.QtCore import QTimer

    QTimer.singleShot(0, _land_on_first_action)

    # The automatic update check waits a few seconds so it never slows the
    # program down or interrupts the screen reader while the window opens.
    import help_menu as help_menu_module

    QTimer.singleShot(5000, lambda: help_menu_module.check_on_startup(window))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()