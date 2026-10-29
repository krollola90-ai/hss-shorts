"""Shared helpers for the shorts-editor pipeline (stdlib only)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # shorts-editor/
ASSETS_DIR = ROOT / "assets"
SFX_DIR = ASSETS_DIR / "sfx"
MUSIC_DIR = ASSETS_DIR / "music"
FONTS_DIR = ASSETS_DIR / "fonts"
VENDOR_DIR = ASSETS_DIR / "vendor"
STYLES_DIR = ROOT / "styles"
DEFAULT_STYLE = STYLES_DIR / "white-minimal.json"
# the active style: SHORTS_STYLE (set by the `shorts` CLI from project.json) or the default
_style_env = os.environ.get("SHORTS_STYLE") or os.environ.get("SHORTS_THEME")
THEME_PATH = Path(_style_env) if _style_env else DEFAULT_STYLE

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
