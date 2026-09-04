# -*- coding: utf-8 -*-
"""
Сборка витрины «Про двоих».

Каждую страницу из САЙТ/pages/<file> оборачивает в общую рамку САЙТ/shell.html
(шапка, меню, подвал) и кладёт готовый файл в САЙТ/dist/. Меню строится из
САЙТ/pages.py. Сетка работ строится из materialy/build/concepts.py. Стили и
assets/ копируются в dist/ как есть.

Запуск:  python САЙТ/build_sayt.py
Заливаем на хостинг именно папку САЙТ/dist/.
"""
import datetime
import html as _html
import re
import shutil
import sys
from pathlib import Path

from pages import PAGES, SITE

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"

# Кастомный домен GitHub Pages. Пишется в dist/CNAME при каждой сборке —
# иначе привязка домена слетает после деплоя через GitHub Actions.
# Пусто — файл CNAME не создаётся (сайт на *.github.io).
DOMAIN = "pro-dvoih.ru"

# где на готовом сайте будут лежать сами лендинги пар (шаг «билд под общий корень»)
WORKS_BASE = "/works"

PLACEHOLDERS = ("{{TITLE}}", "{{DESC}}", "{{NAV}}", "{{CONTENT}}", "{{YEAR}}", "{{TELEGRAM}}",
                "{{PHONE_TEL}}", "{{PHONE_WA}}", "{{PHONE_DISP}}",
                "{{MAX_ENTRY}}", "{{MAX_MODAL_ENTRY}}",
                "{{PORTFOLIO_GRID}}", "{{PORTFOLIO_PREVIEW}}", "{{REL}}")

_MAX_SVG = ('<svg viewBox="0 0 1000 1000" aria-hidden="true"><path fill="currentColor" '
            'fill-rule="evenodd" clip-rule="evenodd" d="M249.681 0H750.319A249.681 249.681 0 0 1 '
            '1000 249.681V750.319A249.681 249.681 0 0 1 750.319 1000H249.681A249.681 249.681 0 0 1 '
            '0 750.319V249.681A249.681 249.681 0 0 1 249.681 0ZM508.211 878.328c-75.007 0-109.864'
            '-10.95-170.453-54.75-38.325 49.275-159.686 87.783-164.979 21.9 0-49.456-10.95-91.248'
            '-23.36-136.873-14.782-56.21-31.572-118.807-31.572-209.508 0-216.626 177.754-379.597 '
            '388.357-379.597 210.785 0 375.947 171.001 375.947 381.604.707 207.346-166.595 '
            '376.118-373.94 377.224m3.103-571.585c-102.564-5.292-182.499 65.7-200.201 177.024-14.6 '
            '92.162 11.315 204.398 33.397 210.238 10.585 2.555 37.23-18.98 53.837-35.587a189.8 '
            '189.8 0 0 0 92.71 33.032c106.273 5.112 197.08-75.794 204.215-181.95 4.154-106.382'
            '-77.67-196.486-183.958-202.574Z"/></svg>')


def max_entries():
    """MAX-иконка в подвале и в окне связи.
    Ссылку берём из pages.py SITE["max"] или из строки вида https://max.ru/u/...
    в САЙТ/номер.txt. Пусто — иконки MAX нет.
    """
    url = (SITE.get("max") or "").strip()
    if not url:
        f = HERE / "номер.txt"
        if f.exists():
            m = re.search(r"https?://max\.ru/\S+", f.read_text(encoding="utf-8"))
            if m:
                url = m.group(0).strip()
    if not url:
        return {"{{MAX_ENTRY}}": "", "{{MAX_MODAL_ENTRY}}": ""}
    foot = f'<a class="ic" href="{url}">{_MAX_SVG}<span>MAX</span></a>'
    modal = f'<a class="contact-link" href="{url}">{_MAX_SVG}<span>MAX</span></a>'
    return {"{{MAX_ENTRY}}": foot, "{{MAX_MODAL_ENTRY}}": modal}

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def load_phone():
    """Телефон из САЙТ/номер.txt — берём ПЕРВУЮ строку с цифрами (не строку max.ru)."""
    f = HERE / "номер.txt"
    raw = ""
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and "max.ru" not in line and any(ch.isdigit() for ch in line):
                raw = line
                break
    d = "".join(ch for ch in raw if ch.isdigit())
    if len(d) == 11 and d[0] in "78":
        d = "7" + d[1:]
    elif len(d) == 10:
        d = "7" + d
    else:
        print("  ! САЙТ/номер.txt пуст или не распознан — вставлен placeholder, заполни файл")
        d = "70000000000"
    disp = f"+7 {d[1:4]} {d[4:7]}-{d[7:9]}-{d[9:11]}"
    return {
        "{{PHONE_TEL}}": f"+{d}",
        "{{PHONE_WA}}": f"https://wa.me/{d}",
        "{{PHONE_MAX}}": f"https://max.ru/{d}",
        "{{PHONE_DISP}}": disp,
    }


def load_concepts():
    """Импортирует 14 концепций из materialy/build/concepts.py."""
    build_dir = HERE.parent / "materialy" / "build"
    sys.path.insert(0, str(build_dir))
    try:
        from concepts import CONCEPTS  # noqa: E402
        return list(CONCEPTS)
    except Exception as e:  # noqa: BLE001
        print(f"  ! не удалось прочитать concepts.py ({e}) — сетка работ будет пустой")
        return []


