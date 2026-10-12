# Third-party components and their licences

This program is not alone: it is built on top of other people's work. Every
item below keeps its own licence, and its own licence text travels with it.
The program's own terms are in `LICENSE` (source code) and in
`resources/agreement_en.txt` / `resources/agreement_ar.txt` (the end user
agreement shown by the installer).

Third-party components retain their independent licence rights. The application
agreement does not restrict rights granted by those component licences.

## Libraries the program imports directly

The versions are the ones pinned in `requirements.txt`.

- PySide6 and Shiboken6 6.11.2, LGPL-3.0. The window, controls and
  accessibility layer. Qt libraries retain their individual licences.
- faster-whisper 1.2.1, MIT. The offline speech recognition.
- ctranslate2 4.8.2, MIT. The inference engine faster-whisper runs on.
- av 18.1.0, BSD-3-Clause. Video and audio reading.
- srt 3.5.3, MIT. Reading and writing `.srt` caption files.
- deep-translator 1.11.4, MIT. The free online translation engine.
- requests 2.34.2, Apache-2.0. Talking to the OpenAI, Groq and Gemini APIs.
- moviepy 2.2.1, MIT. Extracting audio and burning captions into video.
- numpy 2.5.3, BSD-3-Clause and the other licences listed in its own
  metadata. Array maths behind the render path.
- imageio-ffmpeg 0.6.0, BSD-2-Clause. Fallback ffmpeg binary.
- proglog 0.1.12, MIT. The progress bar shown while rendering.
- huggingface-hub 1.32.0, Apache-2.0. Downloading and caching the model.
- Pillow 11.3.0, MIT-CMU. Caption font and icon work.
- pyinstaller 6.22.3, GPL-2.0-or-later with a linking exception that allows
  building closed programs. Used only to produce the exe.
- pytest 9.1.1, MIT. The test suite. Used only during development.

## Libraries installed alongside them

These arrive through the packages above and are also shipped inside the exe.
Their full texts are in the matching `*.dist-info` folders that the build
copies next to the program.

- onnxruntime 1.30.0, MIT
- tokenizers 0.23.2, Apache-2.0
- protobuf 7.36.2, BSD-3-Clause
- huggingface-hub dependencies: certifi (MPL-2.0), charset-normalizer (MIT),
  fsspec (BSD-3-Clause), idna (BSD-3-Clause), tqdm (MPL-2.0 and MIT),
  urllib3 (MIT), hf-xet (Apache-2.0)
- imageio 2.37.4, BSD-2-Clause, and decorator 5.3.1, BSD-2-Clause
- pefile 2024.8.26, MIT, pywin32-ctypes 0.2.3, BSD-3-Clause, and altgraph
  0.17.5, MIT: needed by PyInstaller while building
- packaging 26.3, Apache-2.0 or BSD-2-Clause, and pluggy 1.6.0, MIT: needed
  by pytest

Any library not named here is covered by the licence recorded in its own
`*.dist-info/METADATA` file inside the installed environment.

## Media tools that are not Python packages

- ffmpeg. Audio extraction and caption burn-in. The standalone build comes
  from https://ffmpeg.org and is licensed under the GNU LGPL, or the GNU GPL
  when it is built with GPL components. It is placed in `bin\ffmpeg.exe` and
  is not committed to this repository. When no standalone copy is present the
  program falls back to the ffmpeg binary inside `imageio-ffmpeg`.
- ffprobe. Optional, same project and same licence as ffmpeg.
- The multilingual faster-whisper Tiny, Base and Small models from
  `Systran/faster-whisper-{tiny,base,small}` on Hugging Face, MIT. All three
  are shipped in the installer for offline transcription. It is not committed to this repository either.
- Inno Setup 6, the Inno Setup licence, free to use. Used only to compile
  the installer, never at runtime.

## Note about Qt

The release uses the LGPL community distribution of PySide6 6.11.2 and Qt
6.11.2 as dynamically loaded libraries. Their DLLs remain separate in
`_internal/PySide6` and can be replaced by compatible modified versions.
Recipients may modify these components and reverse engineer the application
for debugging modifications to them, as permitted by the LGPL. The app's
noncommercial terms do not override these rights.

Full LGPL v3 and GPL v3 texts are installed under `resources/licenses`.
Corresponding unmodified source is available from:
- PySide6/Shiboken6: https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/
- Qt: https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/
- Licensing documentation: https://doc.qt.io/qtforpython-6/licenses.html

## Note about the program's own licence

`LICENSE` holds the PolyForm Noncommercial License 1.0.0, which lets anyone
read, change and share this source code as long as the use stays
non-commercial and the copyright notice travels with it. The installer's
`License.txt` is the separate end user agreement for the built program, and
it is also non-commercial.

If you need terms that allow commercial use, ask the author: the same author
can relicense under different terms.
