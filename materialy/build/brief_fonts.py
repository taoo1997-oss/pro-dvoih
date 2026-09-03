# -*- coding: utf-8 -*-
"""
Встраивает пользовательские шрифты из папки «шрифты/» в brief/brief.html:
блок @font-face (woff2, subset, base64) + секция «Как будут выглядеть шрифты»
с образцами имён и основного текста + сбор ответа в форме.

Также рендерит brief/obraztsy-shriftov.png — картинку с образцами для Google Дока.

Запуск:  python materialy/build/brief_fonts.py
Идемпотентно (правит между маркерами).
"""
import base64
import glob
import io
import os
import re
from pathlib import Path

from fontTools import subset
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONTS_DIR = ROOT / "шрифты"
BRIEF = ROOT / "brief" / "brief.html"
SPECIMEN_PNG = ROOT / "brief" / "obraztsy-shriftov.png"

SUBSET_UNICODES = ("U+0020-007E,U+00A0-00FF,U+0400-04FF,U+0490-0491,"
                   "U+2010-2015,U+2018-201F,U+2116,U+20BD,U+2026,U+00AB,U+00BB")

NAME_SAMPLE = "Пётр и Анна"
BODY_SAMPLE = ("Дорогие друзья! Мы рады пригласить вас на нашу свадьбу "
               "12 июня 2027 года. Сбор гостей в 15:00, церемония в 15:30. "
               "Просим ответить до 15 мая.")


def slug(name):
    s = re.sub(r"^ofont\.ru[_-]?", "", name, flags=re.I)
    s = re.sub(r"\.(ttf|otf|woff2?)$", "", s, flags=re.I)
    return "bf-" + re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def pretty(name):
    s = re.sub(r"^ofont\.ru[_-]?", "", name, flags=re.I)
    return re.sub(r"\.(ttf|otf|woff2?)$", "", s, flags=re.I).strip()


def collect():
    role_files = {
        "name": sorted(glob.glob(str(FONTS_DIR / "имена" / "*.ttf"))
                       + glob.glob(str(FONTS_DIR / "имена" / "*.otf"))),
        "body": sorted(glob.glob(str(FONTS_DIR / "основной-текст" / "*.ttf"))
                       + glob.glob(str(FONTS_DIR / "основной-текст" / "*.otf"))),
    }
    fonts = []
    for role, files in role_files.items():
        for f in files:
            if f.endswith(".orig"):
                continue
            base = os.path.basename(f)
            fonts.append({"role": role, "path": f, "file": base,
                          "slug": slug(base), "name": pretty(base)})
    return fonts


def to_woff2_b64(path):
    opt = subset.Options()
    opt.flavor = "woff2"
    opt.desubroutinize = True
    opt.notdef_outline = True
    opt.layout_features = ["*"]
    opt.ignore_missing_unicodes = True
    ft = subset.load_font(path, opt)
    ss = subset.Subsetter(opt)
    ss.populate(unicodes=subset.parse_unicodes(SUBSET_UNICODES))
    ss.subset(ft)
    buf = io.BytesIO()
    subset.save_font(ft, buf, opt)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_css(fonts):
    faces = []
    for fo in fonts:
        b64 = to_woff2_b64(fo["path"])
        faces.append(f"  @font-face{{font-family:{fo['slug']};"
                     f"src:url(data:font/woff2;base64,{b64}) format('woff2');"
                     f"font-display:swap;}}")
    ui = """
  .font-pick{ display:flex; flex-direction:column; gap:8px; }
  .font-opt{ display:block; border:1px solid #CFC8C2; border-radius:10px; padding:14px 16px;
    cursor:pointer; transition:border-color .15s, background .15s; }
  .font-opt:hover{ border-color:var(--accent); }
  .font-opt input{ position:absolute; opacity:0; width:0; height:0; }
  .font-opt.on, .font-opt:has(input:checked){ border-color:var(--accent); background:#FBF6F3;
    box-shadow:0 0 0 2px rgba(169,116,107,.15); }
  .font-opt .spec{ display:block; color:var(--ink); }
  .font-opt .spec.nm{ font-size:clamp(28px,6vw,38px); line-height:1.25; }
  .font-opt .spec.bd{ font-size:16px; line-height:1.62; }
  .font-opt .spec.muted{ color:var(--soft); font-style:italic; font-size:15px; }
  .font-opt .fmeta{ display:block; margin-top:9px; font-size:12px; color:var(--soft); letter-spacing:.02em; }"""
    return ("  /* BRIEF-FONTS CSS START — генерится materialy/build/brief_fonts.py */\n"
            + "\n".join(faces) + "\n" + ui
            + "\n  /* BRIEF-FONTS CSS END */\n")


