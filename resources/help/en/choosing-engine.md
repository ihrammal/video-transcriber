# Choosing an engine

The engine list in group 2 decides who turns the speech into text.

## The choices
Automatic uses your saved choice and falls back when it fails. Local Whisper runs a model on this computer: free, offline, and slower on long videos. OpenAI API, Groq API and Google Gemini API send the audio to a cloud service; they need an API key and are fast and accurate.

## Automatic
Automatic is the safe default. It remembers the engine that worked last time and tries the next one when the chosen one cannot run, so a lost key or a missing model does not stop you.

## Models
The Models menu downloads Tiny, Base, Small, Medium, Large v3 and Turbo. Larger models generally use more memory; compare their results on your recordings. Choose the active model in Preferences. Model status (Control plus 0) reports what is on disk and how much space it takes.


Version 1.3.1 offers Tiny, Base and Small in Custom installation, or you can omit the offline model for API-only use. Express installs Base. Choose Local in Preferences to transcribe without an API key or internet connection after installing a model.


## Offline transcription and online translation
Offline Whisper transcribes recordings on this computer after the chosen model is installed. It does not provide offline translation. Google Translate sends transcript text over the internet and needs no API key; OpenAI, Groq and Gemini use their respective API keys. The Processing engine choice shows both uses clearly.
