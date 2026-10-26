# API keys

Cloud engines need a key from their provider. Keys belong in the preferences, never in a document.

## Where to put them
Open Settings → Preferences (Control plus comma), then API keys. Select the provider to edit its key and model. The key is saved in Windows Credential Manager, not in a plain file, and remains hidden unless you choose Show key.

## A missing key
When the chosen engine has no key, the program names the provider that is missing and offers to open the preferences for you. Nothing is sent anywhere until you press Start.

## Rotating a key
Paste the new key into the same field and save. Removing a key means the engine falls back to another one, or asks you to choose.
