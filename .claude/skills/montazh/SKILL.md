---
name: montazh
description: Mark's personal editing menu. Use when Mark writes "монтаж" (or "смонтируй", "новое видео") — ask which format, pick the format preset, then run the shorts-editor pipeline with it.
---

# «Монтаж» — personal editing menu

Mark records videos on his phone and keeps all sources on Google Drive. This skill is the
entry point; the actual editing is done by the `shorts-editor` skill (same repo), driven by
the format preset chosen here. Talk to Mark in Russian.

## 1. Ask (one AskUserQuestion, two questions)

1. **Что монтируем?** — Вакансия / Новости / Мысль / О себе (Other = free text: Идея, Влог, Эдит, Совет, Ответ…).
2. **Откуда видео?** — «новые во Входящих» (default) / ссылка на Google Drive / файл на ноутбуке.

Inbox via the Google Drive connector: folder ids are in `shorts-editor/drive.json`
(`inbox.<format>`). `search_files` with `parentId = '<id>' and mimeType contains 'video/'` lists new
videos (a same-name .txt next to a video is Mark's note — read it). The connector can't move video
bytes (base64 through the chat), so download with `shorts fetch <name> https://drive.google.com/file/d/<id>/view <format>`;
this needs «01_Входящие» shared as "anyone with the link". If it returns a sign-in page, ask Mark to
share the folder. Deliver finished videos with SendUserFile (and, if the laptop is linked and Google
Drive for desktop is installed, write them into the synced «02_Готово» folder).

If Mark already said the format or pasted a link, skip that question.

## 2. Load the preset

`shorts-editor/formats/<format>.json` — style, target length, structure, overlay rules,
music mood, ending. Format keys: vacancy, news, thought, motivation, idea, about, vlog, edit, advice, answer. Presets marked `"status": "draft"` have never been tested on a real video:
before the first edit in that format, show Mark 3 style options on frames of his video
(build the project with each candidate via `SHORTS_STYLE=$PWD/shorts-editor/styles/<s>.json shorts build`,
snapshot 3 moments, stack into one image; catalogue of styles: `shorts-editor/docs/styles.md`) and
save his choice into the preset (`"style"`, `"status": "approved"`), then commit.

Before cutting, read `shorts-editor/docs/voice.md` (how Mark talks, what to keep, what to cut).

## 2b. Visual brief (formats with `"visuals": "brief"` — thoughts, motivation, about me, ideas, news, advice, answers, vlog)

Mark's rule: for these videos **don't start editing right away**. First:

1. Transcribe and read the whole text carefully. Work out the logic: what is the one idea, what is
   the hook, which order makes it clearest, what to cut. Write the cleaned script (with the new
   order) and the captions.
2. Find every moment a picture would help the viewer understand: people he mentions (e.g. Michael
   Jackson young), objects and places (a guitar, a city, a warehouse), events, abstract ideas
   (alter ego → mirror/two faces), numbers. Aim for ~8–12 visuals per minute of final video;
   for `motivation` follow the variant: **doc** (ref MM1) ~20–25/min, full-screen photos, a 4-photo
   `grid` hook, step numbers; **panel** (ref MM2) ~12–18/min, `layout: top`, symbolic images
   (paintings, b&w photos, surreal collages). Ask Mark which variant if the video doesn't make it obvious.
3. Send Mark a **visual brief** (SendUserMessage, a table) and stop until he answers:

   | № | Момент (фраза) | Что нужно | Фото или видео | Имя файла |
   |---|---|---|---|---|
   | 1 | «…как Майкл Джексон…» | Майкл Джексон в молодости, на сцене | фото | 01-jackson.jpg |
   | 2 | «…в детстве играл на гитаре…» | гитара; лучше твоё детское фото с гитарой | фото / видео 3–5 с | 02-guitar.jpg |

   Mark finds the files himself (Claude never downloads photos of public figures from the web).
   For each item also say what Claude will do if Mark has nothing: an emoji, a text card, an
   icon — or, only with Mark's OK, an AI-generated illustration (ElevenLabs, costs credits).
4. Create the folder `01_Входящие/<рубрика>/<project>_визуалы` with the Google Drive connector
   (`create_file`, folder mime type, parent from `drive.json`) and tell Mark to upload there with
   the file names from the table. The folder inherits the inbox's link sharing.
5. When Mark says «скинул», list the folder (`search_files parentId = '<folder id>'`), download each
   file with `shorts asset <project> <file id> <file name>`, and place them: photos → `image`
   (`layout: full` for story moments, `top` for the panel variant, `card` for references; `"number": N` for steps;
   `grid` overlay with 4 images for a collage hook), videos → `video` B-roll; time each one
   to the exact word from `work/cuts.json`. Missing items → the fallback from the brief.
6. Then continue with the normal edit and a draft preview.

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

## 4. Learn (after every video)

1. `python3 shorts-editor/scripts/speaker_report.py shorts-editor/projects/<name>` — appends metrics
   to `docs/speaker-log.csv`.
2. Update «Наблюдения» in `docs/voice.md`: what was new in this video (new filler, new habit, a
   strength, how the hook/ending went), compared with the log. Keep it about **how Mark speaks and
   presents** (pace, structure, clarity, warmth) — no psychological or personality diagnoses.
3. Give Mark 1–2 short, kind tips for the next recording in the final message (only when useful).
4. Tune defaults from the data: e.g. if pauses get shorter, relax `cuts.max_pause`; if a new filler
   appears often, add it to the filler list in `scripts/transcribe.py`.
5. When Mark corrects something that should apply to all videos of a format or to his voice
   («всегда без капса», «эту фразу не режь»), write it into the preset or `docs/voice.md`. Commit.
