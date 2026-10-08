# Timestamps

## What a timestamp is
Every caption carries a start and an end time, for example 00:00:04,500 to 00:00:07,200. They decide when a line appears and disappears in the rendered video, and they are always kept in .srt files.

## Show timestamps
The Show timestamps check box in the results group, and the Accessibility menu item with the same name (Control plus Shift plus T), decide how the transcript is written. With timestamps on, each segment reads [00:00:04,500 --> 00:00:07,200] text; with them off, each line is just the text. The choice is remembered for the next run and announced when you change it.

## What it does not change
Switching timestamps on or off never changes the real timing, only what plain text exports and the screen reader see. .srt files always contain the full timing, no matter how the check box is set.
