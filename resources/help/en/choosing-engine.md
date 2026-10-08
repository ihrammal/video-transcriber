# Choosing an engine

The engine list in group 2 decides who turns the speech into text.

## The choices
Automatic uses your saved choice and falls back when it fails. Local Whisper runs a model on this computer: free, offline, and slower on long videos. OpenAI API, Groq API and Google Gemini API send the audio to a cloud service; they need an API key and are fast and accurate.

## Automatic
Automatic is the safe default. It remembers the engine that worked last time and tries the next one when the chosen one cannot run, so a lost key or a missing model does not stop you.

## Models
The Models menu downloads the small local models: tiny is the fastest, base is balanced, and small is the most accurate of the three. Model status (Control plus 0) reports what is on disk and how much space it takes.
