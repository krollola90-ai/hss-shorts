#!/usr/bin/env python3
"""Render the talking-head cut from cuts.json with FFmpeg.

usage: cut.py <raw_video> <cuts.json> <out.mp4> [--preview]

Every segment gets a ~12 ms audio fade at both edges so cuts never click. Output is
1080x1920 @ 30 fps, keyframe every frame-second (-g 30) so HyperFrames can seek it.
"""
import argparse
from pathlib import Path

from common import FPS, H, W, load_json, log, run, theme


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("cuts")
    ap.add_argument("out")
    ap.add_argument("--preview", action="store_true", help="fast low-quality encode")
    a = ap.parse_args()

    segs = load_json(a.cuts)["segments"]
    xf = theme()["cuts"]["crossfade"]
    # Scale-to-cover then centre-crop, so any phone aspect lands on exactly 1080x1920.
    fit = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
           f"setsar=1,fps={FPS}")
    parts, labels = [], []
    for k, s in enumerate(segs):
        d = s["src_end"] - s["src_start"]
        parts.append(f"[0:v]trim=start={s['src_start']}:end={s['src_end']},"
                     f"setpts=PTS-STARTPTS,{fit}[v{k}]")
        parts.append(f"[0:a]atrim=start={s['src_start']}:end={s['src_end']},"
                     f"asetpts=PTS-STARTPTS,aresample=48000,"
                     f"afade=t=in:d={xf},afade=t=out:st={max(d - xf, 0):.3f}:d={xf}[a{k}]")
        labels.append(f"[v{k}][a{k}]")
    parts.append(f"{''.join(labels)}concat=n={len(segs)}:v=1:a=1[v][a]")
    graph = Path(a.out).with_suffix(".filtergraph.txt")
    graph.write_text(";\n".join(parts), encoding="utf-8")

    q = ["-preset", "ultrafast", "-crf", "30"] if a.preview else ["-preset", "medium", "-crf", "17"]
    run(["ffmpeg", "-y", "-v", "error", "-i", a.raw,
         "-filter_complex_script", graph, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", *q, "-pix_fmt", "yuv420p", "-g", str(FPS), "-keyint_min", str(FPS),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", a.out])
    graph.unlink(missing_ok=True)
    log(f"cut -> {a.out}")


if __name__ == "__main__":
    main()
