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


def _works_dir_name(c):
    """Папка пары в ПОРТФОЛИО/ — та же формула, что dir_name() в materialy/build/build.py."""
    return f'{c["order"]} {c["names"]}'


def _fmt_date(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"


def make_variants(src, out_dir, stem, widths):
    """webp + jpg уменьшенные копии картинки для srcset. Пишутся только в dist/,
    исходники в assets/ не трогаем. Возвращает [(w, h), ...]."""
    from PIL import Image
    img = Image.open(src).convert("RGB")
    out_dir.mkdir(parents=True, exist_ok=True)
    sizes = []
    for w in sorted({min(w, img.width) for w in widths}):
        h = round(img.height * w / img.width)
        im = img if w == img.width else img.resize((w, h), Image.LANCZOS)
        im.save(out_dir / f"{stem}-{w}.webp", "WEBP", quality=78, method=6)
        im.save(out_dir / f"{stem}-{w}.jpg", "JPEG", quality=80, optimize=True, progressive=True)
        sizes.append((w, h))
    return sizes


WORK_THUMB_W = (400, 720)
WORK_SIZES = "(max-width: 700px) 92vw, (max-width: 1100px) 45vw, 330px"


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
    # «Dusty rose — пыльная роза, романтика» -> заголовок + подпись, без тире
    title, _, sub = c["style_name"].partition(" — ")
    sub_html = f'<span class="work-sub">{e(sub)}</span>' if sub else ""
    base = f'{{{{REL}}}}assets/works/{slug}'
    srcset = lambda ext: ", ".join(f"{base}-{w}.{ext} {w}w" for w in WORK_THUMB_W)
    return (
        f'<a class="work" href="{{{{REL}}}}works/{slug}/" data-reveal style="--w-accent:{p["C_ACCENT"]}">'
        f'<span class="work-shot"><picture>'
        f'<source type="image/webp" srcset="{srcset("webp")}" sizes="{WORK_SIZES}">'
        f'<img src="{base}-{WORK_THUMB_W[0]}.jpg" srcset="{srcset("jpg")}" sizes="{WORK_SIZES}" '
        f'width="400" height="550" alt="Лендинг: {e(c["names"])}" loading="lazy" decoding="async">'
        f'</picture></span>'
        f'<span class="work-body">'
        f'{_swatch_strip(c)}'
        f'<span class="work-style">{e(title)}</span>{sub_html}'
        f'<span class="work-names">{e(c["names"])}</span>'
        f'<span class="work-meta">{e(_fmt_date(c["date_iso"]))} · {e(c["city_venue"])}</span>'
        f'</span>'
        f'</a>'
    )


def _cta_card():
    """Пятнадцатая плитка в сетке: та же форма, что у работы, но про заказ.
    Открывает то же окно «Как вам удобнее написать?», что и кнопки в шапке."""
    return (
        '<a class="work work--cta" href="{{REL}}#svyaz" data-open-contact data-reveal>'
        '<span class="work-cta-body">'
        '<span class="work-cta-title">Здесь может быть ваша свадьба</span>'
        '<span class="work-cta-meta">3&nbsp;500&nbsp;₽ · 3–4 дня</span>'
        '<span class="work-cta-btn">Оставить заявку</span>'
        '</span>'
        '</a>'
    )


def portfolio_grid(concepts):
    if not concepts:
        return '<p class="soon">Работы подтянутся из concepts.py.</p>'
    cards = [_card(c) for c in concepts] + [_cta_card()]
    return '<div class="works-grid">\n' + "\n".join(cards) + '\n</div>'


RAIL_SIZES = "(max-width: 700px) 72vw, 340px"


def _rail_card(c):
    """Карточка ленты на главной: крупное фото, под ним стиль и палитра."""
    e = lambda s: _html.escape(str(s), quote=True)
    slug = c["slug"]
    title, _, sub = c["style_name"].partition(" — ")
    base = f'{{{{REL}}}}assets/works/{slug}'
    srcset = lambda ext: ", ".join(f"{base}-{w}.{ext} {w}w" for w in WORK_THUMB_W)
    return (
        f'<li class="rail-item"><a class="rail-card" href="{{{{REL}}}}works/{slug}/">'
        f'<span class="rail-shot"><picture>'
        f'<source type="image/webp" srcset="{srcset("webp")}" sizes="{RAIL_SIZES}">'
        f'<img src="{base}-{WORK_THUMB_W[0]}.jpg" srcset="{srcset("jpg")}" sizes="{RAIL_SIZES}" '
        f'width="400" height="550" alt="Лендинг: {e(c["names"])}" loading="lazy" decoding="async">'
        f'</picture></span>'
        f'{_swatch_strip(c)}'
        f'<span class="rail-style">{e(title)}</span>'
        f'<span class="rail-sub">{e(sub or c["names"])}</span>'
        f'</a></li>'
    )


def portfolio_preview(concepts, orders=("01", "02", "09", "13", "03", "06", "11", "14")):
    """Горизонтальная лента на главной: 8 работ и в конце ссылка на все."""
    picks = [c for o in orders for c in concepts if c["order"] == o] or concepts[:8]
    if not picks:
        return ""
    end = (f'<li class="rail-item rail-item--end"><a class="rail-end" href="{{{{REL}}}}portfolio/">'
           f'<span class="rail-end-num">{len(concepts)}</span>'
           f'<span class="rail-end-txt">работ в&nbsp;разных стилях</span>'
           f'<span class="link-arrow">Смотреть все</span></a></li>')
    items = "\n".join(_rail_card(c) for c in picks)
    return f'<div class="rail" data-rail-track><ul class="rail-track">\n{items}\n{end}\n</ul></div>'


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
    # уменьшенные превью работ (исходники 1200×1650, в сетке ~330px)
    for c in concepts:
        src = HERE / "assets" / "works" / f'{c["slug"]}.jpg'
        if src.exists():
            make_variants(src, DIST / "assets" / "works", c["slug"], WORK_THUMB_W)
    # фото пары на первом экране
    make_variants(HERE / "assets" / "hero-pyotr-anna.jpg", DIST / "assets", "hero", (750, 1200))
    # кадры лендинга на телефоне (снимает snap_phone.js): 1x и 2x
    for shot in sorted((HERE / "assets" / "phone").glob("*.jpg")):
        make_variants(shot, DIST / "assets" / "phone", shot.stem, (390, 780))

    if DOMAIN:
        (DIST / "CNAME").write_text(DOMAIN + "\n", encoding="utf-8")
        print(f"  CNAME -> {DOMAIN}")

    # лендинги пар: читаем из ПОРТФОЛИО/<NN Имена>/, публикуем на dist/works/<slug>/
    # (URL сайта остаётся латиницей, даже если папка на диске — кириллицей)
    works_src = HERE.parent / "ПОРТФОЛИО"
    n_works = 0
    for c in concepts:
        lp = works_src / _works_dir_name(c) / "index.html"
        if lp.exists():
            dst = DIST / "works" / c["slug"]
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy(lp, dst / "index.html")
            # фото лендинга файлами (шаблоны из WEB_IMG_TEMPLATES в build.py)
            if (lp.parent / "img").is_dir():
                shutil.copytree(lp.parent / "img", dst / "img", dirs_exist_ok=True)
            # страница ответов гостей для пары — тот же RSVP-бэкенд, что и форма
            gl = lp.parent / "spisok-gostey.html"
            if gl.exists():
                shutil.copy(gl, dst / "spisok-gostey.html")
            n_works += 1

    print(f"  работ в сетке: {len(concepts)} · лендингов в dist/works/: {n_works}")
    print("  styles.css, assets/  -> dist/")
    print("\nГотово. Открой САЙТ/dist/index.html")


if __name__ == "__main__":
    main()
