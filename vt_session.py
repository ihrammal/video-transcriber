"""Atomic, local-only recovery of an unfinished transcript. Never stores API keys."""
import json
import os
import tempfile


def path():
    import vt_bootstrap
    return os.path.join(vt_bootstrap.app_data_dir(), "unfinished-transcript.json")


def save(source, text, timestamps, subtitles):
    target = path()
    data = {"version": 1, "source": source, "text": text, "timestamps": bool(timestamps),
            "subtitles": [{"start": s.start.total_seconds(), "end": s.end.total_seconds(),
                           "text": s.content} for s in subtitles]}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=os.path.dirname(target), delete=False) as handle:
            temporary = handle.name
            json.dump(data, handle, ensure_ascii=False)
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.remove(temporary)


def load():
    try:
        with open(path(), encoding="utf-8") as handle:
            data = json.load(handle)
        if (isinstance(data, dict) and data.get("version") == 1
                and isinstance(data.get("text"), str) and data["text"].strip()
                and isinstance(data.get("source"), str) and isinstance(data.get("subtitles"), list)):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return None


def clear():
    try:
        os.remove(path())
    except OSError:
        pass
