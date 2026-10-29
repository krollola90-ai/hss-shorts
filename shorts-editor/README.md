# shorts-editor — движок монтажа

Как пользоваться — в [README в корне](../README.md). Здесь — как устроен движок.

```
видео с телефона ─► shorts fetch/new ─► рабочая копия 1080×1920 30 fps + audio.mp3
  ─► расшифровка (ElevenLabs Scribe через коннектор │ Whisper medium бесплатно) ─► words.json
  ─► plan_cuts + overrides.json (что вырезать, что вернуть, порядок блоков) ─► cuts.json
  ─► cut (FFmpeg, по кускам) ─► cut.mp4
  ─► edit_plan.json (хук, карточки, зумы, звуки, музыка)          ◄── превью / одобрение
  ─► build_comp ─► HyperFrames-проект (субтитры, карточки, микс звука) по стилю
  ─► hyperframes render ─► finalize (−14 LUFS, проверка качества) ─► footage/edited/<имя>.mp4
```

## Команды

Запусти `./shorts` без аргументов — список. Главные:

| Команда | Что делает |
|---|---|
| `shorts fetch <имя> <ссылка-Drive> <формат>` | скачивает видео по ссылке и создаёт проект |
| `shorts new <имя> <файл> <формат>` | то же для локального файла |
| `shorts import-scribe <имя> <words.json>` | подключает расшифровку ElevenLabs |
| `shorts transcribe <имя> uk\|ru` | бесплатная расшифровка Whisper |
| `shorts cuts <имя>` | план вырезок по `overrides.json` |
| `shorts cut <имя> [--preview]` | нарезка видео |
| `shorts build <имя>` | сборка анимаций, субтитров и звука |
| `shorts check <имя>` / `shorts snap <имя> 1.5,10` | проверка и кадры для просмотра |
| `shorts preview <имя>` | черновой рендер |
| `shorts render <имя>` | финальный рендер + громкость + проверка качества |

Стиль проекта — `"style"` в `projects/<имя>/project.json` (по умолчанию из `formats/<формат>.json`).
Разово перебить: `SHORTS_STYLE=$PWD/styles/<стиль>.json ./shorts build <имя>`.

## Папки

| Путь | Что |
|---|---|
| `formats/` | шаблоны форматов (vacancy, thought, idea, vlog, edit) |
| `styles/` | стили — каталог в [docs/styles.md](docs/styles.md) |
| `scripts/` | шаги пайплайна (Python, без зависимостей кроме faster-whisper) |
| `assets/sfx/` | звуки + `manifest.json` (длительность, момент удара, лицензия) |
| `assets/music/` | музыка по настроениям + `CREDITS.md` |
| `assets/fonts/` | 7 шрифтов с кириллицей |
| `assets/vendor/` | GSAP (анимации), чтобы рендер работал без интернета |
| `projects/` | проекты видео; `work/` и `hf/` генерируются и в git не попадают |
| `footage/raw/` | исходники (в git не попадают — храним на Google Drive) |
| `footage/edited/` | готовые ролики |

## Звуки

28 звуков: удары (`bass-drop-1/2`, `boom-deep`, `hit-punch`, `sub-drop`, `double-thump`),
переходы (`whoosh-short/medium/long/up/down`, `swipe-fast`, `riser`, `glitch-1..3`, `camera-shutter`),
интерфейс (`pop`, `click`, `click-soft`, `tick`, `ping`, `notification-ding`, `typing`, `key-press`),
реакции (`correct-chime`, `wrong-buzzer`, `sparkle`). Pixabay — бесплатно для коммерции;
новые 9 синтезированы для этого репозитория (CC0). Добавить свой звук: положить в папку категории,
`python3 scripts/sfx_index.py --normalize`, поставить `"approved": true` в `manifest.json`.

## Основа

Движок основан на пайплайне Даниила Кустова (`danielkustov/recruiting-freelance`), переделан под
форматы, стили и рабочий процесс Марка.