def build_html(fonts):
    def opts(role, group, cls, sample, meta_extra=""):
        rows = []
        for fo in [f for f in fonts if f["role"] == role]:
            meta = fo["name"] + meta_extra
            rows.append(
                f'    <label class="font-opt"><input type="radio" name="{group}" value="{fo["name"]}">'
                f'<span class="spec {cls}" style="font-family:{fo["slug"]},serif">{sample}</span>'
                f'<span class="fmeta">{meta}</span></label>')
        rows.append(
            f'    <label class="font-opt"><input type="radio" name="{group}" value="пока не уверены">'
            f'<span class="spec {cls} muted">— пока не уверены, подберите вы</span></label>')
        return "\n".join(rows)

    return f"""  <!-- BRIEF-FONTS HTML START — генерится materialy/build/brief_fonts.py -->
  <div class="section-bar" data-section="Шрифты">
    <div class="n">Раздел 3 · шрифты</div>
    <h2>Как будут выглядеть шрифты</h2>
    <div class="lead">Реальные начертания из нашей библиотеки. Отметьте, каким писать имена на обложке и каким — основной текст. Можно «пока не уверены» — подберём на макете.</div>
  </div>

  <div class="q">
    <label class="qt">Шрифт имён</label>
    <span class="hint">Крупная надпись с вашими именами на первом экране</span>
    <div class="font-pick" data-group="fontNames">
{opts("name", "fontNames", "nm", NAME_SAMPLE)}
    </div>
  </div>

  <div class="q">
    <label class="qt">Шрифт основного текста</label>
    <span class="hint">Абзацы, даты и подписи по всему сайту</span>
    <div class="font-pick" data-group="fontBody">
{opts("body", "fontBody", "bd", BODY_SAMPLE, meta_extra="  ·  0123456789")}
    </div>
  </div>
  <!-- BRIEF-FONTS HTML END -->

"""


COLLECT_JS = """    // BRIEF-FONTS JS START
    document.querySelectorAll('.font-pick').forEach(function(group){
      var picked = group.querySelector('input:checked');
      if(picked) answers.push({ label: LABELS[group.dataset.group] || group.dataset.group, value: picked.value });
    });
    // BRIEF-FONTS JS END
"""

HIGHLIGHT_JS = """  // BRIEF-FONTS highlight START
  document.querySelectorAll('.font-pick').forEach(function(g){
    g.addEventListener('change', function(){
      g.querySelectorAll('.font-opt').forEach(function(o){
        o.classList.toggle('on', o.querySelector('input').checked);
      });
    });
  });
  // BRIEF-FONTS highlight END
"""


def replace_between(text, start, end, payload):
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    return pat.sub(lambda _: payload.strip("\n"), text, count=1)


