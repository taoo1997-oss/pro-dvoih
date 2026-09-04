# -*- coding: utf-8 -*-
"""
Раздел 3 брифа «Стиль и визуал» — визуальный выбор без открытия портфолио:

  1. Стиль лендинга  — 7 превью-скриншотов (шаблоны A–G), каждая картинка = чекбокс.
  2. Цветовая палитра — 10 палитр кружочками (как дресс-код в лендинге), тоже чекбоксы.

Превью берутся из brief/styli/<A..G>.jpg (готовые скриншоты обложек, ~520px, jpeg).
Палитры и их названия — из materialy/build/concepts.py (первые 10 концепций, поле dresscode).

Ответы собираются штатным обработчиком brief.html для data-select="multi-check" —
отдельного JS не требуется, только подсветка выбранного.

Запуск:  python materialy/build/brief_styles.py
Идемпотентно — правит brief/brief.html между маркерами BRIEF-STYLES.
"""
import base64
import re
from pathlib import Path

from concepts import CONCEPTS

ROOT = Path(__file__).resolve().parents[2]
BRIEF = ROOT / "БРИФ" / "brief.html"
STYLI = ROOT / "БРИФ" / "styli"

# порядок и подписи шаблонов
STYLES = [
    ("A", "Кадр",            "фото на весь экран, имена по центру, курсив в заголовках"),
    ("B", "Разворот",        "цветная панель + фото сбоку, секции в две колонки"),
    ("C", "Полоса",          "имена на плашке под фото, крупные номера секций, мозаика"),
    ("D", "Полоса даты",     "три фото в ряд и крупная дата поверх, акварельная зелень"),
    ("E", "Ч/б разворот",    "полноэкранное чёрно-белое фото, «Save the date», тонкая графика"),
    ("F", "Крупный почерк",  "имена размашистым почерком поверх ч/б фото, дата моноширинным"),
    ("G", "Кинообложка",     "чёрно-белое фото с медленным зумом, как кадр из фильма"),
]


def img_b64(letter):
    p = STYLI / f"{letter}.jpg"
    if not p.exists():
        raise SystemExit(f"нет превью {p} — положите скриншот обложки шаблона {letter}")
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")


def palettes():
    out = []
    for c in CONCEPTS[:10]:
        name_full = c["style_name"]
        name = re.split(r"\s+[—-]\s+", name_full, maxsplit=1)[0].strip()
        sub = name_full[len(name):].lstrip(" —-").strip()
        hexes = [hx for hx, _lbl in c["dresscode"]]
        out.append((name, sub, hexes))
    return out


CSS = """  /* BRIEF-STYLES CSS START — генерится materialy/build/brief_styles.py */
  .style-pick{ display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:12px; }
  .style-opt{ display:block; border:1px solid #CFC8C2; border-radius:10px; overflow:hidden;
    cursor:pointer; background:#fff; transition:border-color .15s, box-shadow .15s; }
  .style-opt:hover{ border-color:var(--accent); }
  .style-opt input{ position:absolute; opacity:0; width:0; height:0; }
  .style-opt.on, .style-opt:has(input:checked){ border-color:var(--accent);
    box-shadow:0 0 0 2px rgba(169,116,107,.18); }
  .style-opt img{ display:block; width:100%; aspect-ratio:4/3; object-fit:cover; border-bottom:1px solid var(--line); }
  .style-opt .style-cap{ display:block; padding:10px 12px; }
  .style-opt .style-cap b{ display:block; font-size:13.5px; }
  .style-opt .style-cap span{ display:block; font-size:12px; color:var(--soft); margin-top:2px; line-height:1.4; }
  .style-opt.on .style-cap b, .style-opt:has(input:checked) .style-cap b{ color:var(--accent-deep); }

  .pal-pick{ display:flex; flex-direction:column; gap:8px; }
  .pal-opt{ display:flex; align-items:center; gap:14px; border:1px solid #CFC8C2; border-radius:10px;
    padding:12px 14px; cursor:pointer; transition:border-color .15s, box-shadow .15s; }
  .pal-opt:hover{ border-color:var(--accent); }
  .pal-opt input{ position:absolute; opacity:0; width:0; height:0; }
  .pal-opt.on, .pal-opt:has(input:checked){ border-color:var(--accent); box-shadow:0 0 0 2px rgba(169,116,107,.18); }
  .pal-dots{ display:flex; flex-shrink:0; }
  .pal-dots i{ width:22px; height:22px; border-radius:50%; display:block; box-shadow:inset 0 0 0 1px rgba(0,0,0,.10); }
  .pal-dots i + i{ margin-left:-5px; }
  .pal-name{ font-size:14.5px; }
  .pal-name .pal-sub{ display:block; font-size:12px; color:var(--soft); }
  /* BRIEF-STYLES CSS END */
"""

