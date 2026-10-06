# -*- coding: utf-8 -*-
"""
Качает фото с Unsplash под каждую концепцию, пережимает Pillow,
кладёт исходники в materialy/foto-ishodniki/<slug>/ и пишет туда images.json
с data:URI для встраивания в лендинг.

Запуск:  python materialy/build/fetch_images.py
Повторный запуск перекачивает всё заново (можно --skip-existing).

  python materialy/build/fetch_images.py --wide-hero
докачивает только hero-wide.jpg (2000×1250, тот же кадр, что hero) для шаблонов
с отдельными файлами фото (WEB_IMG_TEMPLATES в build.py). Это обложка для
горизонтальных экранов: портретная hero.jpg на десктопе растягивается и мылится.
"""
import base64
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

from concepts import CONCEPTS, FALLBACK_POOL
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "materialy" / "foto-ishodniki"

# роль -> (ширина, высота, стартовое качество jpeg, потолок веса в КБ)
SPECS = {
    "hero": (1200, 1650, 74, 185),
    "g1":   (900, 1350, 74, 130),
    "g2":   (880, 1100, 74, 125),
    "g3":   (880, 1100, 74, 125),
}
ROLE_POOL = {"hero": "couple", "g1": "floral", "g2": "scene", "g3": "table"}

UA = {"User-Agent": "Mozilla/5.0 (portfolio build script)"}


def unsplash_url(photo_id, w, h, crop="entropy"):
    return (f"https://images.unsplash.com/photo-{photo_id}"
            f"?w={w}&h={h}&fit=crop&crop={crop}&auto=format&q=82&fm=jpg")


def download(photo_id, w, h, crop="entropy", tries=3):
    url = unsplash_url(photo_id, w, h, crop)
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            data = urllib.request.urlopen(req, timeout=60).read()
            img = Image.open(io.BytesIO(data))
            img.load()
            if img.width < 400 or img.height < 400:
                raise ValueError(f"too small {img.size}")
            return img.convert("RGB")
        except Exception as e:  # noqa
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{photo_id}: {last}")


def get_image(role, primary_id, used_ids):
    w, h = SPECS[role][0], SPECS[role][1]
    # у hero чаще всего люди — просим кроп по лицам, чтобы не срезало головы
    crop = "faces,center" if role == "hero" else "entropy"
    candidates = [primary_id] + [
        cid for cid in FALLBACK_POOL[ROLE_POOL[role]] if cid not in used_ids
    ]
    for cid in candidates:
        try:
            img = download(cid, w, h, crop)
            return cid, img
        except RuntimeError as e:
            print(f"    ! {e} — пробую следующее")
    raise RuntimeError(f"не удалось получить фото для роли {role}")


def _jpeg(img, quality):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def encode(img, start_q, max_kb):
    """Пошагово снижаем качество, затем немного масштаб, пока не влезет в max_kb."""
    q = start_q
    raw = _jpeg(img, q)
    while len(raw) > max_kb * 1024 and q > 50:
        q -= 5
        raw = _jpeg(img, q)
    if len(raw) > max_kb * 1024:
        w, h = img.size
        small = img.resize((int(w * 0.85), int(h * 0.85)), Image.LANCZOS)
        raw = _jpeg(small, max(q, 58))
    uri = "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    return raw, uri, q


def fetch_wide_heroes():
    from build import WEB_IMG_TEMPLATES
    for c in CONCEPTS:
        if c["template"] not in WEB_IMG_TEMPLATES:
            continue
        d = OUT / c["slug"]
        src = json.loads((d / "sources.json").read_text(encoding="utf-8"))
        img = download(src["hero"]["id"], 2000, 1250, "faces,center")
        raw, _, q = encode(img, 80, 320)
        (d / "hero-wide.jpg").write_bytes(raw)
        print(f"  {c['slug']}: hero-wide.jpg {len(raw) // 1024} KB q{q}")


def main():
    if "--wide-hero" in sys.argv:
        fetch_wide_heroes()
        return
    skip_existing = "--skip-existing" in sys.argv
    total_bytes = 0
    for c in CONCEPTS:
        slug = c["slug"]
        d = OUT / slug
        d.mkdir(parents=True, exist_ok=True)
        jpath = d / "images.json"
        if skip_existing and jpath.exists():
            print(f"= {slug}: images.json уже есть, пропускаю")
            total_bytes += sum(f.stat().st_size for f in d.glob("*.jpg"))
            continue
        print(f"* {slug}")
        used = set()
        uris = {}
        report = {}
        for role in ("hero", "g1", "g2", "g3"):
            primary = c["images"][role]
            cid, img = get_image(role, primary, used)
            used.add(cid)
            raw, uri, q = encode(img, SPECS[role][2], SPECS[role][3])
            (d / f"{role}.jpg").write_bytes(raw)
            uris[role] = uri
            report[role] = {"id": cid, "kb": round(len(raw) / 1024, 1), "q": q}
            total_bytes += len(raw)
            print(f"    {role}: {cid}  {report[role]['kb']} KB  q{q}")
        jpath.write_text(json.dumps(uris, ensure_ascii=False), encoding="utf-8")
        (d / "sources.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        approx_html = sum(len(u) for u in uris.values()) / 1024
        print(f"    -> data:URI в сумме ~{approx_html:.0f} KB (пойдёт в HTML)")
    print(f"\nГотово. Всего скачано ~{total_bytes/1024/1024:.1f} MB бинарных данных.")


if __name__ == "__main__":
    main()
