---
name: shorts-editor
description: Edit raw talking-head footage into a 9:16 TikTok / Reels / YouTube Shorts video (≤120 s). Transcribes with ElevenLabs Scribe (Whisper fallback), cuts fillers, pauses and retakes, adds punch-in zooms, word-by-word karaoke captions, HyperFrames motion-graphic cards, live web B-roll, synced SFX and a music bed, then masters and QCs the result. Use when the person asks to edit, cut, or make a short / TikTok / Reel / Shorts from a video, or names a file in shorts-editor/footage/raw.
---

# Shorts editor

Everything lives in `shorts-editor/` (repo root). Tools are installed by `shorts-editor/setup.sh`: run it first in every new cloud session (idempotent, ~1–2 min on a fresh container, seconds otherwise). It also reports missing keys and blocked hosts. The pipeline is driven by `shorts-editor/shorts <command> <project>`. HyperFrames is the renderer; load the `/hyperframes` skill before changing the composition generator itself, not for normal edits.

Settled decisions (from the setup interview, don't re-ask):

- Source: vertical phone talking head. Languages: EN, RU, UK, ES, possibly mixed.
- Transcription: Scribe REST via `ELEVENLABS_API_KEY` (subscription quota); automatic faster-whisper fallback. Never pay beyond the included quota: if Scribe returns a quota/billing error, fall back, don't retry.
- Captions: word-by-word karaoke, 3 words/group, uppercase Inter Black, active word in accent yellow.
- Theme: dark glass + `#FFE600` accent (`shorts-editor/theme.json`).
- One approval checkpoint: the edit plan, before any full render.
- B-roll: live captures from the person's own signed-in Chrome (Claude in Chrome / Remote Control) first, Playwright `storageState` (`PW_STORAGE_STATE` secret) second, recreated `card` overlay last.
- Storage: raw footage in `footage/raw/`, finished videos in `footage/edited/`. Google Drive sync comes later (stock vs edited folders).

## Workflow

### 1. Intake

```bash
shorts-editor/shorts new <name> <path/to/raw.mp4>
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate -of compact shorts-editor/footage/raw/<file>
```

Note duration, resolution, rotation. If the file is over 100 MB, it must go through Git LFS (`.gitattributes` already tracks `footage/**`).

### 2. Transcribe

```bash
shorts-editor/shorts transcribe <name> [en|ru|uk|es]
```

Pass the language when known; omit it for auto-detect / mixed. Read `work/words.json` end to end before going on: check the language, that fillers were captured, that there are no hallucinated words over silence. Whisper is weaker on fillers: when `engine` is `whisper`, also scan `silencedetect` for hesitation gaps.

### 3. Cuts

```bash
shorts-editor/shorts cuts <name>
```

`plan_cuts.py` removes: fillers, audio events, stutters, repeated n-grams, retakes (a phrase restarted within 14 words), isolated soft fillers ("like", "ну", "pues"…), and pauses > 0.3 s (kept edges: 60 ms lead, 100 ms tail). Read `work/cuts.json` → `removed` and the joined kept text. Fix every wrong decision in `projects/<name>/overrides.json` (inclusive word-index ranges) and re-run:

```json
{"drop": [[120, 134]], "keep": [[57, 57]], "trim_start": 0.0, "trim_end": null}
```

Typical manual fixes: a whole bad take the heuristics missed (drop the range), an intentional repetition for emphasis (keep it), a weak ending (trim_end). The cut must be ≤ 120 s; if not, propose what to drop.

### 4. Edit plan (the creative pass) → CHECKPOINT

Write `projects/<name>/edit_plan.json` against the CUT timeline (`work/cuts.json` → `words[].start/end`). Schema and examples: `references/edit-plan.md`. Style rules: `references/style.md`. SFX names: `shorts-editor/sfx/manifest.json` (only `approved: true`).

Then show the person the plan before rendering:

1. `shorts-editor/shorts cut <name> --preview && shorts-editor/shorts build <name> && shorts-editor/shorts check <name>`. Look at the contact sheet yourself and fix anything that overlaps the face, leaves the 168–1330 px safe band, or collides with captions.
2. Present: kept script (with removed parts struck through), hook text, overlay list with times, zoom count, SFX map (time → sound), music choice, final duration, and the contact sheet image. Keep it scannable: a table per section.
3. Wait for approval or edits. Apply edits, re-check, and only then continue.

### 5. B-roll capture (if the plan uses `image` overlays)

Per screenshot: open the page in the person's Chrome (load the `chrome-browser` skill first), scroll to the relevant element, screenshot at ≥1600 px wide, save to `projects/<name>/broll/<slug>.png`. Never capture DMs, notifications, or anyone's private data beyond what the video is about; crop out account names unless the person wants them shown. If no browser access: Playwright with `PW_STORAGE_STATE`, else switch that overlay to a `card`.

### 6. Render + QC

```bash
shorts-editor/shorts cut <name>        # full-quality cut (step 4 used --preview)
shorts-editor/shorts build <name>
shorts-editor/shorts render <name>     # HyperFrames render -> loudnorm -14 LUFS -> QC
```

Render speed is ~6 s per output second on 4 CPUs (2 min ≈ 12 min): run it in the background and tell the person. `finalize.py` exits 2 when QC fails (duration > 120 s, wrong size/fps, A/V length mismatch, black frames, frozen video, silence > 1.2 s). A freeze during a full-screen still B-roll is expected; anything else gets fixed and re-rendered. Then spot-check 4–6 frames around cuts with `hyperframes snapshot --at` and listen for clipped word starts at each segment boundary (`ffmpeg -ss <t-0.3> -t 0.8` around each `segments[].out_start`).

### 7. Deliver

Output: `shorts-editor/footage/edited/<name>.mp4`. Send it to the person (SendUserFile), report duration, LUFS, what was cut (seconds and %), and any QC notes. Commit the project folder (plan, overrides, broll, cuts.json) plus the edited video; `work/` and `hf/assets` are gitignored. Delete `work/*.mp4` after a successful build.

## SFX library

`shorts-editor/sfx/<category>/<name>.mp3` + `manifest.json` (`duration`, `hit` = seconds to the peak, `approved`, `license`, `source`). Cues are placed so the hit lands on the event time. Adding sounds: drop files into the right category, run `python3 shorts-editor/scripts/sfx_index.py --normalize`, play/describe them to the person, set `approved: true` for the ones they accept. Wanted list and sources: `references/sfx-library.md`.

## Music

`shorts-editor/music/<mood>/` with a `CREDITS.md` per mood folder. Free, commercial-use sources only (Pixabay Music by default). Bed at −22 dB under the voice (`theme.audio.music_db`). If no music is in the library yet, render without (`"music": null`) and say so; the person may add a trending sound in-app instead.

## Troubleshooting

- `hyperframes check` errors → read the `Fix:` line; for generator bugs see `/hyperframes` contract (no CSS transforms on GSAP-animated elements, clips need `data-start`/`data-duration`).
- Video freezes in render → the cut must have `-g 30` (cut.py does this); re-run `shorts cut`.
- Scribe 401/403/429 → key missing or quota hit → Whisper fallback runs automatically; tell the person.
- Whisper can't download its model → `huggingface.co` is not in the environment's allowed domains.
