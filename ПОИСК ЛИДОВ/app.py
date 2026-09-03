"""Поиск клиентов на свадебные лендинги — локальное приложение.

Запуск:  python app.py   (или двойной клик по run.bat)
Откроется http://127.0.0.1:5017
"""
import sys
import threading
import webbrowser

from flask import Flask, jsonify, render_template, request

from finder import sources, store
from finder.aggregate import run_search
from finder.config import load_config

app = Flask(__name__)
HOST, PORT = "127.0.0.1", 5017


@app.get("/")
def index():
    conn = store.connect()
    runs = store.recent_runs(conn, 8)
    conn.close()
    return render_template("index.html", runs=runs)


@app.post("/api/search")
def api_search():
    cfg = load_config()
    conn = store.connect()
    try:
        result = run_search(cfg, conn)
    finally:
        conn.close()
    return jsonify(result)


@app.get("/api/leads")
def api_leads():
    bucket = request.args.get("bucket") or None
    include_archived = request.args.get("archived") == "1"
    conn = store.connect()
    try:
        rows = store.get_leads(conn, bucket=bucket, include_archived=include_archived)
    finally:
        conn.close()
    return jsonify({"leads": rows, "manual": sources.manual_cards(load_config())})


@app.post("/api/archive")
def api_archive():
    data = request.get_json(force=True, silent=True) or {}
    uid = data.get("uid")
    value = int(data.get("value", 1))
    if not uid:
        return jsonify({"ok": False, "error": "no uid"}), 400
    conn = store.connect()
    try:
        store.set_archived(conn, uid, value)
    finally:
        conn.close()
    return jsonify({"ok": True})


@app.get("/api/runs")
def api_runs():
    conn = store.connect()
    try:
        return jsonify({"runs": store.recent_runs(conn, 20)})
    finally:
        conn.close()


def _open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, _open_browser).start()
    app.run(host=HOST, port=PORT, debug=False)
