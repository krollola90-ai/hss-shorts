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
    # One short encode per segment (input-seeked), then a stream-copy concat. Memory stays
    # flat however many segments there are; the trim+concat filtergraph buffered every
    # segment of a long 4K source and got OOM-killed.
    q = ["-preset", "ultrafast", "-crf", "30"] if a.preview else ["-preset", "medium", "-crf", "17"]
    tmp = Path(a.out).with_suffix(".parts")
    tmp.mkdir(exist_ok=True)
    files = []
    for k, s in enumerate(segs):
        d = s["src_end"] - s["src_start"]
        f = tmp / f"p{k:03d}.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{s['src_start']:.3f}", "-i", a.raw, "-t", f"{d:.3f}",
             "-vf", fit, "-af", f"aresample=48000,afade=t=in:d={xf},afade=t=out:st={max(d - xf, 0):.3f}:d={xf}",
             "-c:v", "libx264", *q, "-pix_fmt", "yuv420p", "-g", str(FPS), "-keyint_min", str(FPS),
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", f])
        files.append(f)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{f.name}'\n" for f in files))
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-c", "copy", "-movflags", "+faststart", a.out])
    for f in files:
        f.unlink()
    lst.unlink()
    tmp.rmdir()
    log(f"cut -> {a.out}")


if __name__ == "__main__":
    main()
