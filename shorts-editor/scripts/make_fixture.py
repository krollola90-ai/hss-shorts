#!/usr/bin/env python3
"""Synthetic test clip for pipeline self-tests (needs espeak-ng).

usage: make_fixture.py <out_dir>
Writes <out_dir>/raw.mp4 (1080x1920 test pattern + robot speech with fillers, a stutter,
a retake and long pauses) and <out_dir>/words.json with approximate word timings, so
plan_cuts -> cut -> build_comp -> render -> finalize can run without any API.
"""
import sys
import tempfile
import wave
from pathlib import Path

from common import duration, log, run, save_json

# (text, pause_after_seconds). Fillers/retakes are deliberate.
SCRIPT = [
    ("Five Claude skills barely anyone knows about.", 0.25),
    ("Um,", 0.5),
    ("Number one is the skill", 0.2),
    ("Number one is the skill creator.", 0.9),
    ("It writes skills for you in like", 0.1),
    ("like two minutes.", 0.7),
    ("Uh,", 0.4),
    ("Ninety two percent of people never open it.", 1.2),
]


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    words, t = [], 0.0
    with tempfile.TemporaryDirectory() as td:
        parts = []
        for n, (text, pause) in enumerate(SCRIPT):
            wav = Path(td) / f"p{n}.wav"
            run(["espeak-ng", "-v", "en-us", "-s", "175", "-w", wav, text])
            d = duration(wav)
            toks = text.split()
            total_chars = sum(len(x) for x in toks)
            cur = t + 0.05
            speak = d - 0.1
            for tok in toks:
                wd = speak * len(tok) / total_chars
                kind = "filler" if tok.lower().strip(",.") in ("um", "uh") else "word"
                words.append({"text": tok, "start": round(cur, 3), "end": round(cur + wd * 0.92, 3),
                              "kind": kind, "speaker": "speaker_0"})
                cur += wd
            sil = Path(td) / f"s{n}.wav"
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                 "anullsrc=r=22050:cl=mono", "-t", str(pause), sil])
            parts += [wav, sil]
            t += d + pause
        lst = Path(td) / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        speech = Path(td) / "speech.wav"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
             "-ar", "48000", speech])
        dur = duration(speech)
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             f"testsrc2=size=1080x1920:rate=30:duration={dur}", "-i", speech,
             "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-shortest", out / "raw.mp4"])
    for i, w in enumerate(words):
        w["i"] = i
    save_json(out / "words.json", {"engine": "fixture", "language": "en",
                                   "duration": duration(out / "raw.mp4"), "words": words})
    log(f"fixture -> {out}")


if __name__ == "__main__":
    main()
