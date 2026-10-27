#!/usr/bin/env python3
"""Master loudness and run the quality gate on a rendered short.

usage: finalize.py <rendered.mp4> <final.mp4> [--qc qc.json]

- Two-pass EBU R128 loudnorm to theme.audio.voice_lufs (-14 LUFS, TP -1 dB): platform target.
- QC (fails with exit 2): duration <= 120 s, 1080x1920, 30 fps, audio present,
  |audio - video duration| < 0.1 s, no black frames > 0.25 s, no frozen video > 1.5 s
  (outside full-screen B-roll, see notes), no silence > 1.2 s.
"""
import argparse
import json
import re
import sys

from common import FPS, H, MAX_DURATION, W, ffprobe, log, run, save_json, theme


def loudnorm(src, dst, lufs, tp):
    r = run(["ffmpeg", "-hide_banner", "-i", src, "-af",
             f"loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
            capture=True)
    m = json.loads(re.findall(r"\{[^{}]+\}", r.stderr, re.S)[-1])
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}:linear=true")
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-c:v", "copy", "-af", af,
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", dst])


def detect(path, vf=None, af=None):
    args = ["ffmpeg", "-hide_banner", "-i", path]
    args += ["-vf", vf, "-an"] if vf else ["-af", af, "-vn"]
    return run(args + ["-f", "null", "-"], capture=True, quiet=True).stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--qc")
    a = ap.parse_args()
    au = theme()["audio"]
    loudnorm(a.src, a.dst, au["voice_lufs"], au["true_peak"])

    info = ffprobe(a.dst)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    aud = [s for s in info["streams"] if s["codec_type"] == "audio"]
    dur = float(info["format"]["duration"])
    fps = eval(v["r_frame_rate"])  # "30/1"
    issues = []
    if dur > MAX_DURATION:
        issues.append(f"duration {dur:.2f}s > {MAX_DURATION}s")
    if (v["width"], v["height"]) != (W, H):
        issues.append(f"resolution {v['width']}x{v['height']}")
    if abs(fps - FPS) > 0.01:
        issues.append(f"fps {fps}")
    if not aud:
        issues.append("no audio stream")
    else:
        ad, vd = float(aud[0].get("duration", dur)), float(v.get("duration", dur))
        if abs(ad - vd) > 0.1:
            issues.append(f"audio/video length mismatch {ad:.3f} vs {vd:.3f}")

    black = re.findall(r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)",
                       detect(a.dst, vf="blackdetect=d=0.25:pix_th=0.08"))
    freeze = re.findall(r"freeze_start: ([\d.]+)", detect(a.dst, vf="freezedetect=n=0.002:d=1.5"))
    silence = re.findall(r"silence_start: ([\d.]+)", detect(a.dst, af="silencedetect=n=-45dB:d=1.2"))
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", detect(a.dst, af="ebur128"))
    for b in black:
        issues.append(f"black frames {b[0]}-{b[1]}s")
    for f in freeze:
        issues.append(f"frozen video from {f}s (ok only if it is a still B-roll shot)")
    for s in silence:
        issues.append(f"silence > 1.2s from {s}s")

    report = {"file": a.dst, "duration": round(dur, 3), "fps": fps,
              "resolution": f"{v['width']}x{v['height']}",
              "integrated_lufs": float(lufs[-1]) if lufs else None,
              "issues": issues, "pass": not issues}
    if a.qc:
        save_json(a.qc, report)
    print(json.dumps(report, indent=2))
    sys.exit(0 if not issues else 2)


if __name__ == "__main__":
    main()
