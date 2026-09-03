# Шаблоны

Три файла компоновки — `A-kadr`, `B-razvorot`, `C-polosa` — из которых
`materialy/build/build.py` собирает работы портфолио (какой шаблон у концепции,
задаёт поле `template` в `concepts.py`). Плюс `guests.template.html` — приватный
список гостей, тема берётся от концепции.

Правьте разметку и стили здесь — изменения попадут во все лендинги на этом
шаблоне при следующей сборке.

## Плейсхолдеры `{{ИМЯ}}`

Подставляются `build.py` из концепции и из `foto-ishodniki/<slug>/images.json`.
Если после сборки останется незакрытый `{{…}}` — `build.py` падает и называет
пропущенные токены.

### Шрифты (задаёт build.py по шаблону, не по концепции)
| токен | что |
|-------|-----|
| `{{FONT_LINK}}` | `<link>` на Google Fonts со всеми начертаниями шаблона |
| `{{FONT_HEAD}}` | стек заголовков (A: Cormorant Garamond, B: Forum, C: Tenor Sans) |
| `{{FONT_TEXT}}` | стек текста (A: Manrope, B: PT Sans, C: Golos Text) |
| `{{FONT_NAME}}` | стек имён на обложке — Great Vibes во всех трёх |

### Палитра (CSS-переменные в `:root`) — из концепции
`{{C_INK}}` `{{C_INK2}}` тёмные секции · `{{C_BG}}` `{{C_BG2}}` фон и фон
чередующихся секций · `{{C_ACCENT}}` `{{C_ACCENT_DEEP}}` акцент ·
`{{C_TEXT}}` `{{C_TEXT_SOFT}}` текст · `{{C_ON_INK}}` `{{C_ON_INK_SOFT}}` текст на
тёмном · `{{C_LINE}}` `{{C_LINE_ON_INK}}` линии · `{{HERO_FOCUS}}` —
`object-position` фото обложки (напр. `50% 35%`).

### Контент
`{{NAMES}}` (имя мужчины первым) `{{INITIALS}}` `{{HERO_EYEBROW}}` `{{CITY_VENUE}}`
`{{DATE_HUMAN}}` `{{DATE_SHORT}}` `{{WHEN_VALUE}}` `{{WHEN_EXTRA}}`
`{{WHERE_VALUE}}` `{{WHERE_EXTRA}}` `{{MAP_URL}}` `{{INTRO_LEAD}}` `{{INTRO_BODY}}`
`{{PROGRAM_SUB}}` `{{PROGRAM_ROWS}}` (строки тайминга — генерит build.py)
`{{DRESSCODE_NOTE}}` `{{DRESSCODE_SWATCHES}}` `{{FAQ_ITEMS}}`
`{{RSVP_LEAD}}` `{{RSVP_EXTRA_LABEL}}` `{{RSVP_NOTE}}` `{{FOOTER_LINE}}`

### Фото
`{{IMG_HERO}}` `{{IMG_G1}}` `{{IMG_G2}}` `{{IMG_G3}}` — `data:`-URI.
`{{GCAP1}}` `{{GCAP2}}` `{{GCAP3}}` — подписи/alt к фото галереи.

### Дата, скрипт, хранилище
`{{CAL_YEAR}}` `{{CAL_MONTH_INDEX}}` (0–11) `{{CAL_DAY}}` — мини-календарь ·
`{{EVENT_DATE_ISO}}` — обратный отсчёт · `{{STORAGE_KEY}}` — ключ `window.storage`,
уникальный для работы (тот же читает `guests.template.html`) ·
`{{SCRIPT}}` — общий JS (календарь, отсчёт, появление секций, RSVP), встраивает
build.py из константы `SHARED_SCRIPT`.

## Секции лендинга (одинаковый набор во всех трёх шаблонах)

Обложка → вступление → «Когда и где» (детали + календарь + отсчёт) →
«Программа дня» → галерея → «Дресс-код» → «Гостям на заметку» (FAQ) → RSVP →
подвал.

Появление секций (`.reveal`) включается классом `js` на `<html>`; если JS не
выполнится — весь контент виден без анимации. В шаблонах A и C белый текст на
обложке защищён затемняющей заливкой; в B имена лежат на сплошной цветной панели.
