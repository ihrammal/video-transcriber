"""vt_workers.py -- background tasks.

Everything heavy (audio extraction, speech recognition, translation, video
rendering) runs in a QThread so the window never freezes.

Fixes contained here compared with the first release:

* Audio extraction now goes straight through the bundled ffmpeg binary instead
  of moviepy, which gives us a reliable "this video has no audio track" error
  instead of a bare AttributeError, plus real progress reporting.
* The recogniser never touches a ``None`` stream: ``log_progress`` is disabled
  and the module-level bootstrap has already replaced ``sys.stderr``.
* The Whisper model is loaded from the local cache when it is available, so a
  machine without internet keeps working; only a genuine first run downloads.
* Results are validated: an empty transcription is reported as such instead of
  silently showing an empty table.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from datetime import timedelta

import numpy as np
import srt

from PyQt6.QtCore import QThread, pyqtSignal

from vt_i18n import tr

log = logging.getLogger("vidtrans.workers")

_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


class NoAudioTrack(Exception):
    """Raised when the selected video does not contain an audio stream."""


class WorkerError(Exception):
    """Raised with a message that is already translated for the user."""


def _ffmpeg_exe() -> str:
    """ffmpeg next to the program first, imageio's copy as the fallback."""
    try:
        import vt_install

        found = vt_install.ffmpeg_exe()
        if found and os.path.exists(found):
            return found
    except Exception:  # noqa: BLE001 - fall through to the bundled copy
        pass
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _ffprobe_exe() -> str:
    """ffprobe from PATH or next to the bundled ffmpeg, else ''."""
    try:
        import vt_install

        found = vt_install.ffprobe_exe()
        if found:
            return found
    except Exception:
        pass
    found = shutil.which("ffprobe")
    if found:
        return found
    try:
        exe = _ffmpeg_exe()
    except Exception:
        return ""
    if exe:
        sibling = os.path.join(os.path.dirname(exe), "ffprobe.exe")
        if os.path.exists(sibling):
            return sibling
    return ""


def _probe_with_ffprobe(exe: str, path: str):
    """``(has_audio, duration, text)`` from ffprobe's JSON output."""
    proc = subprocess.run(
        [
            exe,
            "-v", "error",
            "-show_entries", "format=duration:stream=codec_type",
            "-of", "json",
            path,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        creationflags=_CREATE_NO_WINDOW,
    )
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 or not out:
        raise RuntimeError(((proc.stderr or "").strip() or "ffprobe exit %s" % proc.returncode))
    data = json.loads(out)
    streams = data.get("streams") or []
    duration = float((data.get("format") or {}).get("duration") or 0.0)
    if not streams or duration <= 0:
        raise RuntimeError("ffprobe reported no usable streams")
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    return has_audio, duration, out


def _run_ffmpeg(args, timeout=None):
    return subprocess.run(
        [_ffmpeg_exe()] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=_CREATE_NO_WINDOW,
    )


def probe_video(path: str):
    """Return ``(has_audio, duration_seconds, probe_output_text)``.

    A PATH (or bundled) ffprobe is used first because it answers with JSON; the
    bundled ffmpeg always remains the fallback, so a machine without ffprobe
    behaves exactly like one that has it.
    """
    probe = _ffprobe_exe()
    if probe:
        try:
            return _probe_with_ffprobe(probe, path)
        except Exception as exc:  # noqa: BLE001 - the ffmpeg fallback below is authoritative
            log.debug("ffprobe failed for %s (%s); falling back to ffmpeg", path, exc)
    try:
        proc = _run_ffmpeg(["-hide_banner", "-i", path], timeout=60)
    except FileNotFoundError as exc:
        raise WorkerError("ffmpeg is missing: %s" % exc) from exc
    except subprocess.TimeoutExpired:
        return False, 0.0, "timeout while probing the file"
    text = (proc.stderr or "") + (proc.stdout or "")
    # ffmpeg may print a stream id, an optional hexadecimal stream label and
    # language metadata before the stream type, for example:
    # ``Stream #0:1[0x2](eng): Audio: aac``.
    has_audio = re.search(
        r"Stream\s+#\d+:\d+(?:\[[^\]]+\])?(?:\([^)]*\))?.*:\s*Audio:",
        text,
        re.IGNORECASE,
    ) is not None
    duration = 0.0
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if match:
        duration = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))
    if not re.search(r"Duration:", text):
        # ffmpeg could not even parse the container.
        first_error = ""
        for line in text.splitlines():
            if "error" in line.lower() or "invalid" in line.lower() or "not found" in line.lower():
                first_error = line.strip()
                break
        raise WorkerError(first_error or "unreadable or unsupported video file")
    return has_audio, duration, text


