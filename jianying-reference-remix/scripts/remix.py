"""Portable reference evidence and reviewed-plan JianYing builder (stdlib only)."""
from __future__ import annotations

import argparse
import csv
import html
import importlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def run(args: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(args, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-2000:])
    return result


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def probe(path: Path, ffprobe: str) -> dict:
    data = json.loads(run([ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]).stdout)
    videos = [x for x in data["streams"] if x["codec_type"] == "video"]
    video = videos[0] if videos else {}
    rate = video.get("avg_frame_rate", "0/1").split("/")
    fps = float(rate[0]) / max(float(rate[1]), 1) if len(rate) == 2 else float(rate[0])
    return {"path": str(path.resolve()), "duration": float(data.get("format", {}).get("duration", 0)),
            "width": video.get("width"), "height": video.get("height"), "fps": fps,
            "audio_present": any(x["codec_type"] == "audio" for x in data["streams"])}


def inventory(root: Path, output: Path, ffprobe: str) -> None:
    folders = [p for p in root.iterdir() if p.is_dir() and (p.name == "参考视频" or re.match(r"^[1-5](?:[.、 _-]|$)", p.name))]
    records = []
    for folder in sorted(folders):
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.suffix.lower() in VIDEO_EXTS:
                try:
                    records.append({"category": folder.name, "status": "success", **probe(path, ffprobe)})
                except (RuntimeError, ValueError) as exc:
                    records.append({"category": folder.name, "path": str(path), "status": "failed", "error": str(exc)})
    dump(output, {"source_root": str(root.resolve()), "files": records})


