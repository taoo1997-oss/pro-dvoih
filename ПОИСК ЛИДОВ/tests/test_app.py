import pytest

import app as app_module
from finder import store


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "app.db")
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()


def test_index_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Поиск клиентов".encode() in r.data


def test_api_search_shape(client, monkeypatch):
    def fake_run(cfg, conn):
        return {"exact": [{"uid": "u1", "title": "t", "url": "http://x",
                           "bucket": "exact", "score": 6, "is_new": True,
                           "snippet": "", "budget": 10000, "reasons": ""}],
                "similar": [], "manual": [{"source": "Avito", "title": "a", "url": "http://a"}],
                "errors": [], "stats": {"raw": 5, "kept": 1, "new": 1}}
    monkeypatch.setattr(app_module, "run_search", fake_run)
    r = client.post("/api/search")
    assert r.status_code == 200
    data = r.get_json()
    assert set(data) >= {"exact", "similar", "manual", "errors", "stats"}
    assert data["exact"][0]["budget"] == 10000


def test_api_leads_and_archive(client):
    conn = store.connect(store.DB_PATH)
    store.upsert_leads(conn, [{
        "uid": "abc", "source": "FL.ru", "title": "Свадебный лендинг", "url": "http://l",
        "snippet": "s", "budget": 9000, "published": "", "bucket": "exact",
        "score": 6.0, "reasons": "r"}])
    conn.close()

    r = client.get("/api/leads?bucket=exact")
    assert r.status_code == 200
    assert r.get_json()["leads"][0]["uid"] == "abc"

    r = client.post("/api/archive", json={"uid": "abc", "value": 1})
    assert r.get_json()["ok"] is True
    assert client.get("/api/leads").get_json()["leads"] == []

    r = client.post("/api/archive", json={})
    assert r.status_code == 400
