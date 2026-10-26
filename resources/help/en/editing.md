# Editing the transcript

## The editor
The transcript is a plain text area in group 5: one segment per line, and Tab moves out of it, so keyboard users are never trapped. With Show timestamps on, a segment starts with its timing, and any following line without a timing belongs to the previous segment.

## Changing text
Type directly. Changes are kept: when you translate, export or render, the program reads the editor first, so what you see is what is used.

## Adding and removing
Edit then Add a line (Control plus Shift plus N) appends a new empty segment with a two second slot after the last one. Edit then Delete the selected lines (Control plus Shift plus D) removes every segment the cursor is on; deleting the whole transcript asks for confirmation first.

## Mistakes
A line that looks like a timing but is not valid is reported with its line number instead of being silently dropped, and an end time that is not after the start time is refused as well.


## Recovery after restarting
Unfinished transcript edits are saved locally after a short pause and when closing. On the next launch, choose whether to restore the unfinished transcript. Recovery keeps the source path, text and caption timings, and never stores API keys. Exporting clears the recovery copy. General preferences can disable recovery and remove its saved copy. Before replacing an unexported transcript, the program asks for confirmation. Switching the interface language keeps your edits.
