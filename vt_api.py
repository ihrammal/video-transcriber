"""vt_api.py -- cloud transcription and translation clients.

Three optional engines sit behind the free local one:

* ``openai`` -- Whisper for speech, GPT for text (``https://api.openai.com``)
* ``groq``   -- Whisper large v3 for speech, Llama for text (``https://api.groq.com``)
* ``gemini`` -- Google Gemini for both (``https://generativelanguage.googleapis.com``)

Rules this module keeps:

* Every failure is raised as :class:`vt_workers.WorkerError` carrying an
  **already translated** message, so the UI never shows a raw traceback and
  never crashes on a missing key, a bad key, a quota limit or no internet.
* Nothing here is imported unless the user actually chose an API engine, so a
  machine that only uses the local engine never touches the network.
* Requests are retried once on a transient error; a 401/403 (bad key), 404
  (wrong model name) and 429 (quota) are reported immediately with a hint
  telling the user what to change in Settings.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
import time

from vt_i18n import tr

log = logging.getLogger("vidtrans.api")

_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

ENDPOINTS = {
    "openai": {
        "transcribe": "https://api.openai.com/v1/audio/transcriptions",
        "translate": "https://api.openai.com/v1/chat/completions",
        "models": "https://api.openai.com/v1/models",
    },
    "groq": {
        "transcribe": "https://api.groq.com/openai/v1/audio/transcriptions",
        "translate": "https://api.groq.com/openai/v1/chat/completions",
        "models": "https://api.groq.com/openai/v1/models",
    },
    "gemini": {
        "transcribe": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "translate": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "models": "https://generativelanguage.googleapis.com/v1beta/models",
    },
}

# The translation prompt must make the model echo the array shape exactly.
_TRANSLATE_SYSTEM = (
    "You are a subtitle translator. Translate every string in the JSON array "
    "the user gives you from {source} to {target}. Return ONLY a JSON array of "
    "strings with exactly the same length and order as the input. Keep line "
    "breaks inside each string. Never add explanations."
)

_TRANSCRIBE_SYSTEM = (
    "Transcribe the speech in this audio. Reply with ONLY a JSON object of the "
    "form {\"language\": \"xx\", \"segments\": [{\"start\": 0.0, "
    "\"end\": 1.2, \"text\": \"...\"}]}. Use seconds for start and end."
)


def _worker_error(message: str) -> Exception:
    """Build a ``vt_workers.WorkerError`` without importing Qt at module load."""
    from vt_workers import WorkerError

    return WorkerError(message)


class ApiFailure(Exception):
    """Internal failure carrying a translated message."""

    def __init__(self, message: str, *, hint_key: str | None = None):
        super().__init__(message)
        self.hint_key = hint_key


# --------------------------------------------------------------------- helpers
def engine_label(engine: str) -> str:
    return {"openai": "OpenAI", "groq": "Groq", "gemini": "Google Gemini"}.get(engine, engine)


def _fail(lang: str, key: str, **kwargs) -> ApiFailure:
    return ApiFailure(tr(lang, key, **kwargs), hint_key=key)


def _http(method: str = "GET", *, url: str, headers=None, data=None, json_body=None,
          files=None, params=None, timeout: float = 180):
    """One HTTP call with a short, polite retry.

    Transient failures (no connection, a dropped socket) and rate limits
    (HTTP 429, plus the occasional 5xx) are retried up to three times with an
    exponential pause, honouring ``Retry-After`` when the server sends it, so
    an intermittent network never turns into a failed job for the user.
    """
    import requests

    last = None
    for attempt in range(3):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                data=data,
                json=json_body,
                files=files,
                params=params,
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 - classified by the caller
            last = exc
            if attempt < 2:
                time.sleep(1.2 * (attempt + 1))
                continue
            raise
        if response.status_code in (429,) or response.status_code >= 500:
            last = None
            if attempt >= 2:
                return response
            delay = 1.5 * (attempt + 1)
            retry_after = response.headers.get("Retry-After") if response.headers else None
            try:
                delay = min(10.0, float(retry_after)) if retry_after else delay
            except (TypeError, ValueError):
                pass
            time.sleep(delay)
            continue
        return response
    if last is not None:
        raise last
    raise RuntimeError("unreachable")  # pragma: no cover - defensive only


def _check_response(response, engine: str, lang: str, what: str) -> dict:
    """Turn an HTTP response into JSON or raise an ApiFailure with a hint."""
    label = engine_label(engine)
    status = getattr(response, "status_code", 0)
    try:
        payload = response.json()
    except Exception:  # noqa: BLE001 - HTML error pages are common on 5xx
        payload = {}

    if status in (401, 403):
        raise _fail(lang, "err_api_key_invalid", engine=label)
    if status == 404:
        error = payload.get("error")
        if isinstance(error, dict):
            detail = str(error.get("message", ""))[:200]
        elif isinstance(error, str):
            detail = error[:200]
        else:
            detail = ""
        raise _fail(lang, "err_api_not_found", engine=label, detail=detail or what)
    if status == 429:
        raise _fail(lang, "err_api_quota", engine=label)
    if status >= 500:
        raise _fail(lang, "err_api_server", engine=label, code=status)
    if status >= 400:
        error = payload.get("error")
        if isinstance(error, dict):
            detail = str(error.get("message", ""))[:300]
        elif isinstance(error, str):
            detail = error[:300]
        else:
            detail = ""
        raise _fail(lang, "err_api_bad_request", engine=label, detail=detail or "HTTP %s" % status)
    return payload


def _looks_offline(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "connection", "timed out", "timeout", "max retries",
            "name or service", "unreachable", "could not resolve",
            "failed to establish", "gaierror", "proxy", "ssl",
        )
    )


def _post_with_network_guard(lang: str, engine: str, **kwargs):
    try:
        return _http(**kwargs)
    except ApiFailure:
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("%s request failed: %s", engine, exc)
        if _looks_offline(exc):
            raise _fail(lang, "err_api_offline", engine=engine_label(engine)) from exc
        raise _fail(lang, "err_api_transport", engine=engine_label(engine), detail=str(exc)[:200]) from exc


# ------------------------------------------------------------------ audio prep
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


def prepare_audio(path: str, lang: str, cancelled_cb=None) -> str:
    """Return a compact (<= ~15 MB) upload copy of ``path``.

    API endpoints cap uploads (OpenAI 25 MB, Gemini ~20 MB inline), so a long
    video's 16 kHz wave file is transcoded to mono MP3 first. Small files are
    passed through untouched to avoid a pointless re-encode.
    """
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        raise _fail(lang, "err_audio_missing", detail=str(exc)) from exc
    if size == 0:
        raise _fail(lang, "err_audio_empty")
    if size <= 15 * 1024 * 1024 and os.path.splitext(path)[1].lower() in (".mp3", ".m4a", ".ogg", ".flac"):
        return path
    if size <= 15 * 1024 * 1024 and os.path.splitext(path)[1].lower() == ".wav" and size <= 4 * 1024 * 1024:
        return path

    out = os.path.join(
        os.path.dirname(path) or tempfile.gettempdir(),
        "vt_upload_%d.mp3" % int(time.time()),
    )
    try:
        proc = subprocess.run(
            [
                _ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                "-i", path, "-vn", "-ac", "1", "-ar", "16000",
                "-b:a", "64k", "-f", "mp3", out,
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=600, creationflags=_CREATE_NO_WINDOW,
        )
    except Exception as exc:  # noqa: BLE001
        raise _fail(lang, "err_api_audio_prepare", detail=str(exc)) from exc
    if cancelled_cb is not None and cancelled_cb():
        raise _fail(lang, "msg_cancel_requested")
    if proc.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
        detail = (proc.stderr or "").strip()[:300] or "ffmpeg exit %s" % proc.returncode
        raise _fail(lang, "err_api_audio_prepare", detail=detail)
    return out


def _read_b64(path: str, lang: str) -> str:
    try:
        with open(path, "rb") as handle:
            return base64.b64encode(handle.read()).decode("ascii")
    except OSError as exc:
        raise _fail(lang, "err_audio_missing", detail=str(exc)) from exc


# --------------------------------------------------------------- transcription
def _transcribe_openai_compatible(engine: str, api_key: str, audio_path: str,
                                  language: str, model: str, lang: str,
                                  cancelled_cb=None) -> dict:
    url = ENDPOINTS[engine]["transcribe"]
    headers = {"Authorization": "Bearer %s" % api_key}
    with open(audio_path, "rb") as handle:
        data = {
            "model": model or ("whisper-1" if engine == "openai" else "whisper-large-v3"),
            "response_format": "verbose_json",
        }
        if language and language not in ("auto", ""):
            data["language"] = language
        response = _post_with_network_guard(
            lang, engine,
            method="POST", url=url, headers=headers,
            data=data, files={"file": (os.path.basename(audio_path), handle, "audio/mpeg")},
            timeout=600,
        )
    return _check_response(response, engine, lang, "audio/transcriptions")


def _segments_from_openai(payload: dict, lang: str) -> tuple[list, str]:
    segments = payload.get("segments") or []
    detected = str(payload.get("language") or "auto") or "auto"
    out = []
    for item in segments:
        try:
            start = float(item.get("start", 0.0))
            end = float(item.get("end", 0.0))
        except (TypeError, ValueError):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            out.append({"start": start, "end": end, "text": text})
    if not out:
        text = str(payload.get("text") or "").strip()
        if text:
            out.append({"start": 0.0, "end": 3.0, "text": text})
    if not out:
        raise _fail(lang, "err_api_empty_result", engine="API")
    return out, detected


def _transcribe_gemini(api_key: str, audio_path: str, language: str,
                       model: str, lang: str, cancelled_cb=None) -> dict:
    model = model or "gemini-2.5-flash"
    url = ENDPOINTS["gemini"]["transcribe"].format(model=model)
    mime = "audio/mpeg" if audio_path.lower().endswith(".mp3") else "audio/wav"
    hint = "" if (language in ("auto", "", None)) else " The speech is %s." % _lang_name(language)
    body = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": mime, "data": _read_b64(audio_path, lang)}},
                    {"text": _TRANSCRIBE_SYSTEM.replace("{lang}", language or "auto") + hint},
                ]
            }
        ],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    response = _post_with_network_guard(
        lang, "gemini", method="POST", url=url,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json_body=body, timeout=600,
    )
    return _check_response(response, "gemini", lang, "generateContent")


def _lang_name(code: str) -> str:
    names = {"en": "English", "ar": "Arabic", "fr": "French", "es": "Spanish",
             "de": "German", "zh": "Chinese", "hi": "Hindi", "ja": "Japanese",
             "pt": "Portuguese", "ru": "Russian"}
    return names.get(str(code), str(code))


def _text_from_gemini(payload: dict, lang: str) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        if (payload.get("promptFeedback") or {}).get("blockReason"):
            raise _fail(lang, "err_api_blocked", engine="Google Gemini")
        raise _fail(lang, "err_api_empty_result", engine="Google Gemini")
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    text = "".join(str(part.get("text") or "") for part in parts)
    if not text.strip():
        raise _fail(lang, "err_api_empty_result", engine="Google Gemini")
    return text


def _parse_json_block(text: str) -> str:
    """Strip markdown fences and return the first balanced JSON object/array."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def _segments_from_gemini(payload: dict, lang: str) -> tuple[list, str]:
    text = _parse_json_block(_text_from_gemini(payload, lang))
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Some models wrap the object in prose: take the outermost braces.
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError as exc:
                raise _fail(lang, "err_api_bad_json", engine="Google Gemini",
                            detail=str(exc)[:120]) from exc
        else:
            raise _fail(lang, "err_api_bad_json", engine="Google Gemini", detail="no object")
    detected = str(data.get("language") or "auto") or "auto"
    out = []
    for item in (data.get("segments") or []):
        try:
            start_s = float(item.get("start", 0.0))
            end_s = float(item.get("end", 0.0))
        except (TypeError, ValueError):
            continue
        body = str(item.get("text") or "").strip()
        if body:
            out.append({"start": start_s, "end": end_s, "text": body})
    if not out:
        raise _fail(lang, "err_api_empty_result", engine="Google Gemini")
    return out, detected