def _fmt_date(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"


def _swatch_strip(c):
    """Полоска из 5 цветов дресс-кода пары — карточка читается как референс стиля."""
    dots = "".join(
        f'<i style="background:{hx}" title="{_html.escape(str(lb), quote=True)}"></i>'
        for hx, lb in c.get("dresscode", [])[:5]
    )
    return f'<span class="work-palette" aria-hidden="true">{dots}</span>'


def _card(c):
    p = c["palette"]
    e = lambda s: _html.escape(str(s), quote=True)
    slug = c["slug"]
    return (
        f'<a class="work" href="{{{{REL}}}}works/{slug}/" data-reveal style="--w-accent:{p["C_ACCENT"]}">'
        f'<span class="work-shot">'
        f'<img src="{{{{REL}}}}assets/works/{slug}.jpg" alt="Лендинг: {e(c["names"])}" loading="lazy">'
        f'</span>'
        f'<span class="work-body">'
        f'{_swatch_strip(c)}'
        f'<span class="work-style">{e(c["style_name"])}</span>'
        f'<span class="work-names">{e(c["names"])}</span>'
        f'<span class="work-meta">{e(_fmt_date(c["date_iso"]))} · {e(c["city_venue"])}</span>'
        f'</span>'
        f'</a>'
    )


def portfolio_grid(concepts):
    if not concepts:
        return '<p class="soon">Работы подтянутся из concepts.py.</p>'
    return '<div class="works-grid">\n' + "\n".join(_card(c) for c in concepts) + '\n</div>'


def portfolio_preview(concepts, orders=("01", "02", "09", "13")):
    picks = [c for c in concepts if c["order"] in orders] or concepts[:4]
    if not picks:
        return ""
    return '<div class="works-grid works-grid--preview">\n' + "\n".join(_card(c) for c in picks) + '\n</div>'


def build_nav(current_slug):
    out = []
    for p in PAGES:
        if not p.get("in_nav"):
            continue
        href = "{{REL}}" if p["slug"] == "index" else f'{{{{REL}}}}{p["slug"]}/'
        cls = ' class="is-current"' if p["slug"] == current_slug else ""
        out.append(f'<a{cls} href="{href}">{p["nav"]}</a>')
    return "\n        ".join(out)


def main():
    shell = (HERE / "shell.html").read_text(encoding="utf-8")
    DIST.mkdir(exist_ok=True)
    for item in DIST.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            try:
                item.unlink()
            except OSError:
                pass
    year = str(datetime.date.today().year)
    phone = load_phone()
    mx = max_entries()
    concepts = load_concepts()
    grid = portfolio_grid(concepts)
    preview = portfolio_preview(concepts)

    print("Сборка витрины:")
    for p in PAGES:
        src = HERE / "pages" / p["file"]
        if not src.exists():
            raise SystemExit(f"нет файла контента: {src}")
        content = src.read_text(encoding="utf-8")
        rel = "" if p["slug"] == "index" else "../"
        html = shell
        repl = {
            "{{TITLE}}": p["title"],
            "{{DESC}}": p["desc"],
            "{{NAV}}": build_nav(p["slug"]),
            "{{CONTENT}}": content,
            "{{YEAR}}": year,
            "{{TELEGRAM}}": SITE["telegram"],
            "{{PORTFOLIO_GRID}}": grid,
            "{{PORTFOLIO_PREVIEW}}": preview,
        }
        repl.update(phone)
        repl.update(mx)
        for token, value in repl.items():
            html = html.replace(token, value)
        html = html.replace("{{REL}}", rel)   # после всех вставок (grid/nav тоже содержат {{REL}})

        leftover = [t for t in PLACEHOLDERS if t in html]
        if leftover:
            raise SystemExit(f"{p['out']}: не заменены {leftover}")

        out = "index.html" if p["slug"] == "index" else f'{p["slug"]}/index.html'
        dst = DIST / out
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(html, encoding="utf-8")
        url = "/" if p["slug"] == "index" else f"/{p['slug']}/"
        print(f"  {url:24s} -> dist/{out}")

    shutil.copy(HERE / "styles.css", DIST / "styles.css")
    shutil.copytree(HERE / "assets", DIST / "assets", dirs_exist_ok=True)

    if DOMAIN:
        (DIST / "CNAME").write_text(DOMAIN + "\n", encoding="utf-8")
        print(f"  CNAME -> {DOMAIN}")

    # лендинги пар → dist/works/<slug>/ (шаг «общий корень»)
    works_src = HERE.parent / "ПОРТФОЛИО"
    n_works = 0
    for c in concepts:
        lp = works_src / c["slug"] / "index.html"
        if lp.exists():
            dst = DIST / "works" / c["slug"]
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy(lp, dst / "index.html")
            n_works += 1

    print(f"  работ в сетке: {len(concepts)} · лендингов в dist/works/: {n_works}")
    print("  styles.css, assets/  -> dist/")
    print("\nГотово. Открой САЙТ/dist/index.html")


if __name__ == "__main__":
    main()
