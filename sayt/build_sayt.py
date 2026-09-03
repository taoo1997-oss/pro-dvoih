# -*- coding: utf-8 -*-
"""
Сборка витрины «Про двоих».

Каждую страницу из sayt/pages/<file> оборачивает в общую рамку sayt/shell.html
(шапка, меню, подвал) и кладёт готовый файл в sayt/dist/. Меню строится из
sayt/pages.py. Сетка работ строится из materialy/build/concepts.py. Стили и
assets/ копируются в dist/ как есть.

Запуск:  python sayt/build_sayt.py
Заливаем на хостинг именно папку sayt/dist/.
"""
import datetime
import html as _html
import shutil
import sys
from pathlib import Path

from pages import PAGES, SITE

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"

# где на готовом сайте будут лежать сами лендинги пар (шаг «билд под общий корень»)
WORKS_BASE = "/works"

PLACEHOLDERS = ("{{TITLE}}", "{{DESC}}", "{{NAV}}", "{{CONTENT}}", "{{YEAR}}", "{{TELEGRAM}}",
                "{{PHONE_TEL}}", "{{PHONE_WA}}", "{{PHONE_MAX}}", "{{PHONE_DISP}}",
                "{{PORTFOLIO_GRID}}", "{{PORTFOLIO_PREVIEW}}", "{{REL}}")

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def load_phone():
    """Читает sayt/номер.txt (одна строка в любом виде) → ссылки для связи."""
    f = HERE / "номер.txt"
    raw = f.read_text(encoding="utf-8").strip() if f.exists() else ""
    d = "".join(ch for ch in raw if ch.isdigit())
    if len(d) == 11 and d[0] in "78":
        d = "7" + d[1:]
    elif len(d) == 10:
        d = "7" + d
    else:
        print("  ! sayt/номер.txt пуст или не распознан — вставлен placeholder, заполни файл")
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


def _card(c):
    p = c["palette"]
    e = lambda s: _html.escape(str(s), quote=True)
    slug = c["slug"]
    return (
        f'<a class="work" href="{{{{REL}}}}works/{slug}/" style="--w-accent:{p["C_ACCENT"]}">'
        f'<span class="work-shot">'
        f'<img src="{{{{REL}}}}assets/works/{slug}.jpg" alt="Лендинг: {e(c["names"])}" loading="lazy">'
        f'</span>'
        f'<span class="work-body">'
        f'<span class="work-names">{e(c["names"])}</span>'
        f'<span class="work-style">{e(c["style_name"])}</span>'
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

    # лендинги пар → dist/works/<slug>/ (шаг «общий корень»)
    works_src = HERE.parent / "portfolio"
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
    print("\nГотово. Открой sayt/dist/index.html")


if __name__ == "__main__":
    main()
