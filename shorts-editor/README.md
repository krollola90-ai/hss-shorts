# shorts-editor

Pipeline that turns raw vertical talking-head footage into a finished 9:16 short (TikTok / Reels / Shorts, ≤120 s). Claude drives it through the `shorts-editor` skill (`.claude/skills/shorts-editor/`).

```
raw.mp4 ─► transcribe (ElevenLabs Scribe │ faster-whisper) ─► words.json
        ─► plan_cuts (fillers, pauses >0.3 s, stutters, retakes) ─► cuts.json
        ─► cut (FFmpeg) ─► cut.mp4
        ─► edit_plan.json (hook, zooms, cards, B-roll, SFX, music)  ◄── approval checkpoint
        ─► build_comp ─► HyperFrames project (captions, overlays, audio mix)
        ─► hyperframes render ─► finalize (−14 LUFS, QC gate) ─► footage/edited/<name>.mp4
```

## Layout

| Path | What |
| --- | --- |
| `shorts` | CLI: `new`, `transcribe`, `cuts`, `cut`, `build`, `check`, `preview`, `render`, `all` |
| `setup.sh` | Installs/validates the toolchain in a fresh cloud container (idempotent) |
| `theme.json` | Look and timing: colors, caption style, zoom cadence, loudness, cut thresholds |
| `scripts/` | Pipeline steps (Python stdlib; faster-whisper optional) |
| `sfx/` | Approved sound library + `manifest.json` (duration, hit offset, license) |
| `music/` | Background beds, one folder per mood + credits |
| `vendor/` | GSAP and Inter (Latin + Cyrillic), so renders need no CDN |
| `footage/raw`, `footage/edited` | Stock footage in, finished videos out (Git LFS) |
| `projects/<name>/` | Per-video: `edit_plan.json`, `overrides.json`, `broll/`, generated `hf/` |

## Requirements

- `ELEVENLABS_API_KEY` as an environment secret (Scribe speech-to-text). Without it, the pipeline uses local Whisper.
- Environment network allowlist: `api.elevenlabs.io` (Scribe), `huggingface.co` (Whisper model download), `www.myinstants.com`, `pixabay.com`, `cdn.pixabay.com` (SFX/music sourcing).
- Self-test without any API: `python3 scripts/make_fixture.py /tmp/fx` creates a synthetic clip + transcript (needs `espeak-ng`).
