# Getting started

Accessible Media Transcriber turns the speech in audio or video into editable captions, translates them, and can burn the result back into a copy of the video. Everything can be driven from the keyboard.

## First run
The optional welcome screen closes within three seconds. Choose Continue to skip the wait, or disable it in Preferences → Accessibility. The farewell message has its own saved checkbox.

## The five groups
The main window reads top to bottom in five groups: 1 Choose an audio or video file, 2 Task and languages, 3 Run, 4 Progress, 5 Results. Move between groups with the Tab key and between the controls inside a group with Tab or the arrow keys.

## A typical session
Open an audio or video recording, pick a task and a language, press the Start button (F5), wait for the progress bar, correct anything in the transcript, then export the subtitles or render the subtitled video. When the work finishes or the program exits, it says so and plays a short sound; both can be switched off in the Accessibility tab in Preferences.


## Transcribe a group of recordings
Choose Tools → Batch transcription, or press Ctrl+B. Add audio or video recordings, choose an output folder and start the queue. The current transcription engine and model are used for each file. Every successful file produces UTF-8 text and timed SRT subtitles in a new batch folder. A report records failures, and later files continue. Stop queue prevents remaining files from starting. Closing the batch window while a task runs requests cancellation and keeps the worker alive until it finishes. Existing output files are not overwritten.
