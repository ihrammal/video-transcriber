"""Run the real offline pipeline on the author's local sample recordings.

Outputs stay in test-results, which is excluded from version control.
"""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "test-results"
OUT.mkdir(exist_ok=True)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["LOCALAPPDATA"] = str(OUT / "profile")
os.environ["HF_HUB_OFFLINE"] = "1"

from PySide6.QtWidgets import QApplication
from faster_whisper import WhisperModel
import srt
from vt_workers import TranscriptionThread, RenderThread, probe_video
from vt_render import FONT_PATH
from vid_trans_app import MainWindow
import vt_secrets

# Local validation must never touch the author's real Windows credential store.
vt_secrets.is_available = lambda: False

app = QApplication([])
model_name = sys.argv[1] if len(sys.argv) > 1 else "base"
model = WhisperModel(str(ROOT / "models" / model_name), device="cpu", compute_type="int8")
report = []
for source in sorted((ROOT / "test audio-video").iterdir()):
    if source.suffix.lower() not in (".mp3", ".mp4"):
        continue
    folder = OUT / model_name / source.stem
    folder.mkdir(parents=True, exist_ok=True)
    errors, results, rendered = [], [], []
    start = time.monotonic()
    worker = TranscriptionThread(str(source), "", "auto", str(folder), model_name=model_name)
    worker._load_model = lambda: model
    worker.completed.connect(lambda subtitles, detected, audio: results.append((subtitles, detected)))
    worker.failed.connect(errors.append)
    worker.run()
    item = {"source": source.name, "model": model_name, "seconds": round(time.monotonic()-start, 2)}
    if results:
        subtitles, language = results[0]
        from types import SimpleNamespace
        writer = SimpleNamespace(show_timestamps=False)
        writer._plain_text_export = lambda subs: MainWindow._plain_text_export(writer, subs)
        MainWindow._write_caption_file(writer, str(folder / "transcript.txt"), subtitles)
        MainWindow._write_caption_file(writer, str(folder / "captions.srt"), subtitles)
        item.update(language=language, captions=len(subtitles), text="\n".join(s.content for s in subtitles))
        if model_name == "base":
            renderer = RenderThread(str(source), subtitles, str(folder / "subtitled.mp4"), str(folder), font_path=FONT_PATH)
            renderer.completed.connect(rendered.append)
            renderer.failed.connect(errors.append)
            renderer.run()
            if rendered:
                has_audio, duration, _ = probe_video(rendered[0])
                source_duration = probe_video(str(source))[1]
                item.update(rendered=True, has_audio=has_audio, duration=duration,
                            duration_difference=round(abs(duration-source_duration), 3))
                if not has_audio or abs(duration-source_duration) > 1:
                    errors.append("Rendered duration or audio does not match source")
        assert list(srt.parse((folder / "captions.srt").read_text(encoding="utf-8-sig")))
    item["errors"] = errors
    report.append(item)
    (OUT / (model_name + "-report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(source.name, item.get("captions", 0), item["seconds"], errors, flush=True)
    app.processEvents()
raise SystemExit(1 if any(r["errors"] or not r.get("captions") for r in report) else 0)