def transcribe_audio(engine: str, api_key: str, audio_path: str, language: str,
                     model: str, lang: str = "en", cancelled_cb=None,
                     progress_cb=None) -> tuple[list, str]:
    """Return ``([{start, end, text}, ...], detected_language)``.

    Raises :class:`vt_workers.WorkerError` with a translated message when the
    key is missing or rejected, the quota is exhausted, or the machine is
    offline.
    """
    try:
        return _transcribe_audio(engine, api_key, audio_path, language, model,
                                 lang, cancelled_cb, progress_cb)
    except ApiFailure as exc:
        raise _worker_error(str(exc)) from exc


def _transcribe_audio(engine, api_key, audio_path, language, model, lang,
                      cancelled_cb, progress_cb) -> tuple[list, str]:
    if progress_cb:
        progress_cb(5)
    if not str(api_key or "").strip():
        raise _fail(lang, "err_api_key_missing", engine=engine_label(engine))
    upload = prepare_audio(audio_path, lang, cancelled_cb=cancelled_cb)
    if progress_cb:
        progress_cb(25)
    if cancelled_cb is not None and cancelled_cb():
        raise _fail(lang, "msg_cancel_requested")

    try:
        if engine == "gemini":
            payload = _transcribe_gemini(api_key, upload, language, model, lang, cancelled_cb)
            segments, detected = _segments_from_gemini(payload, lang)
        else:
            payload = _transcribe_openai_compatible(
                engine, api_key, upload, language, model, lang, cancelled_cb
            )
            segments, detected = _segments_from_openai(payload, lang)
    finally:
        if upload != audio_path:
            try:
                os.remove(upload)
            except OSError:
                pass

    if cancelled_cb is not None and cancelled_cb():
        raise _fail(lang, "msg_cancel_requested")
    if progress_cb:
        progress_cb(100)
    return segments, detected or (language or "auto")


