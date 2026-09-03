"""Источники запросов. Каждая функция возвращает список «сырых» лидов:
{source, title, url, snippet, published (строка), published_ts (float|None)}.
Ошибки не роняют поиск — собираются в errors.
"""
import html
import json
import re
import time
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ru-RU,ru;q=0.9",
                      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    return s


def _get(session, url, timeout=20, tries=2):
    last = None
    for i in range(tries):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = str(e)[:120]
        time.sleep(1.2 * (i + 1))
    raise RuntimeError(last or "unknown error")


def extract_balanced_json(text, marker):
    """Вырезает первый сбалансированный {...} после подстроки marker."""
    i = text.find(marker)
    if i < 0:
        return None
    i = text.find("{", i)
    if i < 0:
        return None
    depth = 0
    instr = False
    esc = False
    for j in range(i, len(text)):
        c = text[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
        else:
            if c == '"':
                instr = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[i:j + 1]
    return None


def clean(text):
    """Снять html-теги и сущности, сжать пробелы."""
    text = re.sub(r"<[^>]+>", " ", html.unescape(str(text or "")))
    return re.sub(r"\s+", " ", text).strip()


def _struct_time_to_ts(st):
    if not st:
        return None
    try:
        return time.mktime(st)
    except (OverflowError, ValueError):
        return None


# ---------------------------------------------------------------- fl.ru (RSS)
def fetch_fl_ru(cfg, session, errors):
    out = []
    seen = set()
    for url in cfg.get("fl_ru_feeds", []):
        try:
            r = _get(session, url, timeout=20)
            feed = feedparser.parse(r.content)
            if feed.bozo and not feed.entries:
                errors.append(f"fl.ru {url}: не разобран RSS")
                continue
            for e in feed.entries:
                link = e.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                out.append({
                    "source": "FL.ru",
                    "title": clean(e.get("title", "")),
                    "url": link,
                    "snippet": clean(e.get("summary", ""))[:600],
                    "published": e.get("published", ""),
                    "published_ts": _struct_time_to_ts(e.get("published_parsed")),
                })
        except Exception as ex:  # noqa: BLE001
            errors.append(f"fl.ru {url}: {ex}")
    return out


# ---------------------------------------------------------------- kwork (JSON в HTML)
def fetch_kwork(cfg, session, errors):
    out = []
    seen = set()
    pages = int(cfg.get("kwork_pages", 3))
    for cat in cfg.get("kwork_categories", [""]):
        for page in range(1, pages + 1):
            base = "https://kwork.ru/projects"
            params = []
            if cat:
                params.append(f"c={cat}")
            if page > 1:
                params.append(f"page={page}")
            url = base + ("?" + "&".join(params) if params else "")
            try:
                r = _get(session, url, timeout=25)
                r.encoding = "utf-8"
                raw = extract_balanced_json(r.text, "window.stateData")
                if not raw:
                    errors.append(f"kwork {url}: не найден stateData")
                    break
                data = json.loads(raw)
                wants = (data.get("wantsListData") or {}).get("wants") or data.get("wants") or []
                if not wants:
                    break
                for w in wants:
                    wid = str(w.get("id", ""))
                    if not wid or wid in seen:
                        continue
                    seen.add(wid)
                    budget = None
                    for key in ("priceLimit", "getPriceThreshold", "possiblePriceLimit"):
                        v = w.get(key)
                        try:
                            fv = float(str(v).replace(" ", "")) if v not in (None, "", "0", "0.00") else None
                        except (TypeError, ValueError):
                            fv = None
                        if fv:
                            budget = int(fv)
                            break
                    dt = w.get("date_create") or w.get("date_active") or ""
                    ts = None
                    if dt:
                        try:
                            ts = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").replace(
                                tzinfo=timezone.utc).timestamp()
                        except ValueError:
                            ts = None
                    out.append({
                        "source": "Kwork",
                        "title": clean(w.get("name") or w.get("title") or ""),
                        "url": f"https://kwork.ru/projects/{wid}",
                        "snippet": clean(w.get("description", ""))[:600],
                        "published": dt,
                        "published_ts": ts,
                        "budget": budget,
                    })
            except Exception as ex:  # noqa: BLE001
                errors.append(f"kwork {url}: {ex}")
                break
    return out


# ---------------------------------------------------------------- telegram (web-превью)
def fetch_telegram(cfg, session, errors, prefilter_terms=None):
    out = []
    prefilter_terms = [t.lower() for t in (prefilter_terms or [])]
    for ch in cfg.get("telegram_channels", []):
        url = f"https://t.me/s/{ch}"
        try:
            r = _get(session, url, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            for wrap in soup.select(".tgme_widget_message_wrap"):
                tx = wrap.select_one(".tgme_widget_message_text")
                if tx is None:
                    continue
                text = tx.get_text(" ", strip=True)
                low = text.lower()
                if prefilter_terms and not any(t in low for t in prefilter_terms):
                    continue
                a = wrap.select_one("a.tgme_widget_message_date")
                link = a["href"] if a and a.has_attr("href") else url
                tm = wrap.select_one("time")
                ts = None
                published = ""
                if tm and tm.has_attr("datetime"):
                    published = tm["datetime"]
                    try:
                        ts = datetime.fromisoformat(published.replace("Z", "+00:00")).timestamp()
                    except ValueError:
                        ts = None
                out.append({
                    "source": f"Telegram @{ch}",
                    "title": text.split("\n")[0][:120] or f"Сообщение @{ch}",
                    "url": link,
                    "snippet": text[:600],
                    "published": published,
                    "published_ts": ts,
                })
        except Exception as ex:  # noqa: BLE001
            errors.append(f"telegram @{ch}: {ex}")
    return out


# ---------------------------------------------------------------- ручные ссылки
def manual_cards(cfg):
    cards = []
    for m in cfg.get("manual_links", []):
        cards.append({
            "source": m.get("source", "Ссылка"),
            "title": m.get("title", m.get("url", "")),
            "url": m.get("url", ""),
            "snippet": m.get("note", ""),
            "published": "",
            "published_ts": None,
        })
    return cards


ALL_FETCHERS = {
    "fl_ru": fetch_fl_ru,
    "kwork": fetch_kwork,
    "telegram": fetch_telegram,
}
