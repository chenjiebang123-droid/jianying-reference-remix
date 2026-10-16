# Reviewed plan format

Paths in the JSON resolve relative to the plan file, or may be absolute. Each project name must be unique. Each reference should have three distinct project entries for a three-variant task. The builder does not infer semantic roles or original copy.

```json
{
  "min_speed": 0.75,
  "max_speed": 1.5,
  "projects": [
    {
      "name": "reference-name_裂变1_job-id",
      "reference": "reference-name",
      "variant": 1,
      "reference_audio": null,
      "music": null,
      "notes": "Original pt-BR copy; music still needed.",
      "shots": [
        {
          "source": "footage/complete-action.mp4",
          "role": "hook",
          "reviewed": true,
          "action_complete": true,
          "action_notes": "Hand enters, completes one wipe, then withdraws.",
          "source_start": 0,
          "source_end": 3.2,
          "target_duration": 3.2,
          "text": "Veja esta etapa da rotina."
        }
      ]
    }
  ]
}
```

Omit `source_start`/`source_end` to use the whole source file; still review the action. Omit `target_duration` for normal-speed playback. The source end must be within the media duration. Every shot requires review, action notes and a role. Use `notes` to explain substitutions and timing drift.

`reference_audio` is always muted. `music` is an optional local audio path and is placed on a separate track. Music shorter than the timeline stops at its actual end; the index flags that coverage gap. Text is editable and timed to its shot, with a small gap at boundaries to avoid rounding collisions. Confirm text layout in the editor.

For narration, add a local `narration` audio path and an optional `narration_captions` array of `{"start":0.0,"end":2.1,"text":"Spoken sentence."}`. Times are seconds from project start. Audio must fit the planned video duration; captions must be ordered, non-overlapping and within the narration. The builder uses `Narration` and `Narration_Captions` tracks. An optional `narration_disclosure` records AI-generated or supplied-recording provenance. The companion `jianying-voiceover` helper can populate these fields from measured WAV clips.
