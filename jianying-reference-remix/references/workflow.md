# Reference-led editing workflow

## Analyze

Inventory the supplied root once. Recognize `参考视频` and numbered categories such as `1.吸睛开头` through `5.促销机制`, including nested directories. Treat category names as search hints. Record each source path, duration, dimensions, frame rate and audio presence. Do not assume the library or number of references matches an earlier job.

For every reference, inspect scene-change frames plus the actual opening, meaningful action boundaries and ending. Review motion around candidate cuts rather than relying on midpoint stills alone. Document time ranges, narrative function, visible action, camera/framing, transitions, text appearance, music/voice layers, rhythm points, hook and CTA. Record mean shot length and differing structural patterns. Do not hard-code an old reference's shot-role array for new media.

The helper emits candidate scene times, per-shot PNGs, metadata and a low-confidence mixed-audio tempo estimate. Review false cuts caused by fast motion, flashes and text changes. The estimate cannot identify a song or distinguish voice rhythm from the music beat. For transcription use an available local model or the `transcribe` skill; disclose unavailable transcription and never invent dialogue.

## Match complete actions

Inspect candidate source clips at the beginning, during the action and at its finish. Reject unrelated products, incompatible actions, baked-in text that conflicts with the new copy, and mismatched results. Preserve watermarks and provenance; choose another authorized source if a marked clip is unsuitable.

Mark a source window reviewed only after checking the motion. Prefer complete naturally bounded actions. Full-file use is one option, not proof of action completeness. A shorter shot can contain one complete rub, squeeze or wipe; it need not contain an entire skincare routine. Preserve the order of product reveal, demonstration and CTA even when an exact visual substitute is missing.

Optimize variant differences after semantic suitability and action integrity. Reuse across separate drafts can be acceptable when the library is small; report the overlap. Never repeat one canonical source path within a draft. Exact duplicate content under different filenames should also be excluded when observed; hash candidate files if this is plausible.

Select duration-compatible actions first. Use restrained speed changes only if the motion remains natural. When an exact rhythm match would cut an action, choose another source, merge compatible beats or document a modest timing change. Do not force a very long take into a brief slot. The plan's `max_speed` and `min_speed` bound mechanical playback; they do not replace a visual judgment.

## Copy and audio

Write original localized copy that fits the product and source evidence. For Brazilian exfoliant projects use native pt-BR, distinguish gel/body scrub/soap, and verify spelling from the supplied product. Preserve the user's market. Avoid unsupported efficacy, ingredient, discount or medical promises and false before/after comparisons.

Separate music, narration and captions. Reference audio can be a muted review track. Provide licensed/user-supplied music when available; do not present clicks or a metronome as completed music. With no usable music, deliver a clearly marked draft requiring music completion. If no narration was generated, describe the text track as copy/captions rather than synchronized speech subtitles.

## Build and accept

Use explicit job names and preserve existing drafts. The helper builds reviewed plans through the separately installed JyProject and its draft library, maintaining integer-microsecond video boundaries. Build paths point to the original source media; moving those files requires relinking. Draft backups are editable projects, not self-contained video archives.

Verify all draft JSON files, canonical source uniqueness, source bounds, timeline continuity, audio track type, text tracks, saved projects and accessible media. Inspect representative draft frames at the hook, product reveal, demonstration and CTA. If MP4s are requested, export and check framing, text safe areas, sync, black frames, watermarks and natural motion. JSON validation alone does not prove that a draft opens correctly or looks good in the user's installed editor version.

Deliver `analysis/`, the reviewed plan, `asset-manifest.csv`, `projects-index.json`, `projects/` backups and `QA.json`. State uncompleted audio/transcription/export checks and list material substitutions.
