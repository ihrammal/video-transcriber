# Third-party components and their licences

This program is not alone: it is built on top of other people's work. Every
item below keeps its own licence, and its own licence text travels with it.
The program's own terms are in `LICENSE` (source code) and in
`resources/agreement_en.txt` / `resources/agreement_ar.txt` (the end user
agreement shown by the installer).

Nothing in this file changes those terms. Where two licences could apply to
the same file, the stricter one wins.

## Libraries the program imports directly

The versions are the ones pinned in `requirements.txt`.

- PyQt6 6.11.0, GPL-3.0-only. The window, the controls and the accessibility
  layer. See the note about GPL below.
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
- The faster-whisper base model, `Systran/faster-whisper-base` from Hugging
  Face, MIT. About 141 MB, downloaded on first run or shipped in the
  installer. It is not committed to this repository either.
- Inno Setup 6, the Inno Setup licence, free to use. Used only to compile
  the installer, never at runtime.

## Note about Qt

PyQt6 is published under the GNU GPL version 3. This program links to it, so
a compiled `.exe` that you hand to other people carries GPL obligations for
the Qt parts: you must let those people have the source of the GPL covered
parts and pass the same freedoms on. Buying a commercial PyQt6 licence from
Riverbank Computing removes that obligation. The Qt modules that ship inside
the exe keep their own licence text in `PyQt6_Qt6-*.dist-info`.

## Note about the program's own licence

`LICENSE` holds the PolyForm Noncommercial License 1.0.0, which lets anyone
read, change and share this source code as long as the use stays
non-commercial and the copyright notice travels with it. The installer's
`License.txt` is the separate end user agreement for the built program, and
it is also non-commercial.

If you need terms that allow commercial use, ask the author: the same author
can relicense under different terms.
