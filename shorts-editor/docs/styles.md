# Каталог стилей

![Все стили](img/styles.jpg)

Слева на каждой паре — хук, справа — карточка-список и субтитры. Видео: вакансия Тересин.

| Стиль | Файл | Субтитры | Темп | Где использовали |
|---|---|---|---|---|
| Белый минимал | `styles/white-minimal.json` | белые, капс, активное слово ярче | паузы до 0,3 с, зум каждые 2–4 с | Бидгощ, Лодзь |
| Белый минимал · быстрый | `styles/white-minimal-fast.json` | как выше | паузы до 0,22 с, зум каждые 1,6–3 с | Тересин — **стиль вакансий по умолчанию** |
| Классика · жёлтый | `styles/yellow-classic.json` | активное слово жёлтое | как белый минимал | Познань |
| Динамика · голубой | `styles/blue-dynamic.json` | 2 слова, крупнее, активное голубое | паузы до 0,18 с, зум каждые 1,4–2,4 с | Temu Stryków |
| Спокойный · зелёный | `styles/green-calm.json` | без капса, активное зелёное | паузы до 0,45 с, мягкие редкие зумы | — |
| Тёмные плашки | `styles/dark-plates.json` | на тёмной подложке | обычный | — |
| Чистый | `styles/clean.json` | без капса, матовые карточки | обычный | — |

## Шрифты

![Шрифты](img/fonts.jpg)

В любом стиле: `"font_family": "Montserrat"` (Inter, Montserrat, Unbounded, Rubik, Manrope, Oswald, Nunito).

## Что можно менять в стиле

| Хочу… | Поле |
|---|---|
| другой цвет акцента | `colors.accent`, `colors.accent_ink`, `colors.stat` |
| цвет хука | `hook.bg`, `hook.ink`, `hook.alt_bg`, `hook.alt_ink` |
| больше/меньше слов в субтитре, размер, капс | `captions.words_per_group`, `font_size`, `min_font_size`, `uppercase` |
| неактивные слова ярче/темнее | `captions.idle_color` |
| выделение цифр | `captions.emphasis_style`: `plate` (плашка) или цвет |
| чаще/реже зумы, сила | `zoom.min_interval`, `max_interval`, `scales` |
| резче/мягче резать паузы | `cuts.max_pause`, `keep_lead`, `keep_tail` |
| громкость голоса, звуков, музыки | `audio.voice_lufs`, `sfx_db`, `music_db` |
| темнее карточки | `colors.glass` |

Новый стиль = копия любого файла в `styles/` с другим именем и `title`.
