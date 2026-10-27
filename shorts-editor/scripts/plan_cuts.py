#!/usr/bin/env python3
"""Decide cut points from a word transcript ("breathless" pacing).

usage: plan_cuts.py <words.json> <cuts.json> [--overrides overrides.json]

Drops: fillers, audio events, stutters/repeated n-grams, retakes (a sentence restarted
with the same opening), isolated soft fillers, pauses > theme.cuts.max_pause.
overrides.json lets the editor correct decisions by word index:
  {"drop": [[12, 18]], "keep": [[40, 40]], "trim_start": 0.0, "trim_end": null}
Ranges are inclusive word indices. "keep" wins over every automatic rule.
"""
import argparse
from common import load_json, log, save_json, theme
from transcribe import SOFT_FILLERS, norm

def mark_repeats(words, drop):
    """Stutters and repeated phrases: 'I think I think we' -> drop the first copy."""
    toks = [w for w in words if w["kind"] == "word"]
    keys = [norm(w["text"]) for w in toks]
    for n in (4, 3, 2, 1):
        i = 0
        while i + 2 * n <= len(toks):
            a, b = keys[i:i + n], keys[i + n:i + 2 * n]
            gap = toks[i + n]["start"] - toks[i + n - 1]["end"]
            if a == b and all(a) and (n > 1 or gap < 0.6):
                for w in toks[i:i + n]:
                    drop.setdefault(w["i"], f"repeat x{n}")
                i += n
            else:
                i += 1


def mark_retakes(words, drop, window=14):
    """A restarted phrase: the run at i is spoken again from j (within `window` words),
    e.g. 'number one is the skill | number one is the skill creator' -> drop the first run.
    Needs >= 2 matching words (>= 3 when the abandoned run is longer than 2 words)."""
    toks = [w for w in words if w["kind"] == "word" and w["i"] not in drop]
    keys = [norm(w["text"]) for w in toks]
    i = 0
    while i < len(toks):
        hit = None
        for j in range(i + 1, min(len(toks), i + window)):
            k = 0
            while j + k < len(toks) and i + k < j and keys[i + k] == keys[j + k] and keys[i + k]:
                k += 1
            if k >= max(2, min(3, j - i)):
                hit = j
        if hit is not None:
            for w in toks[i:hit]:
                drop.setdefault(w["i"], "retake")
            i = hit
        else:
            i += 1


def mark_soft_fillers(words, lang, drop):
    soft = SOFT_FILLERS.get(lang, set())
    for j, w in enumerate(words):
        if w["kind"] != "word" or norm(w["text"]) not in soft:
            continue
        before = w["start"] - words[j - 1]["end"] if j > 0 else 9
        after = words[j + 1]["start"] - w["end"] if j + 1 < len(words) else 9
        if before >= 0.25 and after >= 0.25:
            drop.setdefault(w["i"], "soft filler")


def apply_ranges(ranges, fn):
    for lo, hi in ranges or []:
        for i in range(lo, hi + 1):
            fn(i)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("out")
    ap.add_argument("--overrides")
    a = ap.parse_args()

    cfg = theme()["cuts"]
    data = load_json(a.words)
    words, lang, src_dur = data["words"], data["language"], data["duration"]
    ov = load_json(a.overrides) if a.overrides else {}

    drop = {}
    for w in words:
        if w["kind"] in ("filler", "event"):
            drop[w["i"]] = w["kind"]
    mark_repeats(words, drop)
    mark_retakes(words, drop)
    mark_soft_fillers(words, lang, drop)
    apply_ranges(ov.get("drop"), lambda i: drop.__setitem__(i, "manual"))
    apply_ranges(ov.get("keep"), lambda i: drop.pop(i, None))

    t0 = float(ov.get("trim_start") or 0.0)
    t1 = float(ov.get("trim_end") or src_dur)
    kept = [w for w in words if w["i"] not in drop and w["start"] >= t0 and w["end"] <= t1]
    if not kept:
        raise SystemExit("nothing left after cutting")

    # Group kept words into runs; split a run where the pause exceeds max_pause
    # or where a dropped token sits between two kept words.
    dropped_spans = sorted((w["start"], w["end"]) for w in words if w["i"] in drop)
    runs, cur = [], [kept[0]]
    for prev, w in zip(kept, kept[1:]):
        gap = w["start"] - prev["end"]
        between = any(prev["end"] - 1e-3 <= s and e <= w["start"] + 1e-3 for s, e in dropped_spans)
        if gap > cfg["max_pause"] or between or w["i"] != prev["i"] + 1 and gap > 0.05:
            runs.append(cur)
            cur = [w]
        else:
            cur.append(w)
    runs.append(cur)

    def clamp_lead(run):
        s = run[0]["start"] - cfg["keep_lead"]
        prior = [e for _, e in dropped_spans if e <= run[0]["start"] + 1e-3]
        prior_kept = [w["end"] for w in kept if w["end"] <= run[0]["start"] + 1e-3]
        floor = max(prior + prior_kept + [t0])
        return max(s, floor)

    def clamp_tail(run):
        e = run[-1]["end"] + cfg["keep_tail"]
        nxt = [s for s, _ in dropped_spans if s >= run[-1]["end"] - 1e-3]
        nxt_kept = [w["start"] for w in kept if w["start"] >= run[-1]["end"] - 1e-3]
        ceil = min(nxt + nxt_kept + [t1])
        return min(e, ceil)

    segments, out_t, words_out = [], 0.0, []
    for run in runs:
        s, e = clamp_lead(run), clamp_tail(run)
        if e - s < 0.08:
            continue
        for w in run:
            words_out.append({"i": w["i"], "text": w["text"], "kind": w["kind"],
                              "start": round(out_t + (w["start"] - s), 3),
                              "end": round(out_t + (w["end"] - s), 3)})
        segments.append({"src_start": round(s, 3), "src_end": round(e, 3),
                         "out_start": round(out_t, 3)})
        out_t += e - s

    removed = [{"i": w["i"], "text": w["text"], "reason": drop[w["i"]],
                "start": w["start"], "end": w["end"]} for w in words if w["i"] in drop]
    out = {"language": lang, "source_duration": src_dur, "duration": round(out_t, 3),
           "segments": segments, "words": words_out, "removed": removed}
    save_json(a.out, out)
    log(f"{len(segments)} segments, {src_dur:.1f}s -> {out_t:.1f}s, "
        f"{len(removed)} tokens removed -> {a.out}")
    if out_t > 120:
        log("WARNING: cut is longer than 120 s; trim content (overrides.json drop ranges)")


if __name__ == "__main__":
    main()
