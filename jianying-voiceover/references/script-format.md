# Approved narration script

```json
{
  "language": "pt-BR",
  "voice": "cedar",
  "speed": 1.0,
  "instructions": "Tone: clear and friendly. Pacing: steady.",
  "segments": [
    {"text": "Veja esta etapa da rotina.", "target_duration": 3.5, "pause_after": 0.15},
    {"text": "Confira os detalhes do produto.", "pause_after": 0}
  ]
}
```

`language` controls delivery instructions, not translation. `voice` defaults to cedar and must be a built-in voice supported by the installed speech CLI. `model` is optional: when absent the current speech CLI default is used. `speed` defaults to 1.0 (valid API range 0.25–4.0); choose natural pacing for the actual content. `instructions` add delivery guidance without rewriting the text.

Every `text` must contain 1–4096 characters after surrounding whitespace is removed. `target_duration` is an optional total slot budget including `pause_after`; it does not force a speaking duration. If audio plus pause is shorter than the budget the remainder is silence. If it is longer, preserve it and flag `overflow_seconds`. Later segment starts follow actual slot ends. `pause_after` defaults to 0.12 seconds and must be nonnegative.

`voiceover.json` has `status: complete` only when measured audio was assembled. Its `captions` contain start/end seconds for each complete audio segment, excluding the added pause and padding. `requires_timing_review` marks budget overflow. `listening_reviewed` defaults to false. Synthetic timing tests or dry runs do not imply real voice generation or listening review.

The `attach` command adds `narration`, `narration_captions` and `narration_disclosure` to exactly one named remix project. It resolves existing shot/audio paths relative to the original plan so the new plan can live elsewhere. It refuses an overlong narration; revise the edit/text explicitly.