HIGHLIGHT_JS = """  // BRIEF-STYLES highlight START
  document.querySelectorAll('.style-pick, .pal-pick').forEach(function(g){
    g.addEventListener('change', function(){
      g.querySelectorAll('.style-opt, .pal-opt').forEach(function(o){
        var i = o.querySelector('input'); if(i) o.classList.toggle('on', i.checked);
      });
    });
  });
  // BRIEF-STYLES highlight END
"""


def build_html():
    style_rows = []
    for letter, name, desc in STYLES:
        style_rows.append(
            f'      <label class="style-opt"><input type="checkbox" value="{letter} — {name}">'
            f'<img src="{img_b64(letter)}" alt="{name}" loading="lazy">'
            f'<span class="style-cap"><b>{letter} · {name}</b><span>{desc}</span></span></label>')
    pal_rows = []
    for name, sub, hexes in palettes():
        dots = "".join(f'<i style="background:{hx}"></i>' for hx in hexes)
        sub_html = f'<span class="pal-sub">{sub}</span>' if sub else ""
        pal_rows.append(
            f'      <label class="pal-opt"><input type="checkbox" value="{name}">'
            f'<span class="pal-dots">{dots}</span>'
            f'<span class="pal-name">{name}{sub_html}</span></label>')
    return (
        "  <!-- BRIEF-STYLES HTML START — генерится materialy/build/brief_styles.py -->\n"
        '  <div class="q">\n'
        '    <label class="qt">Стиль лендинга<span class="req">*</span></label>\n'
        '    <span class="hint">Отметьте 1–2 варианта компоновки, которые нравятся</span>\n'
        '    <div class="style-pick" data-group="landingStyle" data-select="multi-check">\n'
        + "\n".join(style_rows) + "\n"
        "    </div>\n"
        "  </div>\n"
        '  <div class="q">\n'
        '    <label class="qt">Цветовая палитра</label>\n'
        '    <span class="hint">Можно несколько. Если нужного оттенка нет — впишите свой в поле ниже</span>\n'
        '    <div class="pal-pick" data-group="weddingPalette" data-select="multi-check">\n'
        + "\n".join(pal_rows) + "\n"
        "    </div>\n"
        "  </div>\n"
        "  <!-- BRIEF-STYLES HTML END -->"
    )


def replace_between(text, start, end, payload):
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    return pat.sub(lambda _: payload, text, count=1)


def main():
    html = BRIEF.read_text(encoding="utf-8")

    if "BRIEF-STYLES CSS START" in html:
        html = replace_between(html, "/* BRIEF-STYLES CSS START", "BRIEF-STYLES CSS END */",
                               CSS.strip("\n"))
    else:
        html = html.replace("</style>", CSS + "</style>", 1)

    if "BRIEF-STYLES HTML START" not in html:
        raise SystemExit("в brief.html нет маркеров BRIEF-STYLES HTML — вставьте их в разделе 3")
    html = replace_between(html, "<!-- BRIEF-STYLES HTML START", "<!-- BRIEF-STYLES HTML END -->",
                           build_html())

    if "BRIEF-STYLES highlight START" in html:
        html = replace_between(html, "  // BRIEF-STYLES highlight START",
                               "  // BRIEF-STYLES highlight END", HIGHLIGHT_JS.strip("\n"))
    elif "BRIEF-FONTS highlight END" in html:
        html = html.replace("  // BRIEF-FONTS highlight END\n",
                            "  // BRIEF-FONTS highlight END\n" + HIGHLIGHT_JS, 1)
    else:
        html = html.replace("</script>\n</body>", HIGHLIGHT_JS + "</script>\n</body>", 1)

    BRIEF.write_text(html, encoding="utf-8")
    kb = len(html.encode("utf-8")) / 1024
    print(f"brief/brief.html обновлён — {kb:.0f} KB")
    print(f"  стилей: {len(STYLES)}, палитр: {len(palettes())}")


if __name__ == "__main__":
    main()
