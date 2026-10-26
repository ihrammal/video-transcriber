# Local transcription evaluation — 24 October 2026

Keep faster-whisper as the default offline engine for 1.3.1. Qwen3-ASR is a viable
alternative worth further testing, but the available results do not establish an
accuracy improvement for these Arabic and mixed Arabic/English recordings.

The continuation re-ran Base and Qwen on the same nine MP3/MP4 recordings.
Small's results are from the earlier local run:

| Model | Recordings | Total reported transcription time | Median per recording |
| --- | ---: | ---: | ---: |
| Whisper Base (re-run) | 9 | 50.68 seconds | 5.32 seconds |
| Whisper Small | 9 | 153.82 seconds | 14.01 seconds |
| Qwen3-ASR 0.6B (re-run) | 9 | 262.63 seconds | 29.02 seconds |

These figures describe saved local runs, not a controlled benchmark. The re-runs
overlapped with other validation/build work. Qwen ran on CPU in float32 with four threads; Whisper used int8.
Model initialization, warm-up and hardware effects are not normalized. The
Whisper validation also exercises extraction and subtitle export. Do not infer
a universal speed or accuracy ranking from these numbers.

All three produced transcripts. Some Qwen output contains obvious mixed-script
artifacts. There are no human-corrected reference transcripts, so no word-error
rate or character-error rate is claimed. Qwen timestamps and forced alignment
were not tested. Base's re-run verifies nine captioned videos with audio preserved
and duration differences within one second. All nine completed without reported errors.

The optional Qwen evaluation dependencies remain outside the application's
runtime. User recordings were processed locally. No paid API comparison was
performed and no recordings were uploaded for this evaluation.

## Follow-up comparison

Prepare human-reviewed Arabic and English references, then compare normalized
word/character error rates, mixed-language handling, subtitle timing, silence
hallucinations, memory use and speed on identical hardware. Include Whisper
Large-v3/Turbo and Qwen 1.7B before changing the default. Cloud candidates need
separate checks for timestamp output and provider limits.

Qwen's own model card documents Arabic and English support:
https://huggingface.co/Qwen/Qwen3-ASR-0.6B

Raw local evidence, excluded from version control: test-results/base-report.json,
test-results/small-report.json and test-results/qwen-report.json. Re-run the
Whisper pipeline with tests/run_media_validation.py and the Qwen experiment
with tests/compare_local_models.py when its separate dependencies are available.
