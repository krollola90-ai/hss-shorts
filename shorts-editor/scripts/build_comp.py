#!/usr/bin/env python3
"""Generate a HyperFrames 9:16 project from the cut video + edit plan.

usage: build_comp.py <project_dir>

Reads  <project_dir>/work/cut.mp4, work/cuts.json, edit_plan.json, ../../theme.json
Writes <project_dir>/hf/ (index.html + assets/) ready for `hyperframes render`.

Edit plan schema (all times are in CUT-timeline seconds; see SKILL.md):
{
  "hook":     {"text": "LINE ONE\\nLINE TWO", "start": 0.1, "end": 3.2, "sfx": "vine-boom"},
  "zooms":    [{"t": 2.4, "scale": 1.2, "sfx": "whoosh-short"}, {"t": 4.1, "scale": 1.0}],
  "overlays": [
    {"type": "badge", "start": 5, "end": 7, "text": "#1", "sub": "Skill Creator", "sfx": "pop"},
    {"type": "stat",  "start": 9, "end": 11, "text": "92%", "sub": "of teams", "sfx": "vine-boom"},
    {"type": "card",  "start": 12, "end": 15, "title": "...", "body": "...", "sfx": "whoosh-medium"},
    {"type": "list",  "start": 16, "end": 20, "title": "...", "items": [["a", 16.2], ["b", 17.5]], "sfx": "pop"},
    {"type": "code",  "start": 21, "end": 24, "title": "prompt", "code": "...", "sfx": "typing"},
    {"type": "image", "start": 25, "end": 28, "src": "broll/x.png", "layout": "card|full",
     "focus": [0.5, 0.3], "zoom": 1.15, "caption": "", "sfx": "camera-shutter"}
  ],
  "sfx":      [{"t": 30.0, "name": "ka-ching", "db": -8}],
  "music":    {"file": "music/lofi/track.mp3", "db": -22, "start_at": 0} | null,
  "captions": {"enabled": true, "words_per_group": 3, "emphasis": [12, 40]}
}
"""
import html
import json
import math
import random
import re
import shutil
import sys
from pathlib import Path

from common import (FPS, H, ROOT, SFX_DIR, VENDOR_DIR, W, db_to_gain, duration, load_json,
                    log, theme)

esc = html.escape


# ---------- SFX lookup ------------------------------------------------------------------

def sfx_manifest():
    p = SFX_DIR / "manifest.json"
    return load_json(p) if p.exists() else {}


# Stand-ins used until the approved originals are in the library (see sfx-library.md).
FALLBACKS = {"vine-boom": "bass-drop-1", "camera-shutter": "click", "record-scratch": "glitch-1",
             "ka-ching": "correct-chime", "bonk": "pop", "fahhh": "wrong-buzzer",
             "bruh": "wrong-buzzer", "crowd-ooh": "sparkle"}


def resolve_sfx(name, manifest):
    if name not in manifest and name in FALLBACKS:
        log(f"sfx '{name}' not in library yet - using stand-in '{FALLBACKS[name]}'")
        name = FALLBACKS[name]
    if name in manifest:
        return name, manifest[name]
    # family match: "whoosh" -> first approved "whoosh-*"
    for k, v in manifest.items():
        if k.startswith(name) and v.get("approved", True):
            return k, v
    return None, None


# ---------- captions --------------------------------------------------------------------

def caption_groups(words, n, max_gap):
    groups, cur = [], []
    for w in words:
        if w["kind"] != "word":
            continue
        if cur and (len(cur) >= n or w["start"] - cur[-1]["end"] > max_gap
                    or re.search(r"[.!?…,;:]$", cur[-1]["text"])):
            # a one/two-letter word (у, в, з, o, і, to…) never hangs at the end of a line:
            # it moves down to start the next group together with the word it belongs to
            carry = []
            if (len(cur) > 1 and len(cur[-1]["text"]) <= 2 and not re.search(r"[.!?…,;:]$", cur[-1]["text"])
                    and w["start"] - cur[-1]["end"] <= max_gap):
                carry = [cur.pop()]
            groups.append(cur)
            cur = carry
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def caption_font_size(text, cfg):
    # Inter Black uppercase averages ~0.64 em per glyph; 900 px usable width in portrait.
    est = 900 / max(1, len(text) * 0.64)
    return int(max(cfg["min_font_size"], min(cfg["font_size"], est)))


