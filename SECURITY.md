# Security policy

## Reporting a problem

Please do not write about security problems in a public issue, a public pull
request or a social media post. Send an email to:

    iman.rammal@gmail.com

Put the words "Vid-Trans security" in the subject line so it is noticed
quickly.

Include what you did, what you expected, what happened, and which version you
are using (F12 opens About with the version). If you have a log file, attach
it: Help, then Open Log Folder, or Ctrl+Shift+V.

You will get an answer that says the report was received, and then an update
when it is fixed. Please keep the details private until a fixed version is
released, and then write about it if you wish.

There is no bug bounty. Credit is offered in the release notes if you want it.

## What matters most

- Any place where an API key could end up in a file, a log, a crash dump, a
  screen or a network request that is not the provider's own.
- Anything in `vt_secrets.py` or `vt_prefs.py`, where keys are stored in the
  Windows Credential Manager and stripped from `prefs.json`.
- Anything in `vt_api.py` or `vt_workers.py`, which send caption text and
  audio to OpenAI, Groq or Google Gemini.
- The installer and the build, in `installer\` and `build.py`, since they run
  with the user's own rights.
- Handling of video paths, temporary files and the log file in
  `vt_bootstrap.py`.

## How keys are handled today

Keys live in the Windows Credential Manager, under the target name
`VidTrans/`. They are read only when a request is made, shown masked in the
preferences dialog, never written into `prefs.json`, and never written into
the log. Older plain text copies found in an old `prefs.json` are moved into
the credential store on first load and then removed from the file.

If you find a path where a key can leak, that is a security problem, whatever
the file or the screen.

## Supported versions

Security fixes go into the newest release. Older releases may not be patched,
so please upgrade before reporting, when you can.

## Scope

This is a Windows desktop program run by the person who installed it. Reports
about a user harming themselves with their own machine, or about the third
party services (OpenAI, Groq, Google Gemini, the free translation service,
Hugging Face) are outside what this project can fix, but you are still
welcome to write.
