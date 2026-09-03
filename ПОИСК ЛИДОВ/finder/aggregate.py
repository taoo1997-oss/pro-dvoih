"""Собирает все источники, оценивает, кладёт в базу, возвращает результат для UI."""
import time

from . import sources, store
from .matching import score_lead


def _age_hours(ts):
    if not ts:
        return None
    return max(0.0, (time.time() - ts) / 3600.0)


def run_search(cfg, conn, session=None, fetchers=None):
    """fetchers — можно подменить в тестах. По умолчанию реальные."""
    session = session or sources.make_session()
    errors = []
    prefilter = list(cfg.get("keywords_wedding", [])) + ["лендинг", "landing", "одностранич", "сайт-визитк", "промостраниц"]

    raw = []
    fx = fetchers or {
        "fl_ru": lambda: sources.fetch_fl_ru(cfg, session, errors),
        "kwork": lambda: sources.fetch_kwork(cfg, session, errors),
        "telegram": lambda: sources.fetch_telegram(cfg, session, errors, prefilter_terms=prefilter),
    }
    for name, fn in fx.items():
        try:
            got = fn()
            raw.extend(got or [])
        except Exception as ex:  # noqa: BLE001
            errors.append(f"{name}: {ex}")

    scored = []
    for item in raw:
        res = score_lead(item.get("title", ""), item.get("snippet", ""), cfg,
                         age_hours=_age_hours(item.get("published_ts")))
        if res["bucket"] == "drop":
            continue
        scored.append({
            "uid": item.get("url") or (item.get("source", "") + "|" + item.get("title", "")),
            "source": item.get("source", ""),
            "title": item.get("title", "").strip() or "(без заголовка)",
            "url": item.get("url", ""),
            "snippet": item.get("snippet", "").strip(),
            "budget": item.get("budget") or res["budget"],
            "published": item.get("published", ""),
            "published_ts": item.get("published_ts"),
            "bucket": res["bucket"],
            "score": res["score"],
            "reasons": " · ".join(res["reasons"]),
        })

    # дедуп по uid, оставляем лучший score
    dedup = {}
    for s in scored:
        cur = dedup.get(s["uid"])
        if cur is None or s["score"] > cur["score"]:
            dedup[s["uid"]] = s
    scored = list(dedup.values())

    new_uids = store.upsert_leads(conn, scored)
    store.record_run(conn, len(scored), len(new_uids), errors)

    new_set = set(new_uids)
    for s in scored:
        s["is_new"] = s["uid"] in new_set

    scored.sort(key=lambda x: (x["bucket"] != "exact", -x["score"],
                               -(x["published_ts"] or 0)))
    return {
        "exact": [s for s in scored if s["bucket"] == "exact"],
        "similar": [s for s in scored if s["bucket"] == "similar"],
        "manual": sources.manual_cards(cfg),
        "errors": errors,
        "stats": {
            "raw": len(raw),
            "kept": len(scored),
            "new": len(new_uids),
            "ts": time.time(),
        },
    }
