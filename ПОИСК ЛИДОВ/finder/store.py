"""SQLite-хранилище: кэш найденных запросов + отметка «уже видел» + история поисков."""
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "leads.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
  uid          TEXT PRIMARY KEY,
  source       TEXT,
  title        TEXT,
  url          TEXT,
  snippet      TEXT,
  budget       INTEGER,
  published    TEXT,
  bucket       TEXT,
  score        REAL,
  reasons      TEXT,
  first_seen   REAL,
  last_seen    REAL,
  archived     INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS runs (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts        REAL,
  found     INTEGER,
  new_count INTEGER,
  errors    TEXT
);
"""


def connect(db_path=None):
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def upsert_leads(conn, leads):
    """leads: список dict с ключами uid, source, title, url, snippet, budget,
    published, bucket, score, reasons(str). Возвращает список uid, которых
    раньше не было (новые)."""
    now = time.time()
    new_uids = []
    for ld in leads:
        row = conn.execute("SELECT uid, archived FROM leads WHERE uid = ?", (ld["uid"],)).fetchone()
        if row is None:
            new_uids.append(ld["uid"])
            conn.execute(
                """INSERT INTO leads (uid, source, title, url, snippet, budget, published,
                   bucket, score, reasons, first_seen, last_seen)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (ld["uid"], ld["source"], ld["title"], ld["url"], ld.get("snippet", ""),
                 ld.get("budget"), ld.get("published", ""), ld["bucket"], ld.get("score", 0),
                 ld.get("reasons", ""), now, now),
            )
        else:
            conn.execute(
                """UPDATE leads SET last_seen=?, bucket=?, score=?, reasons=?, snippet=?, budget=?
                   WHERE uid=?""",
                (now, ld["bucket"], ld.get("score", 0), ld.get("reasons", ""),
                 ld.get("snippet", ""), ld.get("budget"), ld["uid"]),
            )
    conn.commit()
    return new_uids


def record_run(conn, found, new_count, errors):
    conn.execute("INSERT INTO runs (ts, found, new_count, errors) VALUES (?,?,?,?)",
                 (time.time(), found, new_count, "; ".join(errors)))
    conn.commit()


def get_leads(conn, bucket=None, include_archived=False, since_ts=None):
    q = "SELECT * FROM leads WHERE 1=1"
    args = []
    if bucket:
        q += " AND bucket = ?"
        args.append(bucket)
    if not include_archived:
        q += " AND archived = 0"
    if since_ts:
        q += " AND last_seen >= ?"
        args.append(since_ts)
    q += " ORDER BY score DESC, last_seen DESC"
    return [dict(r) for r in conn.execute(q, args).fetchall()]


def set_archived(conn, uid, value=1):
    conn.execute("UPDATE leads SET archived=? WHERE uid=?", (value, uid))
    conn.commit()


def last_run_ts(conn):
    row = conn.execute("SELECT ts FROM runs ORDER BY id DESC LIMIT 1 OFFSET 1").fetchone()
    return row["ts"] if row else 0.0


def recent_runs(conn, limit=10):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