# ---------- zooms -----------------------------------------------------------------------

def auto_zooms(words, total, zcfg, seed=7):
    """Punch-ins on sentence starts / emphasis, spaced 2-4 s, alternating in and out."""
    rnd = random.Random(seed)
    starts = [w for w in words if w["kind"] == "word"]
    out, last, level = [], -9.0, 1.0
    for j, w in enumerate(starts):
        sentence_start = j == 0 or re.search(r"[.!?…]$", starts[j - 1]["text"])
        gap = w["start"] - last
        if gap < zcfg["min_interval"]:
            continue
        if sentence_start or gap >= zcfg["max_interval"]:
            level = 1.0 if level > 1.0 and rnd.random() < 0.5 else rnd.choice(zcfg["scales"])
            out.append({"t": round(max(0.0, w["start"] - 0.03), 3), "scale": level})
            last = w["start"]
    return [z for z in out if z["t"] < total - 0.5]


# ---------- overlay markup --------------------------------------------------------------

def nl2br(t):
    return "<br>".join(esc(x) for x in str(t).split("\n"))


def overlay_html(k, o):
    oid = f"ov{k}"
    pos = o.get("position", "top")
    common = f'id="{oid}" class="clip ov pos-{pos}" data-start="{o["start"]}" ' \
             f'data-duration="{round(o["end"] - o["start"], 3)}"'
    t = o["type"]
    if t == "badge":
        inner = (f'<div class="badge"><span class="badge-num">{esc(o["text"])}</span>'
                 f'<span class="badge-label">{nl2br(o.get("sub", ""))}</span></div>')
    elif t == "stat":
        inner = (f'<div class="stat"><div class="stat-num">{esc(o["text"])}</div>'
                 f'<div class="stat-sub">{nl2br(o.get("sub", ""))}</div></div>')
    elif t == "card":
        inner = (f'<div class="glass card"><div class="card-title">{nl2br(o.get("title", ""))}</div>'
                 f'<div class="card-body">{nl2br(o.get("body", ""))}</div></div>')
    elif t == "list":
        items = "".join(f'<li id="{oid}-i{n}"><span class="dot">{n + 1}</span>{esc(it[0])}</li>'
                        for n, it in enumerate(o.get("items", [])))
        inner = (f'<div class="glass card"><div class="card-title">{nl2br(o.get("title", ""))}</div>'
                 f'<ul class="list">{items}</ul></div>')
    elif t == "code":
        inner = (f'<div class="glass code"><div class="code-bar"><i></i><i></i><i></i>'
                 f'<span>{esc(o.get("title", ""))}</span></div>'
                 f'<pre id="{oid}-code">{esc(o["code"])}</pre></div>')
    elif t == "image":
        layout = o.get("layout", "card")
        cap = f'<div class="img-cap">{nl2br(o["caption"])}</div>' if o.get("caption") else ""
        fx, fy = o.get("focus", [0.5, 0.5])
        inner = (f'<div class="shot shot-{layout}"><div class="shot-frame">'
                 f'<img id="{oid}-img" src="{esc(o["_asset"])}" '
                 f'style="object-position:{fx * 100:.0f}% {fy * 100:.0f}%;'
                 f'transform-origin:{fx * 100:.0f}% {fy * 100:.0f}%"></div>{cap}</div>')
        common = common.replace("ov pos-", f"ov ov-{layout} pos-")
    else:
        raise SystemExit(f"unknown overlay type: {t}")
    return f'<div {common}>{inner}</div>'