# ------------------------------------------------------------------ translation
def _translate_openai_compatible(engine: str, api_key: str, texts: list,
                                 source: str, target: str, model: str,
                                 lang: str) -> list:
    url = ENDPOINTS[engine]["translate"]
    model = model or ("gpt-4o-mini" if engine == "openai" else "llama-3.1-8b-instant")
    system = _TRANSLATE_SYSTEM.format(
        source=_lang_name(source) if source not in ("auto", "", None) else "the source language",
        target=_lang_name(target),
    )
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(texts, ensure_ascii=False)},
        ],
    }
    response = _post_with_network_guard(
        lang, engine, method="POST", url=url,
        headers={"Authorization": "Bearer %s" % api_key, "Content-Type": "application/json"},
        json_body=body, timeout=300,
    )
    payload = _check_response(response, engine, lang, "chat/completions")
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise _fail(lang, "err_api_empty_result", engine=engine_label(engine)) from exc
    return _extract_list(content, texts, engine, lang)


def _translate_gemini(api_key: str, texts: list, source: str, target: str,
                      model: str, lang: str) -> list:
    model = model or "gemini-2.5-flash"
    url = ENDPOINTS["gemini"]["translate"].format(model=model)
    system = _TRANSLATE_SYSTEM.format(
        source=_lang_name(source) if source not in ("auto", "", None) else "the source language",
        target=_lang_name(target),
    )
    body = {
        "contents": [{"parts": [{"text": system + "\n\n" + json.dumps(texts, ensure_ascii=False)}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    response = _post_with_network_guard(
        lang, "gemini", method="POST", url=url,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json_body=body, timeout=300,
    )
    payload = _check_response(response, "gemini", lang, "generateContent")
    return _extract_list(_text_from_gemini(payload, lang), texts, "gemini", lang)


def _extract_list(content: str, original: list, engine: str, lang: str) -> list:
    """Parse the model's answer and guarantee one string per input line."""
    text = _parse_json_block(content)
    parsed = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                parsed = None
        if parsed is None:
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    parsed = None
    if isinstance(parsed, dict):
        for value in parsed.values():
            if isinstance(value, list):
                parsed = value
                break
    if not isinstance(parsed, list):
        raise _fail(lang, "err_api_bad_json", engine=engine_label(engine),
                    detail=text[:120].replace("\n", " "))
    parsed = [str(item) if item is not None else "" for item in parsed]
    if len(parsed) != len(original):
        # Pad / truncate so the caption table never loses a row.
        log.warning("%s returned %d lines for %d inputs", engine, len(parsed), len(original))
        if len(parsed) < len(original):
            parsed = parsed + original[len(parsed):]
        else:
            parsed = parsed[: len(original)]
    return [item if item.strip() else original[index] for index, item in enumerate(parsed)]


def translate_texts(engine: str, api_key: str, texts: list, source: str, target: str,
                    translate_model: str = "", lang: str = "en",
                    cancelled_cb=None, progress_cb=None) -> list:
    """Translate ``texts`` in batches; returns a list of the same length."""
    try:
        return _translate_texts(engine, api_key, texts, source, target,
                                translate_model, lang, cancelled_cb, progress_cb)
    except ApiFailure as exc:
        raise _worker_error(str(exc)) from exc


def _translate_texts(engine, api_key, texts, source, target, translate_model,
                     lang, cancelled_cb, progress_cb) -> list:
    texts = [str(t or "") for t in texts]
    if not texts:
        return []
    if not str(api_key or "").strip():
        raise _fail(lang, "err_api_key_missing", engine=engine_label(engine))

    batch_size = 40
    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
    out: list = []
    for index, batch in enumerate(batches):
        if cancelled_cb is not None and cancelled_cb():
            raise _fail(lang, "msg_cancel_requested")
        if engine == "gemini":
            chunk = _translate_gemini(api_key, batch, source, target, translate_model, lang)
        else:
            chunk = _translate_openai_compatible(
                engine, api_key, batch, source, target, translate_model, lang
            )
        if not isinstance(chunk, list):
            chunk = []
        if len(chunk) != len(batch):
            # Never let a short answer drop caption rows: keep the original
            # text for the lines the engine did not return.
            log.warning("%s returned %d lines for a batch of %d",
                        engine, len(chunk), len(batch))
            chunk = (list(chunk) + list(batch)[len(chunk):])[: len(batch)]
        out.extend(chunk)
        if progress_cb:
            progress_cb(int((index + 1) / len(batches) * 100))
    if len(out) < len(texts):
        out = out + texts[len(out):]
    out = out[: len(texts)]
    # A blank answer keeps the original caption instead of blanking the row.
    return [item if str(item).strip() else original for item, original in zip(out, texts)]


# --------------------------------------------------------------- key validation
def _error_detail(response) -> str:
    """Human readable detail from an API error body (never a raw dict)."""
    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        return "HTTP %s" % getattr(response, "status_code", "?")
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = str(error.get("message") or "").strip()
        if message:
            return message[:200]
        status = str(error.get("status") or "").strip()
        if status:
            return status
    if isinstance(error, str) and error.strip():
        return error.strip()[:200]
    if isinstance(error, dict) is False and isinstance(payload, dict):
        for key in ("message", "detail"):
            if str(payload.get(key) or "").strip():
                return str(payload[key])[:200]
    return "HTTP %s" % getattr(response, "status_code", "?")


def test_key(engine: str, api_key: str, lang: str = "en") -> tuple[bool, str]:
    """Cheap connectivity/credential check. Returns ``(ok, translated message)``."""
    api_key = str(api_key or "").strip()
    if engine not in ENDPOINTS:
        return False, tr(lang, "err_api_unknown_engine", engine=str(engine))
    if not api_key:
        return False, tr(lang, "err_api_key_missing", engine=engine_label(engine))
    if engine == "gemini":
        url = ENDPOINTS["gemini"]["models"]
        params = {"key": api_key, "pageSize": "1"}
        headers = {}
    else:
        url = ENDPOINTS[engine]["models"]
        params = None
        headers = {"Authorization": "Bearer %s" % api_key}
    try:
        response = _http("GET", url=url, headers=headers, params=params, timeout=45)
    except Exception as exc:  # noqa: BLE001
        if _looks_offline(exc):
            return False, tr(lang, "err_api_offline", engine=engine_label(engine))
        return False, tr(lang, "err_api_transport", engine=engine_label(engine), detail=str(exc)[:160])
    status = response.status_code
    if status in (401, 403):
        return False, tr(lang, "err_api_key_invalid", engine=engine_label(engine))
    if status == 429:
        return False, tr(lang, "err_api_quota", engine=engine_label(engine))
    if status >= 400:
        return False, tr(
            lang, "err_api_bad_request",
            engine=engine_label(engine), detail=_error_detail(response),
        )
    return True, tr(lang, "msg_api_key_ok", engine=engine_label(engine))
