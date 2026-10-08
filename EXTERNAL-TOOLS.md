# External tools

Everything the program needs besides the Python packages listed in
`requirements.txt`. The first three are needed to run the program. The last
one is only needed to build the installer.

## Python 3.11 to 3.14 (64 bit, Windows)

Download from https://www.python.org/downloads/ and tick "Add python.exe to
PATH" during setup. The program was built and tested on Python 3.14.7.

## ffmpeg

ffmpeg does the real media work: it pulls the sound out of a video, and it
writes the captions back into the video. The program looks for it in this
order:

1. `VT_FFMPEG` environment variable, if you set one.
2. `ffmpeg.exe` in the program folder or in a `bin` folder next to it.
3. A copy found on `PATH` or in a usual Windows install folder
   (`C:\ffmpeg\bin`, `C:\Program Files\ffmpeg\bin`, the WinGet links folder).
4. The copy that ships inside the `imageio-ffmpeg` package, which is
   installed automatically with `pip install -r requirements.txt`.

So on a normal machine you do not have to install anything by hand: the
pip fallback already provides a working ffmpeg. Download a standalone build
from https://ffmpeg.org/download.html only if you prefer the full Windows
build with ffprobe.

## ffprobe (optional)

ffprobe reports how long a video is and what is inside it. It is searched
in the same folders as ffmpeg. If it is missing the program carries on with
ffmpeg alone, so ffprobe is never a hard requirement.

## Inno Setup 6 (only for building the installer)

The installer is a single `.exe` produced by Inno Setup. Install it from
https://jrsoftware.org/isinfo.php, then run `build.bat` or
`python build.py`. The build script looks for `ISCC.exe` in the usual
install locations, on `PATH`, or at the path stored in the `ISCC`
environment variable. You need it only when you make an installer, never
when you run the program.

## Whisper model (downloaded automatically)

The free local speech engine uses the faster-whisper "base" model, about
141 MB. It is downloaded from Hugging Face the first time you transcribe,
and is then reused from the `models` folder or from the Hugging Face cache.
No account and no API key are needed for it. An internet connection is
required only for that first download.