def overlay_js(k, o):
    oid, s, e = f"#ov{k}", o["start"], o["end"]
    child = f"{oid} > *"
    js = []
    t = o["type"]
    if t in ("badge", "stat"):
        js.append(f'tl.fromTo("{child}",{{scale:0.4,opacity:0,y:30}},'
                  f'{{scale:1,opacity:1,y:0,duration:0.32,ease:"back.out(2.2)"}},{s});')
    elif t == "image" and o.get("layout", "card") == "full":
        js.append(f'tl.fromTo("{child}",{{opacity:0}},{{opacity:1,duration:0.12}},{s});')
    else:
        js.append(f'tl.fromTo("{child}",{{y:-80,opacity:0,scale:0.96}},'
                  f'{{y:0,opacity:1,scale:1,duration:0.4,ease:"power3.out"}},{s});')
    if t == "list":
        for n, it in enumerate(o.get("items", [])):
            at = it[1] if len(it) > 1 else s + 0.3 + 0.5 * n
            js.append(f'tl.fromTo("{oid}-i{n}",{{opacity:0,x:-40}},'
                      f'{{opacity:1,x:0,duration:0.25,ease:"back.out(1.8)"}},{at});')
    if t == "code":
        n = len(o["code"])
        type_dur = min(max(0.6, n * 0.025), (e - s) * 0.6)
        js.append(f'tl.fromTo("{oid}-code",{{clipPath:"inset(0 100% 0 0)"}},'
                  f'{{clipPath:"inset(0 0% 0 0)",duration:{type_dur:.2f},ease:"steps({min(n, 60)})"}},{s + 0.3});')
    if t == "image":
        z = o.get("zoom", 1.12)
        js.append(f'tl.fromTo("{oid}-img",{{scale:1}},{{scale:{z},duration:{e - s:.2f},ease:"none"}},{s});')
    js.append(f'tl.to("{child}",{{opacity:0,duration:0.2,ease:"power2.in"}},{max(s, e - 0.2):.3f});')
    return js


