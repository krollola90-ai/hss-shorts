# SFX library status

The person approved these 16 sound types (2026-10-26). "In library" means a file is in `shorts-editor/assets/sfx/` with `approved: true` in `manifest.json`.

| Category | Sound | In library | File(s) / where to get it |
| --- | --- | --- | --- |
| impact | Vine Boom | no | myinstants.com "Vine Boom" (meme original) |
| impact | Bass Drop / Cinematic Hit | yes | `bass-drop-1`, `bass-drop-2` (Pixabay) |
| impact | Fahhh / Bruh | no | myinstants.com "Fahhh", "Bruh" |
| impact | Record Scratch | no | pixabay.com/sound-effects "record scratch" |
| transition | Whoosh / Swoosh set | yes | `whoosh-short`, `whoosh-medium`, `whoosh-long` (Pixabay) |
| transition | Riser / Uplifter | yes | `riser` (Pixabay) |
| transition | Camera Shutter / Flash | no | pixabay.com "camera shutter" |
| transition | Glitch / Digital Swipe | yes | `glitch-1..3` (Pixabay) |
| ui | Pop / Bubble Pop | yes | `pop` (Pixabay) |
| ui | Mouse Click / UI Tap | yes | `click`, `click-soft` (Pixabay) |
| ui | Keyboard Typing | yes | `typing`, `key-press` (Pixabay) |
| ui | Notification / iPhone Ding | partial | `notification-ding`, `ping` (Pixabay); the iPhone "ding" original is on myinstants.com |
| reaction | Cash Register / Ka-ching | no | pixabay.com "cash register" |
| reaction | Correct / Wrong Buzzer | yes | `correct-chime`, `wrong-buzzer` (Pixabay) |
| reaction | Anime Bonk / Boing | no | myinstants.com "Bonk" |
| reaction | Crowd "Ooh" / Wow | no | pixabay.com "crowd wow" / "crowd ooh" |

## Getting the missing ones

Blocked until the environment's Network access allows `www.myinstants.com`, `pixabay.com` and `cdn.pixabay.com`. Then for each missing sound:

1. Find 2–3 candidates; download each to `sfx/<category>/<name>-cand<N>.mp3`.
2. `python3 shorts-editor/scripts/sfx_index.py --normalize` (new files enter with `approved: false`).
3. Show the person the candidates (send the files) and keep the one they pick; rename it to the final name, delete the others, set `approved: true`, fill `license` and `source`, re-run the indexer.

Licensing: Pixabay sounds are free for commercial use. Meme originals from myinstants (Vine Boom, Fahhh, Bruh, iPhone ding, Bonk) have unclear rights. They're common on TikTok, but they can trigger claims on monetized YouTube. Record `"license": "meme / unclear"` for those.
