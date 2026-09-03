import time

from finder.aggregate import run_search


def _fake_fetchers():
    now = time.time()
    fl = [
        {"source": "FL.ru", "title": "Сайт-приглашение на свадьбу",
         "url": "https://fl.ru/projects/1", "snippet": "свадебный лендинг, бюджет 12000 руб",
         "published": "", "published_ts": now - 3600},
        {"source": "FL.ru", "title": "Смонтировать свадебное видео",
         "url": "https://fl.ru/projects/2", "snippet": "монтаж свадебного видео",
         "published": "", "published_ts": now - 7200},
    ]
    kw = [
        {"source": "Kwork", "title": "Лендинг для онлайн-курса",
         "url": "https://kwork.ru/projects/9", "snippet": "одностраничник на тильде, оплата 20000",
         "published": "", "published_ts": now - 1000},
    ]
    return {"fl_ru": lambda: fl, "kwork": lambda: kw, "telegram": lambda: []}


def test_run_search_buckets_and_new(cfg, db):
    res = run_search(cfg, db, fetchers=_fake_fetchers())
    assert len(res["exact"]) == 1
    assert res["exact"][0]["url"] == "https://fl.ru/projects/1"
    assert res["exact"][0]["budget"] == 12000
    assert res["exact"][0]["is_new"] is True
    assert len(res["similar"]) == 1
    assert res["manual"], "manual links should always be present"
    assert res["stats"]["new"] == 2

    # второй прогон — те же лиды больше не новые
    res2 = run_search(cfg, db, fetchers=_fake_fetchers())
    assert res2["stats"]["new"] == 0
    assert res2["exact"][0]["is_new"] is False


def test_run_search_survives_broken_source(cfg, db):
    def boom():
        raise RuntimeError("boom")
    fx = _fake_fetchers()
    fx["kwork"] = boom
    res = run_search(cfg, db, fetchers=fx)
    assert res["errors"] and "boom" in res["errors"][0]
    assert len(res["exact"]) == 1  # fl.ru всё равно отработал
