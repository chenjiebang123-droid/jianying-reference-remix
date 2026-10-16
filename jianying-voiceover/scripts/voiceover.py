"""Measured narration assembly and speech-skill batch adapter; stdlib only."""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

LANGUAGES = {"pt-BR": "Brazilian Portuguese (pt-BR)", "zh-CN": "Mandarin Chinese (Simplified Chinese text)", "en-US": "American English"}


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def number(value, label: str, minimum=0) -> float:
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValueError(f"Invalid {label}")
    return result


def load_script(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    language = str(data.get("language", "")).strip()
    if not language:
        raise ValueError("Specify the spoken language")
    speed = number(data.get("speed", 1), "speed", 0.25)
    if speed > 4:
        raise ValueError("Speed must be between 0.25 and 4")
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("Script requires segments")
    for segment in segments:
        text = segment.get("text")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4096:
            raise ValueError("Each text must contain 1–4096 characters")
        segment["text"] = text.strip()
        segment["pause_after"] = number(segment.get("pause_after", 0.12), "pause_after")
        if "target_duration" in segment:
            segment["target_duration"] = number(segment["target_duration"], "target_duration", 0.001)
    return {**data, "language": language, "speed": speed, "voice": data.get("voice", "cedar")}


def instruction(data: dict) -> str:
    language = LANGUAGES.get(data["language"], data["language"])
    return f"Language: {language}.\n" + data.get("instructions", "Tone: clear and neutral. Pacing: natural.")


def new_output(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Choose a new output directory: {path}")
    path.mkdir(parents=True)


def timestamp(seconds: float) -> str:
    ms = round(seconds*1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def assemble(data: dict, clips: Path, output: Path) -> dict:
    paths = [clips/f"segment-{i:03d}.wav" for i in range(1, len(data["segments"])+1)]
    parameters = None
    # Preflight all WAVs before producing the combined file.
    for path in paths:
        with wave.open(str(path), "rb") as audio:
            current = (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype())
            if current[3] != "NONE" or current[1] not in (1, 2, 3, 4) or audio.getnframes() <= 0:
                raise ValueError(f"Expected nonempty PCM WAV: {path}")
            if parameters is not None and current != parameters:
                raise ValueError("All source WAV clips must have matching PCM parameters")
            parameters = current
    output.mkdir(parents=True, exist_ok=True)
    for name in ("narration.wav", "narration.srt", "voiceover.json"):
        if (output/name).exists():
            raise FileExistsError(f"Output exists: {output/name}")
    channels, width, rate, _ = parameters
    frame_size = channels*width
    captions, timings, cursor, subtitles = [], [], 0, []
    with wave.open(str(output/"narration.wav"), "wb") as combined:
        combined.setnchannels(channels)
        combined.setsampwidth(width)
        combined.setframerate(rate)
        for i, (segment, path) in enumerate(zip(data["segments"], paths), 1):
            with wave.open(str(path), "rb") as clip:
                frames = clip.getnframes()
                pcm = clip.readframes(frames)
            if len(pcm) != frames*frame_size:
                raise ValueError(f"Truncated PCM data: {path}")
            pause = round(segment["pause_after"]*rate)
            budget = round(segment.get("target_duration", 0)*rate)
            slot = max(frames+pause, budget)
            start, end = cursor/rate, (cursor+frames)/rate
            combined.writeframesraw(pcm)
            # Eight-bit PCM is unsigned; other PCM widths are signed.
            silence = (b"\x80" if width == 1 else b"\x00"*width)*channels
            remaining = slot-frames
            while remaining:
                amount = min(remaining, rate)
                combined.writeframesraw(silence*amount)
                remaining -= amount
            overflow = max(0, frames+pause-budget)/rate if budget else 0.0
            captions.append({"start":start, "end":end, "text":segment["text"]})
            timings.append({"segment":i, "source":str(path.resolve()), "start":start, "speech_end":end,
                            "slot_end":(cursor+slot)/rate, "overflow_seconds":overflow})
            subtitles.append(f"{i}\n{timestamp(start)} --> {timestamp(end)}\n{segment['text']}\n")
            cursor += slot
    (output/"narration.srt").write_text("\n".join(subtitles), encoding="utf-8")
    result = {"status":"complete", "narration":str((output/"narration.wav").resolve()),
              "subtitles":str((output/"narration.srt").resolve()), "duration":cursor/rate,
              "captions":captions, "segments":timings, "language":data["language"],
              "voice":data.get("voice"), "speed":data["speed"], "instructions":instruction(data),
              "requires_timing_review":any(x["overflow_seconds"] > 0 for x in timings),
              "listening_reviewed":False, "caption_alignment":"measured complete segments, not word-level"}
    dump(output/"voiceover.json", result)
    dump(output/"approved-script.json", data)
    return result


def generate(script: Path, output: Path, speech_root: Path, dry_run: bool) -> dict:
    data = load_script(script)
    cli = speech_root/"scripts/text_to_speech.py"
    if not cli.is_file():
        raise FileNotFoundError("Install the speech skill or set SPEECH_SKILL_ROOT")
    if not dry_run and not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Configure it locally; do not paste it in chat.")
    new_output(output)
    clips = output/"clips"
    clips.mkdir()
    jobs = []
    for i, segment in enumerate(data["segments"], 1):
        job = {"input":segment["text"], "voice":data["voice"], "speed":data["speed"],
               "instructions":instruction(data), "response_format":"wav", "out":f"segment-{i:03d}.wav"}
        if data.get("model"):
            job["model"] = data["model"]
        jobs.append(job)
    dump(output/"request-plan.json", {"status":"planned", "language":data["language"], "jobs":jobs})
    # This is a temporary batch manifest for the installed speech CLI only.
    with tempfile.TemporaryDirectory(prefix="speech-jobs-") as temp:
        batch = Path(temp)/"jobs.jsonl"
        batch.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in jobs), encoding="utf-8")
        command = [sys.executable, str(cli), "speak-batch", "--input", str(batch), "--out-dir", str(clips.resolve()), "--rpm", "50"]
        if dry_run:
            command.append("--dry-run")
        subprocess.run(command, check=True)
    if dry_run:
        return {"status":"planned", "audio_generated":False, "output":str(output)}
    result = assemble(data, clips, output)
    result["ai_generated"] = True
    dump(output/"voiceover.json", result)
    return result


def attach(plan_path: Path, name: str, voiceover_path: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Plan output exists: {output}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    voice = json.loads(voiceover_path.read_text(encoding="utf-8"))
    if voice.get("status") != "complete" or voice.get("requires_timing_review"):
        raise ValueError("Narration must be assembled and have no unresolved timing overflow")
    matches = [p for p in plan.get("projects",[]) if p["name"] == name]
    if len(matches) != 1:
        raise ValueError("Project name must identify exactly one project")
    project = matches[0]
    if project.get("narration") or project.get("narration_captions"):
        raise ValueError("Project already has narration; preserve it and create a deliberate replacement plan")
    total = 0
    for shot in project["shots"]:
        if "target_duration" not in shot:
            if "source_end" not in shot:
                raise ValueError("Specify target_duration or source_end for every shot before attaching narration")
            length = float(shot["source_end"])-float(shot.get("source_start",0))
        else:
            length = float(shot["target_duration"])
        if not math.isfinite(length) or length <= 0:
            raise ValueError("Invalid planned shot duration")
        total += round(length*1e6)
    if number(voice["duration"], "narration duration",0.001) > total/1e6+0.001:
        raise ValueError("Narration exceeds planned video duration; revise the script or reviewed edit")
    narration = Path(voice["narration"])
    narration = narration if narration.is_absolute() else voiceover_path.parent/narration
    if not narration.is_file():
        raise FileNotFoundError(narration)
    # A relocated plan must preserve every original source/audio path.
    plan = copy.deepcopy(plan)
    for item in plan["projects"]:
        for shot in item["shots"]:
            path = Path(shot["source"])
            shot["source"] = str((path if path.is_absolute() else plan_path.parent/path).resolve())
        for field in ("reference_audio", "music", "narration"):
            if item.get(field):
                path = Path(item[field])
                item[field] = str((path if path.is_absolute() else plan_path.parent/path).resolve())
        if item["name"] == name:
            item["narration"] = str(narration.resolve())
            item["narration_captions"] = voice["captions"]
            item["narration_disclosure"] = "AI-generated voice" if voice.get("ai_generated") else "User-supplied recording"
    dump(output, plan)
    return {"status":"attached", "project":name, "output":str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "assemble"):
        part = sub.add_parser(command)
        part.add_argument("--script", type=Path, required=True)
        part.add_argument("--output", type=Path, required=True)
        if command == "generate":
            part.add_argument("--dry-run", action="store_true")
            part.add_argument("--speech-root", type=Path, default=Path(os.environ.get("SPEECH_SKILL_ROOT", str(Path.home()/".codex/skills/speech"))))
        else:
            part.add_argument("--audio-dir", type=Path, required=True)
    part = sub.add_parser("attach")
    part.add_argument("--plan", type=Path, required=True)
    part.add_argument("--project", required=True)
    part.add_argument("--voiceover", type=Path, required=True)
    part.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "generate":
        result = generate(args.script, args.output, args.speech_root, args.dry_run)
    elif args.command == "assemble":
        data = load_script(args.script)
        new_output(args.output)
        result = assemble(data, args.audio_dir, args.output)
    else:
        result = attach(args.plan, args.project, args.voiceover, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
