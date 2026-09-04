# -*- coding: utf-8 -*-
"""
Бумажное приглашение A5 (двусторонний макет для типографии) — платный доп +1 500 ₽.

Для каждой концепции из concepts.py рендерит shablon/priglashenie-A5.template.html
в ПОРТФОЛИО/<NN Имена>/для печати/index.html:
  • лицевая сторона — фото из шапки лендинга + кто приглашает и тёплые слова;
  • оборот — что, где и когда (без блока «добавить гостей», без формы).

Палитра, имена, дата и адрес берутся из той же концепции, что и лендинг —
бумага и сайт всегда совпадают.

Запуск:  python materialy/build/build_priglashenie.py
Печать:  открыть index.html → «Печать» → A5, двусторонняя, поля 0 → «Сохранить в PDF».
"""
import html
import json
import urllib.parse
from pathlib import Path

from concepts import CONCEPTS

import build  # переиспуем derive() / MONTHS_GEN / WD — дата считается один раз и одинаково

ROOT = Path(__file__).resolve().parents[2]
TPL = ROOT / "shablon" / "priglashenie-A5.template.html"
PORTF = ROOT / "ПОРТФОЛИО"
IMG_DIR = ROOT / "materialy" / "foto-ishodniki"  # тот же источник фото, что у build.py
# в макете адрес показывается текстом (не ссылкой) — без протокола, короче и без переносов
SITE_BASE = "pro-dvoih.ru/works"


def hero_uri(slug):
    """data:-URI фото из шапки лендинга (ключ hero в images.json). Пусто — предупредить."""
    jp = IMG_DIR / slug / "images.json"
    if jp.exists():
        uri = json.loads(jp.read_text(encoding="utf-8")).get("hero", "")
        if uri:
            return uri
    print(f"  ! нет фото hero для {slug} — лицевая сторона будет без фото "
          f"(запусти materialy/build/fetch_images.py)")
    return ""


def e(s):
    return html.escape(str(s), quote=False)


def swatches_html(items):
    return "".join(
        f'<i style="background:{hx}" title="{html.escape(str(lb), quote=True)}"></i>'
        for hx, lb in items[:5]
    )


def render(tpl, repl):
    out = tpl
    for k, v in repl.items():
        out = out.replace("{{" + k + "}}", str(v))
    leftover = sorted({seg.split("}}")[0] for seg in out.split("{{")[1:]})
    if leftover:
        raise SystemExit(f"{repl.get('NAMES', '?')}: незакрытые токены {leftover}")
    return out


def fields(c):
    d = build.datetime.date.fromisoformat(c["date_iso"])
    dd = build.derive(c)
    weekday_time = f"{build.WD[d.weekday()]}, начало в {c['time']}"
    return {
        # палитра
        "C_BG": c["palette"]["C_BG"], "C_BG2": c["palette"]["C_BG2"],
        "C_INK": c["palette"]["C_INK"], "C_ACCENT": c["palette"]["C_ACCENT"],
        "C_ACCENT_DEEP": c["palette"]["C_ACCENT_DEEP"],
        "C_TEXT": c["palette"]["C_TEXT"], "C_TEXT_SOFT": c["palette"]["C_TEXT_SOFT"],
        "C_ON_INK": c["palette"]["C_ON_INK"], "C_LINE": c["palette"]["C_LINE"],
        # лицевая — фото-обложка как в шапке лендинга
        "IMG_HERO": hero_uri(c["slug"]),
        "HERO_FOCUS": c["palette"]["HERO_FOCUS"],
        "HERO_EYEBROW": e(c["hero_eyebrow"]),
        "NAMES": e(c["names"]),
        "INITIALS": e(c["initials"]),
        "INTRO_LEAD": e(c["intro_lead"]),
        "DATE_NUMERIC": dd["DATE_NUMERIC"],
        # оборот
        "DATE_HUMAN": dd["DATE_HUMAN"],
        "WEEKDAY_TIME": e(weekday_time),
        "GATHER": e(c["when_extra_tail"][0].upper() + c["when_extra_tail"][1:]),
        "WHERE_VALUE": e(c["where_value"]),
        "WHERE_EXTRA": e(c["where_extra"]),
        "DRESSCODE_SWATCHES": swatches_html(c["dresscode"]),
        "DRESSCODE_NOTE": e(c["dresscode_note"]),
        "FOOTER_LINE": e(c["footer_line"]),
        "LANDING_URL": f"{SITE_BASE}/{c['slug']}/",
    }


def main():
    tpl = TPL.read_text(encoding="utf-8")
    print("Бумажные приглашения A5:")
    for c in CONCEPTS:
        out_dir = PORTF / build.dir_name(c) / "для печати"
        out_dir.mkdir(parents=True, exist_ok=True)
        page = render(tpl, fields(c))
        dst = out_dir / "index.html"
        dst.write_text(page, encoding="utf-8")
        print(f"  {build.dir_name(c):34s} -> {dst.relative_to(ROOT)}  ({dst.stat().st_size / 1024:.0f} КБ)")
    print(f"\nГотово: {len(CONCEPTS)} макетов. Печать — A5, двусторонняя, поля 0.")


if __name__ == "__main__":
    main()