def tempo(path: Path, ffmpeg: str) -> dict:
    raw = run([ffmpeg, "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"]).stdout
    samples = [s[0] for s in struct.iter_unpack("<h", raw[:len(raw) // 2 * 2])]
    hop = 160
    energy = [math.sqrt(sum(x*x for x in samples[i:i+hop]) / hop) for i in range(0, len(samples)-hop, hop)]
    onset = [max(0.0, energy[i]-energy[i-1]) for i in range(1, len(energy))]
    if len(onset) < 100 or not any(onset):
        return {"estimated_bpm": None, "confidence": 0, "note": "Insufficient audio evidence"}
    mean = sum(onset) / len(onset)
    centered = [x-mean for x in onset]
    base = sum(x*x for x in centered) or 1
    scores = [(sum(centered[i]*centered[i-lag] for i in range(lag, len(centered))), lag) for lag in range(15, min(51, len(centered)))]
    score, lag = max(scores)
    return {"estimated_bpm": round(3000 / lag, 2), "confidence": round(score/base, 3),
            "note": "Low-confidence mixed-audio estimate; review half/double tempo and voice interference"}


def analyze(video: Path, output: Path, ffmpeg: str, ffprobe: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    meta = probe(video, ffprobe)
    result = run([ffmpeg, "-hide_banner", "-i", str(video), "-vf", "scale=180:-2,select='gt(scene,0.32)',showinfo", "-an", "-f", "null", "-"])
    times = sorted(set(float(x) for x in re.findall(r"pts_time:([0-9.]+)", result.stderr.decode("utf-8", "replace"))))
    cuts = []
    for t in times:
        if 0.2 < t < meta["duration"]-0.2 and (not cuts or t-cuts[-1] > 0.3):
            cuts.append(t)
    bounds = [0.0] + cuts + [meta["duration"]]
    shots, cards = [], []
    for i, (start, end) in enumerate(zip(bounds, bounds[1:]), 1):
        frame = output / f"shot-{i:03d}.png"
        run([ffmpeg, "-y", "-v", "error", "-ss", str((start+end)/2), "-i", str(video), "-frames:v", "1", "-vf", "scale=360:-2", str(frame)])
        shots.append({"start": start, "end": end, "candidate_frame": frame.name, "role": None, "reviewed": False})
        cards.append(f'<figure><img src="{html.escape(frame.name)}"><figcaption>{i}: {start:.2f}–{end:.2f}s</figcaption></figure>')
    audio = tempo(video, ffmpeg) if meta["audio_present"] else {"estimated_bpm": None, "note": "No audio"}
    dump(output / "evidence.json", {**meta, "shots": shots, "average_shot_duration": meta["duration"]/max(1, len(shots)), "audio": audio,
                                    "limitations": ["Candidate boundaries and midpoint images require motion review", "No speech transcript or song identification"]})
    (output / "index.html").write_text('<meta charset="utf-8"><title>Candidate shots</title><style>body{display:flex;flex-wrap:wrap}img{width:220px}figure{margin:8px}</style>'+"".join(cards), encoding="utf-8")


def resolve(base: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def load_plan(path: Path, ffprobe: str, probe_fn=None) -> tuple[dict, list[dict]]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    media_probe = probe_fn or (lambda p: probe(p, ffprobe))
    cache, prepared, names = {}, [], set()
    low, high = float(plan.get("min_speed", 0.75)), float(plan.get("max_speed", 1.5))
    if not 0 < low <= high:
        raise ValueError("Invalid speed bounds")
    for project in plan.get("projects", []):
        name = project["name"]
        if not name or name in {".", ".."} or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith((".", " ")) or name.casefold() in names:
            raise ValueError(f"Unsafe or duplicate project name: {name}")
        if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", name, re.I):
            raise ValueError(f"Reserved project name: {name}")
        names.add(name.casefold())
        seen, shots, cursor = set(), [], 0
        for shot in project.get("shots", []):
            if shot.get("reviewed") is not True or shot.get("action_complete") is not True or not shot.get("action_notes") or not shot.get("role"):
                raise ValueError("Every shot requires semantic/action review, notes and role")
            source = resolve(path.parent, shot["source"])
            key = str(source).casefold()
            if not source.is_file() or key in seen:
                raise ValueError(f"Missing or repeated source in {name}: {source}")
            seen.add(key)
            if key not in cache:
                cache[key] = media_probe(source)
            duration = cache[key]["duration"]
            start, end = float(shot.get("source_start", 0)), float(shot.get("source_end", duration))
            target = float(shot.get("target_duration", end-start))
            if not all(math.isfinite(x) for x in (start, end, target)) or not 0 <= start < end <= duration+0.000001 or target <= 0:
                raise ValueError(f"Invalid source window or target: {source}")
            speed = (end-start)/target
            if not low-1e-6 <= speed <= high+1e-6:
                raise ValueError(f"Speed {speed:.2f} outside plan bounds for {source}; choose another action or revise timing")
            length_us = round(target*1e6)
            if length_us < 1:
                raise ValueError("Target duration rounds to zero")
            shots.append({**shot, "source": str(source), "source_start": start, "source_end": end,
                          "target_start_us": cursor, "target_duration_us": length_us, "speed": speed})
            cursor += length_us
        if not shots:
            raise ValueError(f"Project {name} has no shots")
        prepared.append({**project, "shots": shots, "duration_us": cursor})
    if not prepared:
        raise ValueError("Plan has no projects")
    return plan, prepared


def editor():
    root = Path(os.environ.get("JY_SKILL_ROOT", "")).expanduser() if os.environ.get("JY_SKILL_ROOT") else Path.home()/".codex"/"skills"/"jianying-editor"
    if not (root/"scripts"/"jy_wrapper.py").is_file():
        raise RuntimeError("Install jianying-editor separately and set JY_SKILL_ROOT")
    sys.path[:0] = [str(root/"scripts"), str(root/"scripts"/"vendor")]
    module = importlib.import_module("jy_wrapper")
    return module.JyProject, importlib.import_module("pyJianYingDraft")


def build(plan_path: Path, output: Path, draft_root: Path, ffprobe: str) -> None:
    _, projects = load_plan(plan_path, ffprobe)
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    for item in projects:
        if (draft_root/item["name"]).exists():
            raise FileExistsError(f"Existing draft: {item['name']}")
    JyProject, draft = editor()
    output.mkdir(parents=True)
    shutil.copy2(plan_path, output/"reviewed-plan.json")
    records, manifest = [], []
    for item in projects:
        project = JyProject(item["name"], width=1080, height=1920, drafts_root=str(draft_root), overwrite=False)
        project._ensure_track(draft.TrackType.video, "VideoTrack")
        for shot in item["shots"]:
            mat = draft.VideoMaterial(shot["source"])
            start_us, end_us = round(shot["source_start"]*1e6), round(shot["source_end"]*1e6)
            if end_us > mat.duration:
                if end_us-mat.duration > 2000:
                    raise ValueError("FFprobe and editor disagree on source duration")
                end_us = mat.duration
            seg = draft.VideoSegment(mat, draft.trange(shot["target_start_us"], shot["target_duration_us"]),
                                     source_timerange=draft.trange(start_us, end_us-start_us), volume=0.0)
            project.script.add_segment(seg, "VideoTrack")
            if shot.get("text"):
                project.add_text_simple(shot["text"], start_time=f"{shot['target_start_us']/1e6}s",
                                        duration=f"{max(1,shot['target_duration_us']-12000)/1e6}s", track_name="Copy",
                                        clip_settings=draft.ClipSettings(transform_y=-0.7))
            manifest.append({"project": item["name"], "role": shot["role"], "source": shot["source"],
                             "source_start": start_us/1e6, "source_end": end_us/1e6,
                             "target_start": shot["target_start_us"]/1e6, "target_duration": shot["target_duration_us"]/1e6,
                             "speed": seg.speed.speed, "action_notes": shot["action_notes"]})
        audio_coverage = {}
        for field, track, volume in [("reference_audio", "Reference_Audio", 0.0), ("music", "Music", 0.6)]:
            if item.get(field):
                path = resolve(plan_path.parent, item[field])
                length = min(probe(path, ffprobe)["duration"], item["duration_us"]/1e6)
                audio = project.add_audio_safe(str(path), start_time="0s", duration=f"{length}s", track_name=track)
                if audio is None:
                    raise RuntimeError(f"Audio import failed: {path}")
                audio.volume = volume
                audio_coverage[field] = length
        result = project.save()
        folder = Path(result["draft_path"])
        shutil.copytree(folder, output/"projects"/item["name"])
        records.append({"name": item["name"], "reference": item.get("reference"), "variant": item.get("variant"),
                        "draft_path": str(folder), "duration": item["duration_us"]/1e6, "notes": item.get("notes", ""),
                        "audio_coverage": audio_coverage, "music_complete": audio_coverage.get("music",0)+0.01 >= item["duration_us"]/1e6,
                        "mp4_exported": False, "editor_open_tested": False})
        dump(output/"projects-index.json", records)
    with (output/"asset-manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(manifest)
    verify(output)


def verify(output: Path) -> dict:
    records = json.loads((output/"projects-index.json").read_text(encoding="utf-8"))
    requested = json.loads((output/"reviewed-plan.json").read_text(encoding="utf-8"))
    expected = {p["name"] for p in requested["projects"]}
    missing_projects = sorted(expected - {r["name"] for r in records})
    results = []
    for record in records:
        folder = output/"projects"/record["name"]
        source = next((folder/n for n in ("draft_info.json", "draft_content.json") if (folder/n).is_file()), None)
        issues, seen, cursor, count = [], set(), 0, 0
        if source is None:
            issues.append("missing_draft_json")
        else:
            data = json.loads(source.read_text(encoding="utf-8"))
            materials = {x["id"]:x for x in data.get("materials",{}).get("videos",[])}
            clips = [s for t in data.get("tracks",[]) if t.get("type")=="video" for s in t.get("segments",[])]
            for clip in sorted(clips, key=lambda s:s["target_timerange"]["start"]):
                count += 1
                material = materials.get(clip["material_id"], {})
                path = Path(material.get("path", ""))
                key = str(path.resolve()).casefold()
                if not path.is_file(): issues.append("missing_source")
                if key in seen: issues.append("repeated_source")
                seen.add(key)
                target, window = clip["target_timerange"], clip.get("source_timerange",{})
                if target["start"] != cursor: issues.append("timeline_gap_or_overlap")
                cursor = target["start"]+target["duration"]
                if window.get("start",-1)<0 or window.get("duration",0)<=0: issues.append("invalid_source_window")
                media_duration = material.get("duration")
                if media_duration and window.get("start",0)+window.get("duration",0)>media_duration+2000: issues.append("source_window_out_of_bounds")
            if not clips: issues.append("no_video")
        results.append({"name":record["name"],"video_segments":count,"issues":issues})
    result = {"ok":bool(results) and not missing_projects and all(not x["issues"] for x in results), "projects":results,
              "missing_projects": missing_projects,
              "limitations":["Structure-only validation; review action completeness, editor opening, audio and final visuals separately"]}
    dump(output/"QA.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inventory", "analyze", "check-plan", "build", "verify"):
        command = sub.add_parser(name)
        if name in ("inventory", "analyze", "build", "verify"): command.add_argument("--output", type=Path, required=True)
        if name in ("inventory", "analyze", "check-plan", "build"): command.add_argument("--ffprobe", default="ffprobe")
        if name=="inventory": command.add_argument("--source-root", type=Path, required=True)
        if name=="analyze":
            command.add_argument("--video", type=Path, required=True)
            command.add_argument("--ffmpeg", default="ffmpeg")
        if name in ("check-plan", "build"): command.add_argument("--plan", type=Path, required=True)
        if name=="build": command.add_argument("--draft-root", type=Path, required=True)
    args = parser.parse_args()
    if args.command=="inventory": inventory(args.source_root, args.output, args.ffprobe)
    elif args.command=="analyze": analyze(args.video, args.output, args.ffmpeg, args.ffprobe)
    elif args.command=="check-plan":
        _, projects = load_plan(args.plan, args.ffprobe)
        print(json.dumps({"ok":True,"projects":len(projects)}))
    elif args.command=="build": build(args.plan, args.output, args.draft_root, args.ffprobe)
    else:
        result = verify(args.output)
        print(json.dumps(result, ensure_ascii=False))
        if not result["ok"]: raise SystemExit(1)


if __name__ == "__main__":
    main()
