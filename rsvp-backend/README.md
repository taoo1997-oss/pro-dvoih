# rsvp-backend

Один Cloudflare Worker + база D1 на все свадебные лендинги. Хранит ответы
гостей (RSVP), которые раньше жили в `window.storage` артефактов Claude.

Разделение по свадьбам — поле `wedding` (slug пары из `materialy/build/build.py`).

## Эндпоинты

| Метод | Путь | Тело / параметры | Ответ |
|---|---|---|---|
| `POST` | `/rsvp` | `{wedding, name, guests:[], note}` | `{ok:true}` |
| `GET` | `/rsvp?wedding=<slug>` | — | `{list:[{name,guests,note,ts}], count, people}` |

CORS открыт для всех доменов — лендинги живут на разных доменах клиентов.

## Первый деплой

Аккаунт Cloudflare — тот же, что у `calendar-backend` (общий с проектом
«Календарь»). Квота D1 на бесплатном тарифе делится на аккаунт: 100 000 записей
строк в сутки, 5 ГБ. Для свадеб (десятки гостей на свадьбу) — с большим запасом.

```bash
cd rsvp-backend
npm install

# 1. создать базу — команда напечатает database_id
npx wrangler d1 create wedding-rsvp

# 2. вставить этот id в wrangler.toml (поле database_id)

# 3. создать таблицы в облачной базе
npm run db:migrate

# 4. выкатить воркер — напечатает URL вида
#    https://rsvp-backend.<ваш-сабдомен>.workers.dev
npm run deploy
```

Полученный URL прописать в `materialy/build/build.py` — константа `RSVP_API`
вверху файла. После этого пересобрать лендинги (`python build.py`).

## Локальная разработка

```bash
npm run db:migrate:local   # таблицы в локальной базе
npm run dev                # воркер на http://localhost:8787
```

## Обновление

Правки в `src/index.js` → `npm run deploy`. Правки схемы → дописать в
`schema.sql` (через `IF NOT EXISTS` / `ALTER TABLE`) и `npm run db:migrate`.

## Посмотреть заявки вручную

```bash
npx wrangler d1 execute wedding-rsvp --remote \
  --command "SELECT wedding, name, guests, note FROM rsvp ORDER BY ts DESC LIMIT 50"
```
