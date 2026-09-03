from conftest import FakeResp

from finder import sources


def test_extract_balanced_json():
    txt = 'blah window.stateData = {"a":1,"b":{"c":"}}}","d":[1,2]}}; more'
    raw = sources.extract_balanced_json(txt, "window.stateData")
    assert raw == '{"a":1,"b":{"c":"}}}","d":[1,2]}}'


def test_fetch_fl_ru(cfg, fixtures_dir, monkeypatch):
    monkeypatch.setattr(sources, "_get",
                        lambda s, u, **k: FakeResp(fixtures_dir / "fl_ru.xml"))
    cfg = dict(cfg, fl_ru_feeds=["http://x/feed.xml"])
    errors = []
    leads = sources.fetch_fl_ru(cfg, None, errors)
    assert errors == []
    assert len(leads) == 3
    titles = [x["title"] for x in leads]
    assert any("сайт-приглашение на свадьбу" in t.lower() for t in titles)
    assert all(x["url"].startswith("https://www.fl.ru/projects/") for x in leads)
    assert all(x["published_ts"] for x in leads)


def test_fetch_kwork(cfg, fixtures_dir, monkeypatch):
    monkeypatch.setattr(sources, "_get",
                        lambda s, u, **k: FakeResp(fixtures_dir / "kwork.html"))
    cfg = dict(cfg, kwork_pages=1, kwork_categories=[""])
    errors = []
    leads = sources.fetch_kwork(cfg, None, errors)
    assert errors == []
    assert len(leads) == 3
    first = leads[0]
    assert first["title"] == "Свадебный лендинг под ключ"
    assert first["url"] == "https://kwork.ru/projects/3300001"
    assert first["published_ts"] is not None
    assert first["budget"] == 15000
    assert "Бюджет 15000" in first["snippet"]


def test_fetch_telegram_prefilter(cfg, fixtures_dir, monkeypatch):
    monkeypatch.setattr(sources, "_get",
                        lambda s, u, **k: FakeResp(fixtures_dir / "telegram.html"))
    cfg = dict(cfg, telegram_channels=["workzavr"])
    errors = []
    leads = sources.fetch_telegram(cfg, None, errors, prefilter_terms=["свадеб", "лендинг"])
    assert errors == []
    assert len(leads) == 1  # таргетолог отфильтрован
    assert leads[0]["url"] == "https://t.me/workzavr/12345"
    assert leads[0]["source"] == "Telegram @workzavr"


def test_manual_cards(cfg):
    cards = sources.manual_cards(cfg)
    assert cards, "в config.json должны быть manual_links"
    assert all(c["url"].startswith("http") for c in cards)
    assert any("avito" in c["url"].lower() for c in cards)


def test_source_errors_are_collected(cfg, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("HTTP 503")
    monkeypatch.setattr(sources, "_get", boom)
    errors = []
    leads = sources.fetch_fl_ru(dict(cfg, fl_ru_feeds=["http://x"]), None, errors)
    assert leads == []
    assert errors and "503" in errors[0]
