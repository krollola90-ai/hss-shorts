#!/usr/bin/env python3
"""Speaker metrics for one project -> appended to docs/speaker-log.csv (one row per video).

usage: speaker_report.py <project_dir>
Metrics: source/final length, % cut, speech rate (words/min of the final cut), fillers per minute,
pauses > 1 s (count and total), restarts (retakes the cut planner or Claude removed).
Claude reads the log before each edit (docs/voice.md links it) to tune cuts to Mark's habits and to
give him short coaching notes.
"""
import csv
import re
import sys
from pathlib import Path

from common import ROOT, load_json

FILLERS = re.compile(r"^(е+|е-е-м|м-м-м|м+|ем+|э+|ну|відповідно|соответственно|тобто|там|значить|так)$")


def main():
    p = Path(sys.argv[1])
    t = load_json(p / "transcript.json")
    c = load_json(p / "work" / "cuts.json")
    w = [x for x in t["words"] if x["kind"] == "word"]
    norm = lambda s: re.sub(r"[^\w-]", "", s.lower())
    speak_min = (w[-1]["end"] - w[0]["start"]) / 60
    gaps = [b["start"] - a["end"] for a, b in zip(w, w[1:])]
    long = [g for g in gaps if g > 1.0]
    fill = sum(1 for x in w if FILLERS.match(norm(x["text"])))
    restarts = sum(1 for r in c["removed"] if r["reason"] in ("retake", "repeat x1", "repeat x2", "manual"))
    row = {"project": p.name, "format": load_json(p / "project.json").get("format", ""),
           "source_s": round(t["duration"]), "final_s": round(c["duration"]),
           "cut_pct": round(100 * (1 - c["duration"] / t["duration"])),
           "words_per_min": round(len(c["words"]) / c["duration"] * 60),
           "fillers_per_min": round(fill / speak_min, 1), "pauses_over_1s": len(long),
           "pause_total_s": round(sum(long)), "removed_words": restarts}
    log = ROOT / "docs" / "speaker-log.csv"
    rows = list(csv.DictReader(open(log))) if log.exists() else []
    rows = [r for r in rows if r["project"] != p.name] + [{k: str(v) for k, v in row.items()}]
    with open(log, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(row))
        wr.writeheader()
        wr.writerows(rows)
    print(row)


if __name__ == "__main__":
    main()
