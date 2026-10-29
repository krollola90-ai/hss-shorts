---
name: shorts-editor
description: Edit raw talking-head footage into a 9:16 TikTok / Reels / YouTube Shorts video (≤120 s). Transcribes (ElevenLabs Scribe via connector, Whisper medium fallback), cuts fillers, pauses and retakes, reorders fragments into a logical story, adds punch-in zooms, word-by-word captions, HyperFrames motion-graphic cards and synced SFX, then masters and QCs the result. Use when the person asks to edit, cut, or make a short / TikTok / Reel / Shorts from a video. For Mark's menu ("монтаж") start with the `montazh` skill, which calls this one.
---

# Shorts editor

Everything lives in `shorts-editor/`. `shorts-editor/setup.sh` installs the toolchain (runs
automatically at session start via `.claude/settings.json`; re-run by hand if a tool is missing)
and writes `shorts-editor/.env.sh`, which the CLI sources. The pipeline is driven by
`shorts-editor/shorts <command> <project>`; run it with no arguments for the command list.
Talk to Mark in Russian; he speaks Ukrainian or Russian in his videos.

## Layout

| Path | What |
|---|---|
| `formats/<format>.json` | per-format preset: style, target length, story structure, overlay rules, music mood, ending |
| `styles/<name>.json` | look + pace: colours, font, captions, zoom cadence, cut thresholds, loudness (catalogue: `docs/styles.md`) |
| `assets/sfx/` | sound library + `manifest.json` (only `approved: true` names are usable) |
| `assets/music/<mood>/` | music beds Mark adds (calm, upbeat, emotional, phonk, lofi) |
| `assets/fonts/<family>/` | fonts with Cyrillic: inter, montserrat, unbounded, rubik, manrope, oswald, nunito |
| `projects/<name>/` | `project.json` (format, style, raw), `overrides.json`, `edit_plan.json`; `work/` and `hf/` are generated |
| `footage/raw/`, `footage/edited/` | sources (not in git) and finished videos |

Project names: `<format>-<YYYYMMDD>-<topic>`, e.g. `vacancy-20261029-teresin`.

## Workflow

### 1. Intake

```bash
shorts-editor/shorts fetch <name> <google-drive-link> <format>   # shared link
shorts-editor/shorts new   <name> <path/to/file>     <format>    # local file
```

Either one makes the 1080×1920 30 fps working copy, `work/audio.mp3`, and `project.json` with
the format's style. A link that returns a sign-in page means sharing isn't "anyone with the link".

### 2. Transcribe

- **ElevenLabs connector** (preferred while Mark has credits): `creative_create_flow` (or reuse a
  flow) → `creative_create_asset_upload` for `work/audio.mp3` → `curl -X PUT` the bytes →
  `creative_finalize_asset_upload` with the flow → `creative_transcribe_audio` (eleven_scribe_v1) →
  poll `creative_get_flow_run_status` → download `words_download_url` to `work/scribe_words.json` →
  `shorts import-scribe <name> work/scribe_words.json`. Never call the transcription twice (each
  call is charged). Tell Mark the credit cost.
- **Whisper medium** (free, ~1.5 min per 2.5 min of audio): `shorts transcribe <name> uk|ru`
  (no key → falls back automatically). It misses fillers and mangles Polish names: also run
  `silencedetect` for hesitations and fix caption spellings before rendering.

Read `work/words.json` end to end.

### 3. Cuts and story order

`shorts cuts <name>`, then fix everything in `projects/<name>/overrides.json` (inclusive word
indices) and re-run:

```json
{"drop": [[0, 1], [50, 50]], "keep": [[102, 113]], "order": [[2, 15], [77, 87], [16, 49]]}
```

- `drop`: greetings, fillers («е», «відповідно», «тобто»), failed takes, off-camera talk, repeats.
- `keep`: the retake heuristic often drops real content (lists, prices said twice on purpose) — check `removed`.
- `order`: story blocks in the format's `structure` (vacancy: hook → what/where → who → schedule →
  pay → conditions → urgency → ending). Every fact stays; only order and clutter change.
- Target length from the format preset; propose what to drop if it runs long.

### 4. Edit plan → checkpoint

Write `projects/<name>/edit_plan.json` against the CUT timeline (schema: `references/edit-plan.md`,
style rules: `references/style.md`). Compute overlay times from `work/cuts.json` word times in a
script, then make overlays never overlap (≥0.3 s gap). Optional `"layout": {"overlay_top": 175,
"card_scale": 0.82}` when the face sits high in the frame.

`shorts cut <name> --preview && shorts build <name> && shorts check <name>`, then
`hyperframes snapshot --at …` at each card (from `projects/<name>/hf`) and look: nothing over the
eyes/mouth, captions readable, no glued words. For a new format or an unclear video, send a draft
(`shorts preview`) and wait for Mark's OK; for an approved format, go straight to step 5 and say so.

### 5. Render + QC

```bash
shorts-editor/shorts cut <name> && shorts-editor/shorts build <name> && shorts-editor/shorts render <name>
```

~8 s of work per output second on the cloud's 2 CPUs. `finalize.py` masters to −14 LUFS and fails
QC on wrong size/fps, A/V mismatch, black or frozen frames, silences > 1.2 s.

### 6. Deliver

SendUserFile `footage/edited/<name>.mp4` with duration, LUFS, what was cut, open questions; upload
to Drive «02_Готово» when the Google Drive connector is available. Commit the project folder.

## Sound and music

`assets/sfx/<category>/<name>.mp3`; cues land on the event by the stored peak offset. New files:
drop in, `python3 shorts-editor/scripts/sfx_index.py --normalize`, set `approved: true`. Music: only
tracks Mark added under `assets/music/<mood>/` (credits in `assets/music/CREDITS.md`), bed at
`audio.music_db`; none yet → `"music": null`.

## Troubleshooting

- `hyperframes check` errors → read the `Fix:` line (never animate visibility on `.clip` elements).
- npm/pip "ENOTFOUND" or 403 → run through setup.sh's `pm` pattern (`NO_PROXY= no_proxy= npm_config_noproxy=`).
- Cut OOM on long 4K → `shorts new` makes a 1080p working copy; cut from that (project.json `raw`).
- Whisper `metadata_errors` crash → already handled (audio decoded via ffmpeg).