def extract_audio_ffmpeg(video_path: str, wav_path: str, progress_cb=None, cancelled_cb=None):
    """Extract a 16 kHz mono PCM wave file, reporting progress 0-100."""
    has_audio, duration, _info = probe_video(video_path)
    if not has_audio:
        raise NoAudioTrack(video_path)

    os.makedirs(os.path.dirname(wav_path) or ".", exist_ok=True)
    if os.path.exists(wav_path):
        os.remove(wav_path)

    cmd = [
        _ffmpeg_exe(),
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        "-f", "wav",
        wav_path,
        "-progress", "pipe:1",
        "-nostats",
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_CREATE_NO_WINDOW,
    )
    stderr_chunks = []
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            if cancelled_cb is not None and cancelled_cb():
                proc.terminate()
                raise InterruptedError("cancelled")
            line = raw.strip()
            if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                try:
                    micros = float(line.split("=", 1)[1])
                except ValueError:
                    continue
                if duration > 0 and progress_cb is not None:
                    progress_cb(min(99, int(micros / 1e6 / duration * 100)))
            elif line.startswith("out_time="):
                try:
                    h, m, s = line.split("=", 1)[1].split(":")
                    seconds = int(h) * 3600 + int(m) * 60 + float(s)
                    if duration > 0 and progress_cb is not None:
                        progress_cb(min(99, int(seconds / duration * 100)))
                except ValueError:
                    pass
            elif line == "progress=end":
                if progress_cb is not None:
                    progress_cb(100)
        proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    try:
        if proc.stderr is not None:
            stderr_chunks.append(proc.stderr.read() or "")
    except Exception:
        pass

    if proc.returncode not in (0, None) and not os.path.exists(wav_path):
        detail = "\n".join(stderr_chunks).strip() or "ffmpeg exited with code %s" % proc.returncode
        raise WorkerError(detail)
    if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
        raise WorkerError("ffmpeg produced no audio output")
    if progress_cb is not None:
        progress_cb(100)
    return wav_path


