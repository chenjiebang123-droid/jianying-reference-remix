---
name: jianying-voiceover
description: Generate multilingual video narration from approved text, assemble measured audio and segment-timed subtitles, and attach the result to an editable JianYing remix plan. Use for product-video voiceovers and batch narration; supports built-in voices and supplied recordings.
---

# JianYing Voiceover

Create narration from the user's approved script and connect it to the editing workflow. Preserve the exact input text. Use the `speech` skill for built-in-voice synthesis; read its current instructions and CLI reference before live generation. No custom voice creation or imitation is implemented.

## Inputs and decisions

Collect the spoken language, approved text, voice/delivery preference and any video timing budget. Default to `cedar`, normal speed and neutral, clear delivery. The helper includes language instructions for `zh-CN`, `pt-BR` and `en-US`; other languages can be specified explicitly. Do not silently translate the script. For Brazil use native Brazilian Portuguese, and check product-name pronunciation.

Use [references/script-format.md](references/script-format.md) for the JSON contract. One segment should be one coherent sentence or short speaking turn; split text over 4096 characters before synthesis. Budget segment durations from the actual edit when one exists. Generated durations are not guaranteed by a text length estimate or a delivery instruction.

## Generate and measure

The helper calls the installed `speech/scripts/text_to_speech.py` batch CLI once, requesting WAV files. It does not modify or distribute that CLI. Set `SPEECH_SKILL_ROOT` if it differs from `~/.codex/skills/speech`. Python's `openai` package and `OPENAI_API_KEY` are required only for live synthesis. If the key is absent, complete dry-run preparation and explain how to set it locally; never ask the user to paste it into chat.

```powershell
python <skill>/scripts/voiceover.py generate --script <script.json> --output <new-output> --dry-run
python <skill>/scripts/voiceover.py generate --script <script.json> --output <new-output>
```

For supplied recordings, put compatible PCM WAV clips named `segment-001.wav`, `segment-002.wav`, etc. in a directory and use:

```powershell
python <skill>/scripts/voiceover.py assemble --script <script.json> --audio-dir <clips> --output <new-output>
```

Duration measurement uses actual PCM sample frames. The helper stitches clips, adds requested pauses, pads short budget slots with silence and preserves overlong speech in full. It flags overflow for revision rather than truncating speech. SRT boundaries follow each complete generated segment; these are segment-timed captions, not word-level forced alignment. Check audible leading/trailing silence before claiming speech-level alignment.

## Connect to JianYing

Read `jianying-reference-remix` when attaching to its plans. Use its current builder, which accepts separate narration and narration-caption tracks:

```powershell
python <skill>/scripts/voiceover.py attach --plan <plan.json> --project <exact-project-name> --voiceover <output>/voiceover.json --out <new-plan.json>
```

Attachment preserves existing plan paths by resolving them before saving at a new location. It refuses to replace existing narration or exceed the video's planned length. Resolve flagged timing overflow with an approved script revision, a natural delivery adjustment or a longer reviewed edit. Do not cut words or speed the voice unnaturally to force a fit. Build the new plan through the remix skill; narration is separate from music and the muted reference track.

## Deliver and review

Deliver `narration.wav`, `narration.srt`, the exact approved script and `voiceover.json` with measured timing, settings and overflow flags. For dry runs deliver the request plan only and say no audio has been synthesized. Clearly disclose that generated voices are AI-generated. Listen for pronunciation, clipping, pauses, pace and final-caption timing; file validation alone does not verify audible quality. When no listening facility is available, state that listening review remains outstanding.