# ---------- main ------------------------------------------------------------------------

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:%(W)dpx;height:%(H)dpx;overflow:hidden;background:#000}
#root{position:relative;width:100%%;height:100%%;font-family:'Inter',sans-serif;color:var(--ink)}
:root{--ink:%(ink)s;--ink-dim:%(ink_dim)s;--accent:%(accent)s;--accent-ink:%(accent_ink)s;
--glass:%(glass)s;--glass-border:%(glass_border)s;--radius:%(radius)dpx;
--cap-idle:%(cap_idle)s;--hook-bg:%(hook_bg)s;--hook-ink:%(hook_ink)s;--hook-alt-bg:%(hook_alt_bg)s;--hook-alt-ink:%(hook_alt_ink)s;--stat:%(stat_color)s}
#cam{position:absolute;inset:0;transform-origin:50%% 38%%;z-index:1}
#cam video{position:absolute;inset:0;width:100%%;height:100%%;object-fit:cover}
.ov{position:absolute;left:0;right:0;z-index:10;display:flex;justify-content:center}
.ov>*{will-change:transform,opacity}
.pos-top{top:230px}.pos-middle{top:720px}.pos-bottom{top:1000px}
.ov-full{inset:0;top:0;z-index:5}
.glass{background:var(--glass);border:2px solid var(--glass-border);border-radius:var(--radius);
backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);box-shadow:0 30px 80px rgba(0,0,0,.45)}
#hook{position:absolute;left:0;right:0;top:250px;z-index:12;text-align:center;padding:0 60px}
#hook .line{display:inline-block;background:var(--hook-bg);color:var(--hook-ink);font-weight:900;
font-size:86px;line-height:1.02;letter-spacing:-0.02em;text-transform:uppercase;padding:10px 26px;
margin:6px 0;border-radius:18px;box-shadow:0 18px 50px rgba(0,0,0,.45)}
#hook .line.alt{background:var(--hook-alt-bg);color:var(--hook-alt-ink)}
%(cap_box_css)s
.badge{display:flex;align-items:center;gap:26px;background:var(--glass);border:2px solid var(--glass-border);
border-radius:999px;padding:18px 46px 18px 18px;box-shadow:0 30px 80px rgba(0,0,0,.45)}
.badge-num{display:flex;align-items:center;justify-content:center;min-width:132px;height:132px;padding:0 20px;
border-radius:999px;background:var(--accent);color:var(--accent-ink);font-weight:900;font-size:76px}
.badge-label{font-weight:900;font-size:62px;line-height:1.05;max-width:640px}
.stat{text-align:center}
.stat-num{font-weight:900;font-size:230px;line-height:.95;color:var(--stat);letter-spacing:-0.04em;
text-shadow:0 20px 60px rgba(0,0,0,.6)}
.stat-sub{font-weight:800;font-size:58px;margin-top:10px;text-shadow:0 8px 30px rgba(0,0,0,.7)}
.card{width:960px;padding:44px 48px}
.card-title{font-weight:900;font-size:64px;line-height:1.05;letter-spacing:-0.02em}
.card-body{font-weight:700;font-size:44px;line-height:1.25;color:var(--ink-dim);margin-top:18px}
.list{list-style:none;margin-top:22px}
.list li{display:flex;align-items:center;gap:22px;font-weight:800;font-size:50px;margin:14px 0}
.list .dot{display:inline-flex;align-items:center;justify-content:center;width:70px;height:70px;border-radius:50%%;
background:var(--accent);color:var(--accent-ink);font-weight:900;font-size:40px;flex:none}
.code{width:980px;overflow:hidden}
.code-bar{display:flex;align-items:center;gap:12px;padding:22px 28px;border-bottom:1px solid var(--glass-border)}
.code-bar i{width:20px;height:20px;border-radius:50%%;background:#ff5f57}.code-bar i:nth-child(2){background:#febc2e}
.code-bar i:nth-child(3){background:#28c840}.code-bar span{margin-left:14px;font-weight:700;font-size:30px;color:var(--ink-dim)}
.code pre{padding:30px 34px;font-family:'JetBrains Mono','DejaVu Sans Mono',monospace;font-size:38px;line-height:1.35;
white-space:pre-wrap;word-break:break-word;color:#e8e8f0}
.shot{display:flex;flex-direction:column;align-items:center}
.shot-card .shot-frame{width:960px;height:720px;border-radius:var(--radius);overflow:hidden;
border:3px solid var(--glass-border);box-shadow:0 40px 100px rgba(0,0,0,.55);background:#111}
.shot-full .shot-frame{position:absolute;inset:0;background:#0b0b0f}
.shot-frame img{width:100%%;height:100%%;object-fit:cover;display:block}
.img-cap{margin-top:22px;font-weight:800;font-size:44px;background:var(--glass);padding:12px 26px;border-radius:16px}
#captions{position:absolute;left:0;right:0;bottom:%(cap_bottom)dpx;z-index:20;height:0}
.cg{position:absolute;left:0;right:0;bottom:0;text-align:center;padding:0 70px;font-weight:%(cap_weight)d;
line-height:1.08;letter-spacing:-0.01em;%(cap_case)s}
.cw{display:inline-block;margin:0 .14em;padding:0 .1em;border-radius:14px;color:var(--cap-idle);text-shadow:%(cap_shadow)s;
-webkit-text-stroke:3px rgba(0,0,0,.55);paint-order:stroke fill}
"""


def fonts_css():
    css = (VENDOR_DIR / "fonts" / "inter.css").read_text()
    return re.sub(r"url\((inter-[^)]+)\)", r"url(assets/fonts/\1)", css)


def main():
    proj = Path(sys.argv[1]).resolve()
    th = theme()
    plan = load_json(proj / "edit_plan.json")
    cuts = load_json(proj / "work" / "cuts.json")
    cut_mp4 = proj / "work" / "cut.mp4"
    total = round(duration(cut_mp4), 3)
    words = cuts["words"]

    hf = proj / "hf"
    assets = hf / "assets"
    for d in ("fonts", "sfx", "music", "broll", "vendor"):
        (assets / d).mkdir(parents=True, exist_ok=True)
    for f in (VENDOR_DIR / "fonts").glob("*.woff2"):
        shutil.copy2(f, assets / "fonts" / f.name)
    shutil.copy2(VENDOR_DIR / "gsap.min.js", assets / "vendor" / "gsap.min.js")
    video_asset = assets / "cut.mp4"
    if video_asset.exists() or video_asset.is_symlink():
        video_asset.unlink()
    shutil.copy2(cut_mp4, video_asset)

    manifest = sfx_manifest()
    audio_tags, cues = [], []

    def cue(t, name, db=None):
        if not name:
            return
        key, meta = resolve_sfx(name, manifest)
        if not meta:
            log(f"WARNING: sfx '{name}' not in library - skipped")
            return
        cues.append((t, key, meta, th["audio"]["sfx_db"] if db is None else db))

    # ---- hook
    body, js = [], []
    hook = plan.get("hook")
    if hook:
        lines = "".join(f'<div><span class="line{" alt" if n % 2 else ""}">{esc(l)}</span></div>'
                        for n, l in enumerate(hook["text"].split("\n")))
        body.append(f'<div id="hook" class="clip" data-start="{hook["start"]}" '
                    f'data-duration="{round(hook["end"] - hook["start"], 3)}">{lines}</div>')
        js.append(f'tl.fromTo("#hook .line",{{scale:0.3,opacity:0,rotation:-4}},{{scale:1,opacity:1,rotation:0,'
                  f'duration:0.34,ease:"back.out(2.4)",stagger:0.12}},{hook["start"]});')
        js.append(f'tl.to("#hook .line",{{opacity:0,y:-30,duration:0.2,ease:"power2.in"}},{hook["end"] - 0.2:.3f});')
        cue(hook["start"], hook.get("sfx", "vine-boom"))

    # ---- zooms (on #cam wrapper, never on the timed video)
    zooms = plan.get("zooms")
    if zooms is None and th["zoom"]["auto"]:
        zooms = auto_zooms(words, total, th["zoom"])
    zin = th["zoom"]["in_duration"]
    for z in zooms or []:
        js.append(f'tl.to("#cam",{{scale:{z["scale"]},duration:{zin},ease:"power3.out"}},{z["t"]});')
        cue(z["t"], z.get("sfx"))

    # ---- overlays
    for k, o in enumerate(plan.get("overlays", [])):
        if o["type"] == "image":
            src = (proj / o["src"]) if not Path(o["src"]).is_absolute() else Path(o["src"])
            dst = assets / "broll" / src.name
            shutil.copy2(src, dst)
            o["_asset"] = f"assets/broll/{src.name}"
        body.append(overlay_html(k, o))
        js.extend(overlay_js(k, o))
        default = {"badge": "pop", "stat": "vine-boom", "card": "whoosh-medium", "list": "pop",
                   "code": "typing", "image": "camera-shutter"}[o["type"]]
        cue(o["start"], o.get("sfx", default))
        if o["type"] == "list":
            for n, it in enumerate(o.get("items", [])):
                cue(it[1] if len(it) > 1 else o["start"] + 0.3 + 0.5 * n, o.get("item_sfx", "pop"))

    # ---- extra SFX cues
    for c in plan.get("sfx", []):
        cue(c["t"], c["name"], c.get("db"))

    # ---- captions
    ccfg = dict(th["captions"], **(plan.get("captions") or {}))
    cap_html = []
    if ccfg.get("enabled", True):
        emph = set(ccfg.get("emphasis", []))
        groups = caption_groups(words, ccfg["words_per_group"], ccfg["max_group_gap"])
        prev_end = 0.0
        for g_i, g in enumerate(groups):
            text = " ".join(w["text"] for w in g)
            fs = caption_font_size(text, ccfg)
            g0 = max(0.0, g[0]["start"] - 0.05, prev_end)
            g1 = min(total, g[-1]["end"] + 0.12)
            if g_i + 1 < len(groups):
                g1 = min(g1, groups[g_i + 1][0]["start"] - 0.05)
            g1 = max(g1, g0 + 0.1)
            prev_end = g1
            spans = "".join(f'<span id="w{w["i"]}" class="cw">{esc(w["text"])}</span>' for w in g)
            cap_html.append(f'<div id="cg{g_i}" class="clip cg" data-start="{g0:.3f}" '
                            f'data-duration="{g1 - g0:.3f}" style="font-size:{fs}px">'
                            + '<div class="cgi">' + (f'<span class="box">{spans}</span>' if ccfg.get("box") else spans) + '</div></div>')
            js.append(f'tl.set("#cg{g_i} .cgi",{{opacity:1}},{g0:.3f});')
            js.append(f'tl.fromTo("#cg{g_i} .cw",{{y:18,opacity:0}},{{y:0,opacity:1,duration:0.1,'
                      f'stagger:0.03,ease:"power2.out"}},{g0:.3f});')
            # hard kill so a stale group never lingers under the next one
            js.append(f'tl.set("#cg{g_i} .cgi",{{opacity:0}},{g1 - 0.001:.3f});')
            for w in g:
                if w["i"] in emph and ccfg.get("emphasis_style") == "plate":
                    js.append(f'tl.to("#w{w["i"]}",{{color:"var(--accent-ink)",backgroundColor:"var(--accent)",'
                              f'textShadow:"none",webkitTextStroke:"0px rgba(0,0,0,0)",duration:0.08,overwrite:"auto"}},{w["start"]:.3f});')
                    continue
                big = ccfg["active_scale"] * (1.1 if w["i"] in emph else 1.0)
                js.append(f'tl.to("#w{w["i"]}",{{color:"var(--accent)",scale:{big:.2f},duration:0.06,overwrite:"auto"}},{w["start"]:.3f});')
                if w["i"] not in emph:
                    js.append(f'tl.to("#w{w["i"]}",{{color:"var(--ink)",scale:1,duration:0.06,overwrite:"auto"}},{w["end"]:.3f});')

    # ---- audio
    for n, (t, key, meta, db) in enumerate(cues):
        src = SFX_DIR / meta["file"]
        dst = assets / "sfx" / Path(meta["file"]).name
        if not dst.exists():
            shutil.copy2(src, dst)
        hit = float(meta.get("hit", 0.0))
        start = t - hit
        media_start = 0.0
        if start < 0:
            media_start, start = -start, 0.0
        dur = min(float(meta["duration"]) - media_start, total - start)
        if dur <= 0.05:
            continue
        audio_tags.append(f'<audio id="sfx{n}" class="clip" src="assets/sfx/{dst.name}" '
                          f'data-start="{start:.3f}" data-duration="{dur:.3f}" '
                          f'data-media-start="{media_start:.3f}" data-volume="{db_to_gain(db)}" '
                          f'data-audio-group="sfx"></audio>')
    music = plan.get("music")
    if music:
        src = ROOT / music["file"]
        dst = assets / "music" / src.name
        shutil.copy2(src, dst)
        mdur = duration(src)
        t, off, n = 0.0, float(music.get("start_at", 0)), 0
        while t < total - 0.05:
            seg = min(mdur - off, total - t)
            audio_tags.append(f'<audio id="music{n}" class="clip" src="assets/music/{dst.name}" '
                              f'data-start="{t:.3f}" data-duration="{seg:.3f}" data-media-start="{off:.3f}" '
                              f'data-volume="{db_to_gain(music.get("db", th["audio"]["music_db"]))}" '
                              f'data-fade-in="{0.4 if n == 0 else 0.8}" data-fade-out="1.2" '
                              f'data-audio-group="music"></audio>')
            t, off, n = t + seg, 0.0, n + 1

    c = th["colors"]
    css = CSS % dict(W=W, H=H, radius=th["radius"], cap_bottom=ccfg["bottom_px"],
                     cap_weight=ccfg["weight"], cap_shadow=ccfg["stroke"],
                     cap_case="text-transform:uppercase;" if ccfg.get("uppercase") else "",
                     cap_idle=ccfg.get("idle_color", c["ink"]),
                     hook_bg=th.get("hook", {}).get("bg", c["accent"]),
                     hook_ink=th.get("hook", {}).get("ink", c["accent_ink"]),
                     hook_alt_bg=th.get("hook", {}).get("alt_bg", "#fff"),
                     hook_alt_ink=th.get("hook", {}).get("alt_ink", c["accent_ink"]),
                     stat_color=c.get("stat", c["accent"]),
                     cap_box_css=(".cg .cw{-webkit-text-stroke:0;text-shadow:none}"
                                  ".cg{display:flex;justify-content:center}"
                                  ".cg>.box{display:inline-block;background:%s;border-radius:22px;padding:10px 26px}"
                                  % ccfg["box"]) if ccfg.get("box") else "", **c)
    # per-video layout tweaks (edit_plan.json -> "layout"), for framings where the face sits high:
    #   overlay_top: y of top cards (default 230), card_scale: shrink cards/lists (default 1)
    lay = plan.get("layout") or {}
    layout_css = ""
    if lay.get("overlay_top"):
        layout_css += f".pos-top{{top:{int(lay['overlay_top'])}px}}#hook{{top:{int(lay['overlay_top']) + 20}px}}"
    if lay.get("card_scale"):
        k = float(lay["card_scale"])
        layout_css += (f".card{{padding:{int(44*k)}px {int(48*k)}px;width:{int(960*k)}px}}"
                       f".card-title{{font-size:{int(64*k)}px}}.card-body{{font-size:{int(44*k)}px}}"
                       f".list{{margin-top:{int(22*k)}px}}.list li{{font-size:{int(50*k)}px;margin:{int(14*k)}px 0}}"
                       f".list .dot{{width:{int(70*k)}px;height:{int(70*k)}px;font-size:{int(40*k)}px}}")
    doc = f"""<!doctype html>
<html lang="{cuts.get('language', 'en')}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<script src="assets/vendor/gsap.min.js"></script>
<style>
{fonts_css()}
{css}
{layout_css}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
  <div id="cam"><video id="talk" class="clip" src="assets/cut.mp4" data-start="0" data-duration="{total}" data-has-audio="true" data-volume="1"></video></div>
  {chr(10).join('  ' + b for b in body)}
  <div id="captions" data-track-kind="captions">
{chr(10).join('    ' + h for h in cap_html)}
  </div>
{chr(10).join('  ' + a for a in audio_tags)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
</script>
</body>
</html>
"""
    (hf / "index.html").write_text(doc, encoding="utf-8")
    for f in ("hyperframes.json", "meta.json"):
        if not (hf / f).exists():
            (hf / f).write_text(json.dumps({"name": proj.name} if f == "meta.json" else {}), encoding="utf-8")
    log(f"composition -> {hf / 'index.html'}  ({total:.2f}s, {len(cues)} sfx, "
        f"{len(zooms or [])} zooms, {len(plan.get('overlays', []))} overlays)")


if __name__ == "__main__":
    main()