def load_wav_mono(path: str) -> np.ndarray:
    """Read the extracted PCM wave file into float32 mono in [-1, 1]."""
    with wave.open(path, "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        frames = handle.readframes(handle.getnframes())
    if width != 2:
        raise WorkerError("unexpected sample width %d in %s" % (width, path))
    data = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return np.ascontiguousarray(data)


def _model_is_cached(model_name: str) -> bool:
    try:
        from faster_whisper.utils import download_model

        download_model(model_name, local_files_only=True)
        return True
    except Exception:
        return False


def _local_model_path(model_name: str) -> str:
    """Folder of a recognition model shipped with the program, or ''.

    Handing that folder to :class:`WhisperModel` instead of the bare model
    name makes the library open the files in place: it never looks at the
    Hugging Face cache and never tries the network, which is what lets the
    very first run of a fresh install work offline.
    """
    try:
        import vt_install

        return vt_install.model_dir(model_name)
    except Exception:  # noqa: BLE001 - a missing helper must not break the app
        return ""


def _looks_like_network_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    markers = (
        "connection", "timed out", "timeout", "temporary failure",
        "name or service", "network is unreachable", "proxy", "ssl",
        "max retries", "could not resolve", "offline", "unreachable",
        "failed to establish", "gaierror",
    )
    return any(marker in text for marker in markers)


# --------------------------------------------------------------------- threads
class ExtractAudioThread(QThread):
    progress = pyqtSignal(int)
    stages = pyqtSignal(str)
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, video_path, audio_path, lang="en", parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.audio_path = audio_path
        self.lang = lang

    def run(self):
        try:
            self.stages.emit(tr(self.lang, "stage_probe_audio"))
            extract_audio_ffmpeg(
                self.video_path,
                self.audio_path,
                progress_cb=lambda value: self.progress.emit(int(value)),
                cancelled_cb=self.isInterruptionRequested,
            )
            self.progress.emit(100)
            self.completed.emit(self.audio_path)
        except NoAudioTrack:
            self.failed.emit(tr(self.lang, "err_no_audio"))
        except InterruptedError:
            self.failed.emit(tr(self.lang, "msg_cancel_requested"))
        except Exception as exc:
            log.exception("audio extraction failed")
            self.failed.emit(tr(self.lang, "err_extract", msg=str(exc)))


class TranscriptionThread(QThread):
    progress = pyqtSignal(int)
    stages = pyqtSignal(str)
    completed = pyqtSignal(list, str, str)
    failed = pyqtSignal(str)

    def __init__(self, video_path, audio_path, language, temp_dir, model_name="base",
                 lang="en", engine="local", api_key="", parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.audio_path = audio_path
        self.language = language
        self.temp_dir = temp_dir
        self.model_name = model_name or "base"
        self.lang = lang
        self.engine = engine or "local"
        self.api_key = api_key or ""

    # -------------------------------------------------------------- internals
    def _ensure_audio(self):
        target = os.path.join(self.temp_dir, "audio.wav")
        if self.audio_path and os.path.exists(self.audio_path):
            return self.audio_path
        if not os.path.exists(self.video_path):
            raise WorkerError(tr(self.lang, "err_input_missing", path=self.video_path))
        self.stages.emit(tr(self.lang, "stage_extract"))
        try:
            return extract_audio_ffmpeg(
                self.video_path,
                target,
                progress_cb=lambda value: self.progress.emit(int(value)),
                cancelled_cb=self.isInterruptionRequested,
            )
        except NoAudioTrack:
            raise
        except InterruptedError:
            raise
        except WorkerError as exc:
            # Already-translated messages (from the API layer) stay as they are;
            # raw ffmpeg stderr gets wrapped in the user-facing wording.
            message = str(exc)
            if "ffmpeg" in message.lower() or message.startswith("["):
                raise WorkerError(tr(self.lang, "err_extract", msg=message)) from exc
            raise

    def _load_model(self):
        from faster_whisper import WhisperModel

        local = _local_model_path(self.model_name)
        source = local or self.model_name
        cached = bool(local) or _model_is_cached(self.model_name)
        if cached:
            self.stages.emit(tr(self.lang, "stage_whisper", model=self.model_name))
        else:
            self.stages.emit(tr(self.lang, "stage_download_model", model=self.model_name))

        options = {"device": "cpu", "compute_type": "int8"}
        if not local:
            # Only consulted when the model is looked up by name; a folder is
            # already local by definition.
            options["local_files_only"] = cached

        def open_model():
            try:
                return WhisperModel(source, **options)
            except TypeError as exc:
                # Older faster-whisper releases do not expose
                # ``local_files_only``. Keep them usable with cached models.
                if "local_files_only" not in str(exc):
                    raise
                options.pop("local_files_only", None)
                return WhisperModel(source, **options)

        try:
            return open_model()
        except Exception as first_error:
            if cached:
                raise
            # The download failed: fall back to whatever is already on disk.
            log.warning("model download failed (%s); retrying from the local cache", first_error)
            options["local_files_only"] = True
            return open_model()

    # -------------------------------------------------------------------- run
    def _run_api(self, audio):
        """Cloud transcription path (OpenAI / Groq / Gemini)."""
        import vt_api

        labels = {"openai": "OpenAI", "groq": "Groq", "gemini": "Google Gemini"}
        label = labels.get(self.engine, self.engine)
        self.progress.emit(0)
        self.stages.emit(tr(self.lang, "stage_api_transcribe", engine=label))
        try:
            segments, detected = vt_api.transcribe_audio(
                self.engine,
                self.api_key,
                audio,
                self.language,
                self.model_name,
                lang=self.lang,
                cancelled_cb=self.isInterruptionRequested,
                progress_cb=lambda value: self.progress.emit(int(value)),
            )
        except WorkerError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - never crash the UI thread
            log.exception("cloud transcription failed")
            if _looks_like_network_error(exc):
                self.failed.emit(tr(self.lang, "err_api_offline", engine=label))
            else:
                self.failed.emit(tr(self.lang, "err_transcribe", msg=str(exc)))
            return

        subtitles = []
        for item in segments:
            start = timedelta(seconds=float(item.get("start", 0.0)))
            end = timedelta(seconds=float(item.get("end", 0.0)))
            if end <= start:
                end = start + timedelta(milliseconds=200)
            text = str(item.get("text") or "").strip()
            if text:
                subtitles.append(srt.Subtitle(index=len(subtitles) + 1, start=start, end=end, content=text))
        if not subtitles:
            self.failed.emit(tr(self.lang, "msg_empty_result"))
            return
        if self.isInterruptionRequested():
            self.failed.emit(tr(self.lang, "msg_cancel_requested"))
            return
        self.progress.emit(100)
        self.completed.emit(subtitles, detected or "auto", audio)

    def run(self):
        try:
            audio = self._ensure_audio()
            if not os.path.exists(audio):
                raise WorkerError("audio file does not exist: %s" % audio)
            if os.path.getsize(audio) == 0:
                raise WorkerError("the extracted audio file is empty")

            if self.isInterruptionRequested():
                self.failed.emit(tr(self.lang, "msg_cancel_requested"))
                return

            if self.engine != "local":
                self._run_api(audio)
                return

            try:
                model = self._load_model()
            except Exception as exc:
                log.exception("could not load the recogniser model")
                if _looks_like_network_error(exc):
                    self.failed.emit(tr(self.lang, "err_transcribe_offline"))
                else:
                    self.failed.emit(tr(self.lang, "err_transcribe", msg=str(exc)))
                return

            self.progress.emit(0)
            self.stages.emit(tr(self.lang, "stage_transcribing"))

            samples = load_wav_mono(audio)
            language = None if self.language in (None, "", "auto") else self.language
            segments, info = model.transcribe(
                samples,
                language=language,
                beam_size=5,
                log_progress=False,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 400},
            )

            subtitles = []
            total_duration = float(getattr(info, "duration", 0.0) or 0.0) or max(
                len(samples) / 16000.0, 0.001
            )
            for seg in segments:
                if self.isInterruptionRequested():
                    break
                text = (seg.text or "").strip()
                if not text:
                    continue
                start = timedelta(seconds=float(seg.start))
                end = timedelta(seconds=float(seg.end))
                if end <= start:
                    end = start + timedelta(milliseconds=200)
                subtitles.append(
                    srt.Subtitle(index=len(subtitles) + 1, start=start, end=end, content=text)
                )
                pct = int(float(seg.end) / max(total_duration, 0.001) * 100)
                self.progress.emit(min(99, pct))

            if self.isInterruptionRequested():
                self.failed.emit(tr(self.lang, "msg_cancel_requested"))
                return

            if not subtitles:
                # Say so instead of quietly filling the table with nothing.
                self.failed.emit(tr(self.lang, "msg_empty_result"))
                return

            detected = info.language or "auto"
            self.progress.emit(100)
            self.completed.emit(subtitles, detected, audio)
        except NoAudioTrack:
            self.failed.emit(tr(self.lang, "err_no_audio"))
        except WorkerError as exc:
            self.failed.emit(str(exc))
        except InterruptedError:
            self.failed.emit(tr(self.lang, "msg_cancel_requested"))
        except Exception as exc:
            log.exception("transcription failed")
            if _looks_like_network_error(exc):
                self.failed.emit(tr(self.lang, "err_transcribe_offline"))
            else:
                self.failed.emit(tr(self.lang, "err_transcribe", msg=str(exc)))


class TranslationThread(QThread):
    progress = pyqtSignal(int)
    stages = pyqtSignal(str)
    completed = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, subtitles, source, target, bilateral, lang="en",
                 engine="local", api_key="", translate_model="", parent=None):
        super().__init__(parent)
        self.subtitles = subtitles
        self.source = source
        self.target = target
        self.bilateral = bilateral
        self.lang = lang
        self.engine = engine or "local"
        self.api_key = api_key or ""
        self.translate_model = translate_model or ""

    def _translate_line(self, line, source, target):
        if not line.strip():
            return line

        from deep_translator import GoogleTranslator

        last_error = None
        for attempt in range(3):
            if self.isInterruptionRequested():
                raise WorkerError(tr(self.lang, "msg_cancel_requested"))
            try:
                result = GoogleTranslator(source=source, target=target).translate(line)
                if result:
                    return result.strip()
            except Exception as exc:  # noqa: BLE001 - retried below
                last_error = exc
                time.sleep(0.6 * (attempt + 1))
        if last_error is not None and _looks_like_network_error(last_error):
            raise WorkerError(tr(self.lang, "err_translate_offline"))
        if last_error is not None:
            raise WorkerError(tr(self.lang, "err_translate", msg=str(last_error)))
        raise WorkerError(tr(self.lang, "err_translate_empty"))

    def _source_texts(self):
        """The strings that have to be translated, one per subtitle row."""
        texts = []
        for sub in self.subtitles:
            lines = sub.content.splitlines()
            if self.bilateral:
                texts.append(lines[0] if lines else "")
            else:
                texts.append("\n".join(lines))
        return texts

    def _run_api(self):
        """Cloud translation path: one batched request instead of one per line."""
        import vt_api

        labels = {"openai": "OpenAI", "groq": "Groq", "gemini": "Google Gemini"}
        label = labels.get(self.engine, self.engine)
        self.stages.emit(tr(self.lang, "stage_api_translate", engine=label))
        texts = self._source_texts()
        placeholders = [t if t.strip() else "" for t in texts]
        translated = vt_api.translate_texts(
            self.engine,
            self.api_key,
            [t for t in placeholders if t.strip()] or placeholders,
            self.source,
            self.target,
            self.translate_model,
            lang=self.lang,
            cancelled_cb=self.isInterruptionRequested,
            progress_cb=lambda value: self.progress.emit(int(value)),
        )
        # Re-align: translate_texts returns the non-empty subset in order.
        if len(translated) == len([t for t in placeholders if t.strip()]):
            it = iter(translated)
            aligned = [next(it) if t.strip() else "" for t in placeholders]
        else:  # pragma: no cover - defensive, keeps the row count intact
            aligned = (translated + placeholders)[: len(placeholders)]
        output = []
        for sub, original, done in zip(self.subtitles, texts, aligned):
            if self.bilateral:
                content = "\n".join(part for part in (original.strip(), done.strip()) if part)
            else:
                content = done.strip() or original
            output.append(srt.Subtitle(index=sub.index, start=sub.start, end=sub.end, content=content))
        self.progress.emit(100)
        self.completed.emit(output)

    def run(self):
        try:
            if self.engine != "local":
                self._run_api()
                return
            self.stages.emit(tr(self.lang, "stage_test_translator"))
            self.stages.emit(tr(self.lang, "stage_translating"))
            output = []
            total = max(len(self.subtitles), 1)
            for idx, sub in enumerate(self.subtitles, start=1):
                if self.isInterruptionRequested():
                    self.failed.emit(tr(self.lang, "msg_cancel_requested"))
                    return
                lines = sub.content.splitlines()
                if self.bilateral:
                    if len(lines) >= 2:
                        original, translated = lines[0], lines[-1]
                    else:
                        original = lines[0] if lines else ""
                        translated = self._translate_line(original, "auto", self.target) or ""
                    content = "\n".join(part for part in (original, translated) if part)
                else:
                    combined = "\n".join(lines) if lines else ""
                    content = self._translate_line(combined, self.source, self.target) or combined
                output.append(
                    srt.Subtitle(index=sub.index, start=sub.start, end=sub.end, content=content)
                )
                self.progress.emit(min(99, int(idx / total * 100)))
            self.progress.emit(100)
            self.completed.emit(output)
        except WorkerError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            log.exception("translation failed")
            if _looks_like_network_error(exc):
                self.failed.emit(tr(self.lang, "err_translate_offline"))
            else:
                self.failed.emit(tr(self.lang, "err_translate", msg=str(exc)))


