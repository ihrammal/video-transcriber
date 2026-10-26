"""Local transcription comparison; does not send recordings to any service.

Qwen dependencies must be installed in .model-eval-deps, separate from the app.
No word-error score is calculated without a human reference transcript.
"""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".model-eval-deps"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import torch
from qwen_asr import Qwen3ASRModel

torch.set_num_threads(4)
print("Loading Qwen3-ASR 0.6B on CPU", flush=True)
started = time.monotonic()
model = Qwen3ASRModel.from_pretrained(
    str(ROOT / "models" / "qwen3-asr-0.6b"),
    dtype=torch.float32, device_map="cpu", max_new_tokens=512,
    max_inference_batch_size=1,
)
print("Loaded in %.1f seconds" % (time.monotonic()-started), flush=True)
report = []
for source in sorted((ROOT / "test audio-video").iterdir()):
    folder = ROOT / "test-results" / "base" / source.stem
    audio = folder / "transcribe.wav"
    if not audio.exists():
        # Use the app's already extracted audio; the renderer's temporary
        # compressed track is also a faithful local input if needed.
        audio = folder / "audio.wav"
    if not audio.exists():
        continue
    start = time.monotonic()
    result = model.transcribe(audio=str(audio), language=None)[0]
    item = {"source": source.name, "model": "Qwen3-ASR-0.6B", "seconds": round(time.monotonic()-start, 2),
            "language": result.language, "text": result.text, "timestamps_tested": False}
    report.append(item)
    (ROOT / "test-results" / "qwen-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(source.name, item["seconds"], result.language, flush=True)
print("Completed", len(report), "recordings", flush=True)
