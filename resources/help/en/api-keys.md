# API keys

Cloud engines need a key from their provider. Keys belong in the preferences, never in a document.

## Where to put them
Open Settings then Speech and Translation Settings (Control plus comma). Every provider has its own field. The key is saved in the Windows credential manager, not in a plain file, and it is never shown again after saving.

## A missing key
When the chosen engine has no key, the program names the provider that is missing and offers to open the preferences for you. Nothing is sent anywhere until you press Start.

## Rotating a key
Paste the new key into the same field and save. Removing a key means the engine falls back to another one, or asks you to choose.