class RenderThread(QThread):
    progress = pyqtSignal(int)
    stages = pyqtSignal(str)
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, video_path, subtitles, output_path, temp_dir, font_path=None, lang="en", parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.subtitles = subtitles
        self.output_path = output_path
        self.temp_dir = temp_dir
        self.font_path = font_path
        self.lang = lang

    def _verify_output(self):
        """Fail loudly when the finished file is missing, empty or unplayable.

        Without this check a failed ffmpeg pass left behind a 0-byte or
        truncated file and the UI still reported success.
        """
        path = self.output_path
        if not os.path.exists(path):
            raise WorkerError(tr(self.lang, "err_render_missing", path=path))
        size = os.path.getsize(path)
        if size <= 0:
            raise WorkerError(tr(self.lang, "err_render_empty", path=path))
        try:
            has_audio, duration, _info = probe_video(path)
        except Exception as exc:  # noqa: BLE001 - any probe failure means unplayable
            raise WorkerError(tr(self.lang, "err_render_truncated", path=path)) from exc
        if duration <= 0:
            raise WorkerError(tr(self.lang, "err_render_truncated", path=path))
        source_has_audio = True
        try:
            source_has_audio, _, _ = probe_video(self.video_path)
        except Exception:  # noqa: BLE001 - the source was already probed before
            pass
        if source_has_audio and not has_audio:
            # Re-attach the original audio instead of shipping a silent video.
            self.stages.emit(tr(self.lang, "stage_repair_audio"))
            self._remux_audio()
            has_audio, duration, _info = probe_video(path)
            if not has_audio:
                raise WorkerError(tr(self.lang, "err_render_no_audio", path=path))
        return size, duration

    def _remux_audio(self):
        """Copy the source audio track into the rendered file with ffmpeg."""
        tmp = self.output_path + ".fixed.mp4"
        result = _run_ffmpeg(
            [
                "-hide_banner", "-loglevel", "error", "-y",
                "-i", self.output_path,
                "-i", self.video_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-shortest",
                tmp,
            ],
            timeout=1800,
        )
        if result.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            os.replace(tmp, self.output_path)
        else:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass

    def run(self):
        try:
            from moviepy import CompositeVideoClip, TextClip, VideoFileClip
        except Exception as exc:
            self.failed.emit(tr(self.lang, "err_render", msg=str(exc)))
            return

        try:
            self.stages.emit(tr(self.lang, "stage_loading_video"))
            video = VideoFileClip(self.video_path)
            width, height = int(video.w), int(video.h)
            # Keep long single-line captions inside the frame.
            font_size = max(20, int(min(width, height) / 26))
            overlays = []
            sub_count = 0
            for sub in self.subtitles:
                start_td = sub.start
                end_td = sub.end if sub.end > sub.start else sub.start + timedelta(seconds=1)
                duration = (end_td - start_td).total_seconds()
                if duration <= 0.02:
                    continue
                lines = [line for line in sub.content.splitlines() if line.strip()]
                if not lines:
                    continue
                line_height = int(font_size * 1.5)
                for line_index, line in enumerate(lines):
                    sub_count += 1
                    text_clip = TextClip(
                        text=line,
                        font=self.font_path,
                        font_size=font_size,
                        color="white",
                        bg_color=None,
                        stroke_color="black",
                        stroke_width=2,
                        method="label",
                    )
                    y = int(height * 0.92) - ((len(lines) - line_index) * line_height)
                    overlays.append(
                        text_clip.with_start(start_td.total_seconds())
                        .with_duration(duration)
                        .with_position(("center", max(0, y)))
                    )
            self.stages.emit(tr(self.lang, "stage_burning", count=sub_count))
            composite = CompositeVideoClip([video] + overlays)
            try:
                temp_audio = os.path.join(self.temp_dir, "render_temp_audio.m4a")
                from vt_render import MoviePyProgressLogger

                self._logger = MoviePyProgressLogger(self.progress.emit)
                composite.write_videofile(
                    self.output_path,
                    fps=int(video.fps or 25),
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=temp_audio,
                    remove_temp=True,
                    logger=self._logger,
                )
            finally:
                try:
                    composite.close()
                except Exception:
                    pass
                video.close()
            self.stages.emit(tr(self.lang, "stage_verify_output"))
            size, length = self._verify_output()
            log.info("render verified: %s (%.1f MB, %.1fs)", self.output_path, size / 1e6, length)
            self.progress.emit(100)
            self.completed.emit(self.output_path)
        except WorkerError as exc:
            log.error("render rejected: %s", exc)
            self.failed.emit(str(exc))
        except InterruptedError:
            self.failed.emit(tr(self.lang, "msg_cancel_requested"))
        except Exception as exc:
            log.exception("render failed")
            self.failed.emit(tr(self.lang, "err_render", msg=str(exc)))
