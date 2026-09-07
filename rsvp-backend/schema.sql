-- Ответы гостей на приглашения (RSVP) для всех свадебных лендингов.
-- Применять:  wrangler d1 execute wedding-rsvp --remote --file=./schema.sql
-- Локально:   тот же флаг --local вместо --remote

-- Одна строка = одна заявка одного гостя. wedding — slug пары из build.py.
-- guests хранится как JSON-массив строк (["Имя Фамилия", ...]).
CREATE TABLE IF NOT EXISTS rsvp (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  wedding TEXT NOT NULL,
  name    TEXT NOT NULL,
  guests  TEXT NOT NULL DEFAULT '[]',
  note    TEXT NOT NULL DEFAULT '',
  ts      INTEGER NOT NULL,          -- Date.now() на момент отправки
  ip      TEXT                       -- для разбора спама, гостям не показывается
);

CREATE INDEX IF NOT EXISTS idx_rsvp_wedding ON rsvp(wedding, ts);
