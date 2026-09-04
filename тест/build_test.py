# -*- coding: utf-8 -*-
"""
E2E-тест: собрать ОДИН лендинг по заполненному брифу, не трогая ПОРТФОЛИО/.
Переиспользует настоящий конвейер (fetch_images + build), только с
подменёнными путями вывода на папку тест/.

Запуск:  python тест/build_test.py
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BUILD_DIR = ROOT / "materialy" / "build"
sys.path.insert(0, str(BUILD_DIR))

import build          # noqa: E402  настоящий рендер
import fetch_images   # noqa: E402  настоящая качалка фото

OUT_IMG = HERE / "img"
OUT_LP = HERE / "output"

# --- концепция, выведенная из БРИФ-заполненный.md -------------------------
CONCEPT = {
    "slug": "test-egor-i-valeriya-shalfej",
    "order": "T",
    "template": "A",
    "style_name": "Шалфей и терракота — природная, спокойная",
    "names": "Егор и Валерия",
    "initials": "Е · В",
    "city_venue": "Нижний Новгород · клуб «Сосновка»",
    "venue_short": "клуб «Сосновка»",
    "where_value": "Загородный клуб «Сосновка»",
    "where_extra": "Кстовский р-н, д. Афонино, ул. Лесная, 4",
    "map_query": "Кстовский район Афонино Лесная 4 Сосновка",
    "date_iso": "2027-08-21",
    "time": "15:30",
    "when_extra_tail": "сбор гостей в 15:00",
    "hero_eyebrow": "Мы женимся",
    "intro_lead": "Четыре года назад мы встретились на сплаве по Керженцу — "
                  "а теперь зовём вас на день, ради которого всё это было.",
    "intro_body": "Будет выездная церемония в сосновом лесу, длинный стол в шатре, "
                  "костёр вечером и никакой спешки. Возьмите тёплую кофту на вечер "
                  "и удобную обувь для травы.",
    "program_sub": "Ориентировочный тайминг — чтобы вы спланировали день",
    "program": [
        ("15:00", "Сбор гостей", "Приветственный морс у входа в лес"),
        ("15:30", "Церемония", "На поляне среди сосен"),
        ("16:30", "Фуршет и фото", "Прогулка по территории"),
        ("18:30", "Ужин", "Длинный стол в шатре"),
        ("21:00", "Первый танец", "И танцы до ночи"),
        ("23:00", "Костёр", "Пожелания и тёплый чай"),
    ],
    "gallery_captions": ("С нашей фотопрогулки", "Детали и флористика", "Каким будет вечер"),
    "dresscode_note": "Природная палитра: шалфей, терракота, крем, беж, олива. "
                      "Пожалуйста, без total-белого и без чёрного total-look.",
    "dresscode": [
        ("#8A9A7B", "шалфей"), ("#B4633C", "терракота"), ("#EFE3D3", "крем"),
        ("#C7A98B", "тёплый беж"), ("#7C7A4A", "олива"),
    ],
    "faq": [
        ("Как добраться?", "От площади Минина трансфер в 14:00. Обратно два рейса — "
         "в 23:30 и в 01:00. Точку посадки пришлём в чате гостей."),
        ("Будет ли парковка?", "Да, у клуба бесплатная парковка. Можно оставить "
         "машину на ночь и уехать утром."),
        ("Можно ли с детьми?", "Да, мы рады малышам. Отметьте в форме — "
         "подготовим детский уголок и меню."),
        ("Что с подарками?", "Лучший подарок — вы рядом. Если хочется большего — "
         "будем благодарны за вклад в свадебное путешествие."),
    ],
    "rsvp_lead": "Пожалуйста, ответьте до 25 июля",
    "rsvp_extra_label": "Аллергии, пожелания по меню, нужен ли трансфер",
    "rsvp_note": "Ваш ответ придёт напрямую паре. Ничего устанавливать не нужно.",
    "footer_line": "До встречи 21 августа — Егор и Валерия",
    "palette": {
        "C_INK": "#2F352A", "C_INK2": "#232820",
        "C_BG": "#F2EFE6", "C_BG2": "#E4E1D2",
        "C_ACCENT": "#7E8A6A", "C_ACCENT_DEEP": "#5E6A4C",
        "C_TEXT": "#33372C", "C_TEXT_SOFT": "#6B6E5C",
        "C_ON_INK": "#EFEDE0", "C_ON_INK_SOFT": "rgba(239,237,224,0.72)",
        "C_LINE": "rgba(47,53,42,0.16)", "C_LINE_ON_INK": "rgba(239,237,224,0.22)",
        "HERO_FOCUS": "50% 45%",
    },
    # роли: hero=пара, g1=флористика, g2=место, g3=сервировка.
    # взяты рабочие id из fetch_images.FALLBACK_POOL — имитируем «подобрал на Unsplash».
    "images": {
        "hero": "1541679368093-5c967ac6de11",
        "g1": "1683435844312-ac5324de7572",
        "g2": "1502635385003-ee1e6a1a742d",
        "g3": "1738898179451-b5fc497f9f8e",
    },
}


def fetch():
    """Тот же цикл, что в fetch_images.main(), но для одной концепции."""
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    used, uris, report = set(), {}, {}
    for role in ("hero", "g1", "g2", "g3"):
        primary = CONCEPT["images"][role]
        cid, img = fetch_images.get_image(role, primary, used)
        used.add(cid)
        raw, uri, q = fetch_images.encode(img, fetch_images.SPECS[role][2],
                                          fetch_images.SPECS[role][3])
        (OUT_IMG / f"{role}.jpg").write_bytes(raw)
        uris[role] = uri
        report[role] = {"id": cid, "kb": round(len(raw) / 1024, 1), "q": q}
        print(f"  {role}: {cid}  {report[role]['kb']} KB  q{q}")
    (OUT_IMG / "images.json").write_text(json.dumps(uris, ensure_ascii=False), encoding="utf-8")
    (OUT_IMG / "sources.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return report


def render():
    """Настоящий build.build_concept с подменёнными путями."""
    build.IMG_DIR = HERE            # build ищет <IMG_DIR>/<slug>/images.json
    build.PORTF = OUT_LP            # и пишет в <PORTF>/<slug>/
    (HERE / CONCEPT["slug"]).mkdir(parents=True, exist_ok=True)
    # images.json должен лежать в <IMG_DIR>/<slug>/
    (HERE / CONCEPT["slug"] / "images.json").write_text(
        (OUT_IMG / "images.json").read_text(encoding="utf-8"), encoding="utf-8")

    tpl_cache = {k: (build.TPL_DIR / v).read_text(encoding="utf-8")
                 for k, v in build.TEMPLATE_FILE.items()}
    guests_tpl = (build.TPL_DIR / "guests.template.html").read_text(encoding="utf-8")
    tpl, kb = build.build_concept(CONCEPT, tpl_cache, guests_tpl)
    return tpl, kb


if __name__ == "__main__":
    t = {}
    t["fetch_start"] = time.time()
    print("[1/2] качаю и жму 4 фото…")
    rep = fetch()
    t["fetch_end"] = time.time()

    print("[2/2] рендерю лендинг + список гостей…")
    tpl, kb = render()
    t["render_end"] = time.time()

    lp = OUT_LP / CONCEPT["slug"] / "index.html"
    gl = OUT_LP / CONCEPT["slug"] / "spisok-gostey.html"
    print()
    print(f"лендинг:        {lp}  ({lp.stat().st_size/1024:.0f} KB)")
    print(f"список гостей:   {gl}  ({gl.stat().st_size/1024:.0f} KB)")
    print(f"фото:  качал+жал {t['fetch_end']-t['fetch_start']:.1f} c")
    print(f"рендер:          {t['render_end']-t['fetch_end']:.1f} c")
    print(f"ИТОГО скрипт:    {t['render_end']-t['fetch_start']:.1f} c")
    (HERE / "_timing.json").write_text(json.dumps({
        "fetch_sec": round(t["fetch_end"] - t["fetch_start"], 1),
        "render_sec": round(t["render_end"] - t["fetch_end"], 1),
        "total_sec": round(t["render_end"] - t["fetch_start"], 1),
        "landing_kb": round(lp.stat().st_size / 1024, 1),
        "images": rep,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
