#!/usr/bin/env python3
"""Word-level transcription: ElevenLabs Scribe first, local faster-whisper fallback.

usage: transcribe.py <video> <out_words.json> [--language en|ru|uk|es] [--engine auto|scribe|whisper]

Output (normalized, engine-independent):
{ "engine": "scribe", "language": "en", "duration": 61.2,
  "words": [ {"i": 0, "text": "Hello", "start": 0.12, "end": 0.40,
              "kind": "word"|"filler"|"event", "speaker": "speaker_0"} ] }
"""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from common import duration, env, log, run, save_json

SCRIBE_URL = "https://api.elevenlabs.io/v1/speech-to-text"

# Hesitation tokens per language. Matched on the lowercased word with punctuation stripped.
FILLERS = {
    "en": {"um", "umm", "uh", "uhh", "uh-huh", "er", "erm", "ah", "hmm", "mm", "mhm"},
    "ru": {"э", "ээ", "эээ", "эм", "эмм", "мм", "ммм", "а-а", "ну-у", "кхм", "хм"},
    "uk": {"е", "ее", "еее", "ем", "емм", "мм", "ммм", "хм", "кхм"},
    "es": {"eh", "ehh", "em", "emm", "mm", "mmm", "este", "ehm", "hmm"},
}
# Soft fillers are only dropped when isolated by pauses (decided in plan_cuts.py).
SOFT_FILLERS = {
    "en": {"like", "so", "basically", "actually", "literally", "you know"},
    "ru": {"ну", "типа", "короче", "вот", "как бы", "значит"},
    "uk": {"ну", "типу", "короче", "от", "як би", "значить"},
    "es": {"pues", "bueno", "o sea", "tipo", "entonces"},
}


def norm(t):
    return re.sub(r"[^\w\-]+", "", t.lower(), flags=re.UNICODE)


def classify(text, lang):
    n = norm(text)
    all_fillers = set().union(*FILLERS.values())
    if n in FILLERS.get(lang, set()) or (lang not in FILLERS and n in all_fillers):
        return "filler"
    return "word"


def extract_audio(video, out):
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "flac", out])


def scribe(audio, language):
    key = env("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY not set")
    model = env("ELEVENLABS_STT_MODEL", "scribe_v1")
    cmd = ["curl", "-sS", "--fail-with-body", "-m", "900", "-X", "POST", SCRIBE_URL,
           "-H", f"xi-api-key: {key}",
           "-F", f"model_id={model}", "-F", f"file=@{audio}",
           "-F", "timestamps_granularity=word", "-F", "tag_audio_events=true",
           "-F", "diarize=false"]
    if language:
        cmd += ["-F", f"language_code={language}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Scribe failed: {r.stdout[:400]} {r.stderr[:400]}")
    data = json.loads(r.stdout)
    lang = (data.get("language_code") or language or "en")[:2]
    words = []
    for w in data.get("words", []):
        if w.get("type") == "spacing":
            continue
        kind = "event" if w.get("type") == "audio_event" else classify(w["text"], lang)
        words.append({"text": w["text"].strip(), "start": float(w["start"]),
                      "end": float(w["end"]), "kind": kind,
                      "speaker": w.get("speaker_id") or "speaker_0"})
    return "scribe", lang, words


# Priming text makes Whisper keep hesitations instead of cleaning them up.
WHISPER_PROMPTS = {
    "en": "Umm, so, uh, I was like, hmm, let me think. Okay, um, here's the thing.",
    "ru": "Ну, э-э, короче, ммм, дай подумать. Так, э, вот в чём дело.",
    "uk": "Ну, е-е, короче, ммм, дай подумати. Так, е, ось у чому справа.",
    "es": "Eh, pues, este, mmm, déjame pensar. Bueno, eh, la cosa es así.",
}


def whisper(audio, language):
    from faster_whisper import WhisperModel  # imported lazily: optional dependency
    model_name = env("WHISPER_MODEL", "small")
    log(f"faster-whisper model={model_name} (first run downloads it from huggingface.co)")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segs, info = model.transcribe(audio, language=language, word_timestamps=True,
                                  vad_filter=False, beam_size=5,
                                  initial_prompt=WHISPER_PROMPTS.get(language or "en"),
                                  condition_on_previous_text=False)
    lang = language or info.language
    words = []
    for s in segs:
        for w in s.words or []:
            words.append({"text": w.word.strip(), "start": float(w.start), "end": float(w.end),
                          "kind": classify(w.word, lang), "speaker": "speaker_0"})
    return "whisper", lang, words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--language", default=None, help="ISO-639-1: en, ru, uk, es")
    ap.add_argument("--engine", default="auto", choices=["auto", "scribe", "whisper"])
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        audio = str(Path(td) / "audio.flac")
        extract_audio(a.video, audio)
        result = None
        if a.engine in ("auto", "scribe"):
            try:
                result = scribe(audio, a.language)
            except Exception as e:  # network blocked, no key, quota exhausted, ...
                if a.engine == "scribe":
                    raise
                log(f"Scribe unavailable -> falling back to whisper: {e}")
        if result is None:
            result = whisper(audio, a.language)

    engine, lang, words = result
    words = [w for w in words if w["text"]]
    for i, w in enumerate(words):
        w["i"] = i
    out = {"engine": engine, "language": lang, "duration": duration(a.video), "words": words}
    save_json(a.out, out)
    n_fill = sum(w["kind"] == "filler" for w in words)
    log(f"{engine}: {len(words)} tokens, {n_fill} fillers, lang={lang} -> {a.out}")


if __name__ == "__main__":
    main()
