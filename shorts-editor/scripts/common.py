"""Shared helpers for the shorts-editor pipeline (stdlib only)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # shorts-editor/
SFX_DIR = ROOT / "sfx"
MUSIC_DIR = ROOT / "music"
VENDOR_DIR = ROOT / "vendor"
THEME_PATH = Path(os.environ["SHORTS_THEME"]) if os.environ.get("SHORTS_THEME") else ROOT / "theme.json"

W, H, FPS = 1080, 1920, 30
MAX_DURATION = 120.0


def log(*a):
    print("[shorts]", *a, file=sys.stderr, flush=True)


def run(cmd, check=True, capture=False, quiet=False, **kw):
    if not quiet:
        log("$", " ".join(str(c) for c in cmd))
    r = subprocess.run([str(c) for c in cmd], check=False, text=True,
                       capture_output=capture, **kw)
    if check and r.returncode != 0:
        if capture:
            sys.stderr.write((r.stdout or "") + (r.stderr or ""))
        raise SystemExit(f"command failed ({r.returncode}): {cmd[0]}")
    return r


def ffprobe(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
             "-show_streams", path], capture=True, quiet=True)
    return json.loads(r.stdout)


def duration(path):
    return float(ffprobe(path)["format"]["duration"])


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def save_json(p, data):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def theme():
    return load_json(THEME_PATH)


def db_to_gain(db):
    return round(10 ** (db / 20.0), 4)


def env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default
