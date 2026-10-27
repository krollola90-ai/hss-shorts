# edit_plan.json

All times are seconds on the CUT timeline (`work/cuts.json` → `words[].start/end`, `duration`). Word indices (`emphasis`) are the `i` values in that file. Every key is optional; omit what the video doesn't need.

```json
{
  "hook": {"text": "5 CLAUDE SKILLS\nNOBODY KNOWS", "start": 0.05, "end": 2.7, "sfx": "vine-boom"},

  "zooms": [
    {"t": 2.85, "scale": 1.2, "sfx": "whoosh-short"},
    {"t": 5.10, "scale": 1.0},
    {"t": 7.74, "scale": 1.25}
  ],

  "overlays": [
    {"type": "badge", "start": 2.85, "end": 4.7, "text": "#1", "sub": "Skill Creator"},
    {"type": "stat",  "start": 7.74, "end": 9.2, "text": "92%", "sub": "never open it"},
    {"type": "card",  "start": 10.0, "end": 13.0, "title": "Why it matters", "body": "One line of\nsupporting text"},
    {"type": "list",  "start": 14.0, "end": 19.0, "title": "You need:", "items": [["Claude Pro", 14.3], ["5 minutes", 15.6]]},
    {"type": "code",  "start": 20.0, "end": 23.0, "title": "claude", "code": "/skill-creator build me a skill"},
    {"type": "image", "start": 24.0, "end": 27.0, "src": "broll/settings.png", "layout": "card",
     "focus": [0.5, 0.3], "zoom": 1.15, "caption": "Settings → Skills"}
  ],

  "sfx":   [{"t": 30.2, "name": "ka-ching", "db": -8}],
  "music": {"file": "music/lofi/track.mp3", "db": -22, "start_at": 0},
  "captions": {"enabled": true, "words_per_group": 3, "emphasis": [32, 57]}
}
```

## Fields

| Key | Notes |
| --- | --- |
| `hook` | 1–2 lines, ≤ 18 characters each, uppercase. Alternating yellow/white blocks pop in at `start`. Default SFX `vine-boom` (falls back to `bass-drop-1` until vine-boom is in the library). |
| `zooms` | Omit the key → automatic punch-ins every 2–4 s on sentence starts (`theme.zoom`). `[]` → none. Each entry sets the camera scale from `t` on (0.18 s ease); return to `1.0` explicitly. `sfx` is optional: put a whoosh on at most every other zoom. |
| `overlays[].type` | `badge` numbered list item; `stat` giant number; `card` glass title + body; `list` staged bullet reveal (`items: [text, time]`); `code` terminal card with typing reveal; `image` screenshot (`layout: card` top half, `full` covers the speaker). |
| `overlays[].position` | `top` (default, y=230), `middle` (y=720), `bottom` (y=1000). Never over the face: check the contact sheet. |
| `overlays[].sfx` | Defaults: badge/list → `pop`, stat → `vine-boom`, card → `whoosh-medium`, code → `typing`, image → `camera-shutter`. Use `""` for silence. |
| `sfx[]` | Extra cues: `t` is when the hit should land; `db` defaults to `theme.audio.sfx_db` (−9). |
| `music` | Path relative to `shorts-editor/`. Looped if shorter than the video. `null` for no bed. |
| `captions.emphasis` | Word indices that stay highlighted and slightly bigger: numbers, the key noun of the hook, punchlines. |

## Density targets (≤ 60 s video)

- A visual change every 2–4 s: zoom, overlay, or B-roll.
- 1 overlay per 6–8 s, never two at once; leave 0.3 s between them.
- SFX: one per visual event, at most ~1 per second overall. Big hits (`vine-boom`, `bass-drop`) 1–3 per video.
