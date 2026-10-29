---
name: montazh
description: Mark's personal editing menu. Use when Mark writes "монтаж" (or "смонтируй", "новое видео") — ask which format, pick the format preset, then run the shorts-editor pipeline with it.
---

# «Монтаж» — personal editing menu

Mark records videos on his phone and keeps all sources on Google Drive. This skill is the
entry point; the actual editing is done by the `shorts-editor` skill (same repo), driven by
the format preset chosen here. Talk to Mark in Russian.

## 1. Ask (one AskUserQuestion, two questions)

1. **Что монтируем?** — Вакансия / Мысль / Идея / Влог / Эдит (Other = free text).
2. **Откуда видео?** — ссылка на Google Drive (Mark pastes it) / папка «01_Входящие» на Диске
   (via the Google Drive connector, if connected) / файл на ноутбуке (linked computer folder).

If Mark already said the format or pasted a link, skip that question.

## 2. Load the preset

`shorts-editor/formats/<format>.json` — style, target length, structure, overlay rules,
music mood, ending. Format keys: vacancy, thought, idea, vlog, edit. Presets marked `"status": "draft"` have never been tested on a real video:
before the first edit in that format, show Mark 3 style options on frames of his video
(build the project with each candidate via `SHORTS_STYLE=$PWD/shorts-editor/styles/<s>.json shorts build`,
snapshot 3 moments, stack into one image; catalogue of styles: `shorts-editor/docs/styles.md`) and
save his choice into the preset (`"style"`, `"status": "approved"`), then commit.

## 3. Edit

Follow `shorts-editor` SKILL.md steps 1–7 with these rules:

- Project name: `<format>-<YYYYMMDD>-<short-topic>` (e.g. `vacancy-20261029-temu-strykow`).
- Intake: `shorts fetch <name> <drive-link> <format>` (or `shorts new <name> <file> <format>`) — it
  writes the preset's style into `project.json`. Mark may ask for another style: edit `"style"` there.
- Language: transcribe with ElevenLabs while credits last; otherwise Whisper medium (free).
- Story order follows the preset's `structure`; keep every fact, drop fillers/retakes/off-camera talk.
- Ending: preset's `ending` text unless Mark says otherwise.
- Checkpoint: show a draft preview (or, for a format already approved and a straightforward
  video, go straight to final and say so).
- Deliver with SendUserFile; when the Drive connector is available, also upload to «02_Готово».

## 4. Learn

When Mark corrects something that should apply to all future videos of that format
(«всегда без капса», «концовка короче»), update the preset file and commit.
