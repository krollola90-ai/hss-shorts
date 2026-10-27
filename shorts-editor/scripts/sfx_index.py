#!/usr/bin/env python3
"""(Re)build sfx/manifest.json from the files under sfx/<category>/.

usage: sfx_index.py [--normalize]

For each sound it measures duration and the "hit" (the moment it peaks, via
`hyperframes audio`) so cues can be placed so the hit lands exactly on the event:
audio start = event_time - hit. Existing metadata (license, source, approved, notes)
is preserved; new files enter as approved=false until the person signs off.
--normalize peak-normalizes new files to -1 dBFS (in place) before measuring.
"""
import json
import subprocess
import sys
from pathlib import Path

from common import SFX_DIR, duration, load_json, log, run, save_json

AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}


def hit_time(path):
    r = subprocess.run(["hyperframes", "audio", str(path), "--json"], capture_output=True, text=True)
    try:
        item = json.loads(r.stdout)["items"][0]
        m = item.get("moments") or {}
        return float(m.get("peak") if m.get("peak") is not None else m.get("onset") or 0.0)
    except Exception:
        return 0.0


def main():
    normalize = "--normalize" in sys.argv
    mpath = SFX_DIR / "manifest.json"
    old = load_json(mpath) if mpath.exists() else {}
    new = {}
    for f in sorted(SFX_DIR.glob("*/*")):
        if f.suffix.lower() not in AUDIO_EXT:
            continue
        key = f.stem
        rel = str(f.relative_to(SFX_DIR))
        meta = dict(old.get(key, {}))
        if not meta and normalize:
            tmp = f.with_name(f.stem + ".norm" + f.suffix)
            run(["ffmpeg", "-y", "-v", "error", "-i", f, "-af", "loudnorm=I=-16:TP=-1:LRA=11", tmp])
            tmp.replace(f)
        meta.update({"file": rel, "category": f.parent.name,
                     "duration": round(duration(f), 3), "hit": round(hit_time(f), 3)})
        meta.setdefault("approved", False)
        meta.setdefault("license", "unknown")
        meta.setdefault("source", "")
        new[key] = meta
        log(f"{key:22s} {meta['category']:10s} dur={meta['duration']:.2f}s hit={meta['hit']:.2f}s "
            f"approved={meta['approved']}")
    save_json(mpath, new)
    log(f"{len(new)} sounds -> {mpath}")


if __name__ == "__main__":
    main()
