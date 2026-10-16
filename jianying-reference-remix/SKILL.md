---
name: jianying-reference-remix
description: Analyze reference videos and match a numbered local footage library into differentiated, editable JianYing drafts, preserving complete actions and preventing repeated source files within a draft. Use for reference-led batch remixing and project delivery.
---

# JianYing Reference Remix

Turn reference videos and a categorized footage library into reviewed edit plans and editable drafts. Default to three variants per reference when the user has not specified another count.

Use [references/workflow.md](references/workflow.md) for analysis, semantic matching, music handling and acceptance. Read [references/plan-format.md](references/plan-format.md) before preparing a build plan.

## Essential decisions

- Inspect every reference's hook, shot actions, narrative order, transitions, copy layout, audio, rhythm points and CTA. Shot detection and tempo estimates are evidence aids, not semantic judgments.
- Match the function and visible action of each shot. Do not select footage merely because it belongs to the expected folder or has a convenient duration.
- Review action beginnings and endings. A complete source file may itself contain an incomplete action. Preserve a reviewed full action or choose another source; modest speed changes and documented timing drift are options, not automatic fixes.
- Use each canonical source file at most once within a draft. Prefer low overlap between variants, but do not choose unsuitable shots solely to eliminate cross-variant overlap.
- Keep product identity and creator continuity coherent. Do not manufacture a before/after result by combining different people or body areas.
- Record substitutions and unverified details. Label estimated BPM, unavailable transcripts, missing music and unrendered drafts honestly.

## Runtime

The bundled `scripts/remix.py` uses Python 3.10+, FFmpeg and FFprobe for inventory and evidence extraction. It deliberately has no OpenCV/NumPy dependency. For draft creation, install the separate `jianying-editor` skill and set `JY_SKILL_ROOT` if its location differs from `~/.codex/skills/jianying-editor`. Read that skill's current instructions before building. Its wrapper and vendored editor libraries are not included here.

Copy or adapt business-specific scripts in the user's workspace. The helper can be invoked in place with explicit paths:

```powershell
python <skill>/scripts/remix.py inventory --source-root <folder> --output <workspace>/inventory.json
python <skill>/scripts/remix.py analyze --video <reference.mp4> --output <workspace>/analysis/ref-01
python <skill>/scripts/remix.py check-plan --plan <workspace>/plan.json
python <skill>/scripts/remix.py build --plan <workspace>/plan.json --output <delivery> --draft-root <jianying-drafts>
python <skill>/scripts/remix.py verify --output <delivery>
```

Resolve the actual Python/FFmpeg installation instead of assuming the creator's machine paths. Use `--ffmpeg` and `--ffprobe` when needed. Do not install or upgrade global dependencies merely to run a job.

## Delivery

Deliver a per-reference analysis, reviewed shot plan, original copy, source manifest, project index, draft backups and QA results. Keep the source media unchanged. Identify draft-only delivery separately from exported and visually checked MP4s. Existing output names are rejected by the builder; choose a new job/output name for another run.
