"""PyInstaller hook: pin the external tools the video pipeline needs.

``imageio_ffmpeg`` ships the ffmpeg executable as a plain data file inside its
package.  Nothing imports it, so a normal analysis leaves it out and every
"produce the output video" action (audio extraction, muxing, burning the
captions) dies with "ffmpeg binary not found" on the user's machine.  The
contrib hook covers this today; this project hook keeps it pinned even if the
contrib set is regenerated, because without ffmpeg the application is useless.
"""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("imageio_ffmpeg", include_py_files=False)
hiddenimports = ["imageio_ffmpeg.binaries"]