def inject(html, fonts):
    css = build_css(fonts)
    body = build_html(fonts)

    if "BRIEF-FONTS CSS START" in html:
        html = replace_between(html, "/* BRIEF-FONTS CSS START", "BRIEF-FONTS CSS END */", css)
    else:
        html = html.replace("</style>", css + "</style>", 1)

    if "BRIEF-FONTS HTML START" in html:
        html = replace_between(html, "<!-- BRIEF-FONTS HTML START", "<!-- BRIEF-FONTS HTML END -->", body)
    else:
        html = html.replace("  <!-- ============ 4 ============ -->",
                            body + "  <!-- ============ 4 ============ -->", 1)

    if "BRIEF-FONTS JS START" in html:
        html = replace_between(html, "    // BRIEF-FONTS JS START", "    // BRIEF-FONTS JS END", COLLECT_JS)
    else:
        anchor = ("    document.querySelectorAll('[data-select=\"multi-check\"]').forEach(function(group){\n"
                  "      var a = Array.from(group.querySelectorAll('input:checked')).map(function(i){ return i.value; });\n"
                  "      if(a.length) answers.push({ label: LABELS[group.dataset.group] || group.dataset.group, value: a.join('; ') });\n"
                  "    });\n")
        html = html.replace(anchor, anchor + COLLECT_JS, 1)

    if "BRIEF-FONTS highlight START" in html:
        html = replace_between(html, "  // BRIEF-FONTS highlight START", "  // BRIEF-FONTS highlight END", HIGHLIGHT_JS)
    else:
        html = html.replace("</script>\n</body>", HIGHLIGHT_JS + "</script>\n</body>", 1)

    return html


def render_specimen(fonts):
    W = 1100
    pad = 40
    blocks = []
    for fo in fonts:
        try:
            size = 44 if fo["role"] == "name" else 22
            ft = ImageFont.truetype(fo["path"], size)
            txt = NAME_SAMPLE if fo["role"] == "name" else BODY_SAMPLE
            blocks.append((fo, ft, txt))
        except Exception as e:  # noqa
            print("  ! specimen:", fo["file"], e)
    line_h = 130
    H = pad * 2 + len(blocks) * line_h + 60
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    try:
        label_f = ImageFont.truetype("arialbd.ttf", 13)
        small_f = ImageFont.truetype("arial.ttf", 12)
    except Exception:  # noqa
        label_f = small_f = ImageFont.load_default()
    d.text((pad, pad - 4), "ОБРАЗЦЫ ШРИФТОВ · имена и основной текст", fill="#333", font=label_f)
    y = pad + 34
    role_titles = {"name": "ИМЕНА", "body": "ОСНОВНОЙ ТЕКСТ"}
    seen_role = set()
    for fo, ft, txt in blocks:
        if fo["role"] not in seen_role:
            d.text((pad, y), role_titles[fo["role"]], fill="#A9746B", font=label_f)
            y += 22
            seen_role.add(fo["role"])
        d.text((pad, y + 6), fo["name"], fill="#999", font=small_f)
        if fo["role"] == "body":
            # перенос длинного текста
            words = txt.split(" ")
            line = ""
            yy = y + 26
            for w in words:
                test = (line + " " + w).strip()
                if d.textlength(test, font=ft) > W - pad * 2:
                    d.text((pad, yy), line, fill="#1c1c1c", font=ft)
                    yy += size + 8
                    line = w
                else:
                    line = test
            d.text((pad, yy), line, fill="#1c1c1c", font=ft)
            y = yy + line_h - 30
        else:
            d.text((pad, y + 22), txt, fill="#1c1c1c", font=ft)
            y += line_h
    img.save(SPECIMEN_PNG)
    print(f"  образец: {SPECIMEN_PNG.name}  {img.size}")


def main():
    fonts = collect()
    if not fonts:
        raise SystemExit("В папке «шрифты/» нет файлов .ttf/.otf")
    print("Шрифты:")
    for fo in fonts:
        print(f"  [{fo['role']}] {fo['name']}  ({fo['slug']})")
    html = BRIEF.read_text(encoding="utf-8")
    html = inject(html, fonts)
    BRIEF.write_text(html, encoding="utf-8")
    kb = len(html.encode("utf-8")) / 1024
    print(f"brief/brief.html обновлён — {kb:.0f} KB")
    render_specimen(fonts)
    print("Готово.")


if __name__ == "__main__":
    main()
