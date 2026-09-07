# -*- coding: utf-8 -*-
"""
Рендерит один из трёх шаблонов (shablon/{A,B,C}-*.template.html) по концепциям
из concepts.py в ПОРТФОЛИО/<slug>/index.html + spisok-gostey.html,
плюс собирает витрину ПОРТФОЛИО/index.html.

Запуск:  python materialy/build/build.py
Нужно, чтобы сначала отработал fetch_images.py (нужны images.json).
"""
import datetime
import html
import json
import urllib.parse
from pathlib import Path

from concepts import CONCEPTS

ROOT = Path(__file__).resolve().parents[2]
TPL_DIR = ROOT / "shablon"
IMG_DIR = ROOT / "materialy" / "foto-ishodniki"
PORTF = ROOT / "ПОРТФОЛИО"

# Бэкенд для ответов гостей (RSVP). Форма и spisok-gostey.html ходят сюда
# через fetch. Значение — URL воркера из rsvp-backend/ после `npm run deploy`.
# Без завершающего слэша.
RSVP_API = "https://rsvp-backend.taoo1997.workers.dev"

MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня",
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
WD = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

TEMPLATE_FILE = {
    "A": "A-kadr.template.html",
    "B": "B-razvorot.template.html",
    "C": "C-polosa.template.html",
    # референс-шаблоны (по макетам из папки «референсы»)
    "D": "D-polosa-daty.template.html",     # реф1: фотополоса с крупной датой, акварельная зелень
    "E": "E-chb-razvorot.template.html",    # реф2: чёрно-белая обложка, тонкая графика, Save the date
    "F": "F-krupny-pocherk.template.html",  # реф3: имена огромным почерком поверх ч/б фото
    "G": "G-video-oblozhka.template.html",  # реф4: кинообложка Welcome (ч/б фото + медленный зум)
}

_GV = "https://fonts.googleapis.com/css2"
TEMPLATE_FONTS = {
    "A": {
        "FONT_LINK": _GV + "?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500"
                     "&family=Manrope:wght@400;500;600;700&family=Great+Vibes&display=swap",
        "FONT_HEAD": "'Cormorant Garamond', 'Times New Roman', serif",
        "FONT_TEXT": "'Manrope', system-ui, sans-serif",
        "FONT_NAME": "'Great Vibes', 'Segoe Script', cursive",
    },
    "B": {
        "FONT_LINK": _GV + "?family=Forum&family=PT+Sans:ital,wght@0,400;0,700;1,400"
                     "&family=Great+Vibes&display=swap",
        "FONT_HEAD": "'Forum', 'Times New Roman', serif",
        "FONT_TEXT": "'PT Sans', system-ui, sans-serif",
        "FONT_NAME": "'Great Vibes', 'Segoe Script', cursive",
    },
    "C": {
        "FONT_LINK": _GV + "?family=Tenor+Sans&family=Golos+Text:wght@400;500;600;700"
                     "&family=Great+Vibes&display=swap",
        "FONT_HEAD": "'Tenor Sans', system-ui, sans-serif",
        "FONT_TEXT": "'Golos Text', system-ui, sans-serif",
        "FONT_NAME": "'Great Vibes', 'Segoe Script', cursive",
    },
    # ---- референс-шаблоны ----
    "D": {
        "FONT_LINK": _GV + "?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400"
                     "&family=Golos+Text:wght@400;500;600;700&family=Great+Vibes&display=swap",
        "FONT_HEAD": "'Cormorant Garamond', 'Times New Roman', serif",
        "FONT_TEXT": "'Golos Text', system-ui, sans-serif",
        "FONT_NAME": "'Great Vibes', 'Segoe Script', cursive",
    },
    "E": {
        "FONT_LINK": _GV + "?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500"
                     "&family=Manrope:wght@400;500;600;700&family=Great+Vibes&display=swap",
        "FONT_HEAD": "'Cormorant Garamond', 'Times New Roman', serif",
        "FONT_TEXT": "'Manrope', system-ui, sans-serif",
        "FONT_NAME": "'Great Vibes', 'Segoe Script', cursive",
    },
    "F": {
        "FONT_LINK": _GV + "?family=Caveat:wght@500;600;700&family=Manrope:wght@400;500;600;700;800"
                     "&family=JetBrains+Mono:wght@400;500;700&display=swap",
        "FONT_HEAD": "'Manrope', system-ui, sans-serif",
        "FONT_TEXT": "'Manrope', system-ui, sans-serif",
        "FONT_NAME": "'Caveat', 'Segoe Script', cursive",
    },
    "G": {
        "FONT_LINK": _GV + "?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400"
                     "&family=Manrope:wght@400;500;600;700&family=Great+Vibes&display=swap",
        "FONT_HEAD": "'Cormorant Garamond', 'Times New Roman', serif",
        "FONT_TEXT": "'Manrope', system-ui, sans-serif",
        "FONT_NAME": "'Great Vibes', 'Segoe Script', cursive",
    },
}

# общий JS для всех трёх шаблонов
SHARED_SCRIPT = r"""<script>
  function buildCalendar(id, year, m, hi){
    var T=['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
    var W=['пн','вт','ср','чт','пт','сб','вс'];
    var c=document.getElementById(id); if(!c) return;
    var first=new Date(year,m,1), off=(first.getDay()+6)%7, dim=new Date(year,m+1,0).getDate();
    var o='<div class="cal-month">'+T[m]+' '+year+'</div><div class="cal-grid">';
    W.forEach(function(d){o+='<div class="cal-dow">'+d+'</div>';});
    for(var i=0;i<off;i++) o+='<div class="cal-cell empty"></div>';
    for(var d=1;d<=dim;d++) o+='<div class="cal-cell'+(d===hi?' cal-highlight':'')+'">'+d+'</div>';
    c.innerHTML=o+'</div>';
  }
  buildCalendar('calendarCard', {{CAL_YEAR}}, {{CAL_MONTH_INDEX}}, {{CAL_DAY}});

  var EVENT_DATE=new Date('{{EVENT_DATE_ISO}}');
  function pad(n){return n<10?'0'+n:''+n;}
  function tick(){
    var diff=EVENT_DATE-new Date(); if(diff<0) diff=0;
    var el;
    if((el=document.getElementById('cdDays'))) el.textContent=pad(Math.floor(diff/86400000));
    if((el=document.getElementById('cdHours'))) el.textContent=pad(Math.floor((diff%86400000)/3600000));
    if((el=document.getElementById('cdMinutes'))) el.textContent=pad(Math.floor((diff%3600000)/60000));
    if((el=document.getElementById('cdSeconds'))) el.textContent=pad(Math.floor((diff%60000)/1000));
  }
  tick(); setInterval(tick,1000);

  document.addEventListener('DOMContentLoaded',function(){
    var els=document.querySelectorAll('.reveal');
    if('IntersectionObserver' in window){
      var obs=new IntersectionObserver(function(en){
        en.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('visible'); obs.unobserve(e.target); } });
      },{threshold:0.12});
      els.forEach(function(e){ obs.observe(e); });
      setTimeout(function(){ els.forEach(function(e){ e.classList.add('visible'); }); }, 3000);
    } else { els.forEach(function(e){ e.classList.add('visible'); }); }
  });

  function addGuestRow(focus){
    var host=document.getElementById('extraGuestsList'); if(!host) return;
    var row=document.createElement('div'); row.className='guest-row';
    var inp=document.createElement('input'); inp.type='text'; inp.className='extra-guest-input'; inp.placeholder='Имя и фамилия гостя';
    var rm=document.createElement('button'); rm.type='button'; rm.className='remove-guest';
    rm.setAttribute('aria-label','Убрать гостя'); rm.textContent='×';
    rm.addEventListener('click',function(){ row.remove(); });
    row.appendChild(inp); row.appendChild(rm);
    host.appendChild(row); if(focus) inp.focus();
  }
  addGuestRow(false);
  var addBtn=document.getElementById('addGuestBtn');
  if(addBtn) addBtn.addEventListener('click',function(){ addGuestRow(true); });

  document.getElementById('rsvpForm').addEventListener('submit', async function(e){
    e.preventDefault();
    var name=document.getElementById('guestName').value.trim();
    var st=document.getElementById('rsvpStatus'); st.textContent='';
    if(!name){ st.textContent='Пожалуйста, впишите имя.'; return; }
    var btn=document.getElementById('rsvpSubmit'); btn.disabled=true; btn.textContent='Отправляем...';
    try{
      var extras=Array.from(document.querySelectorAll('.extra-guest-input')).map(function(i){return i.value.trim();}).filter(Boolean);
      var noteEl=document.getElementById('guestNote'); var note=noteEl?noteEl.value.trim():'';
      var resp=await fetch('{{RSVP_API}}/rsvp',{
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({ wedding:'{{WEDDING_ID}}', name:name, guests:extras, note:note })
      });
      if(!resp.ok) throw new Error('rsvp '+resp.status);
      document.getElementById('rsvpForm').style.display='none';
      var t=document.getElementById('rsvpThanks');
      t.textContent='Спасибо! Будем очень рады видеть вас {{DATE_SHORT}}.';
      t.style.display='block';
    }catch(err){
      st.textContent='Не получилось отправить. Попробуйте ещё раз.';
      btn.disabled=false; btn.textContent='Подтвердить участие';
    }
  });
</script>"""


def e(s):
    return html.escape(str(s), quote=False)


def dir_name(c):
    """Папка пары на диске: «NN Имена» кириллицей — удобно открывать глазами.
    URL сайта, foto-ishodniki/ и assets/works/ остаются на slug (латиница),
    чтобы не ломать ссылки. dir_name используют build_priglashenie.py и pack.js."""
    return f'{c["order"]} {c["names"]}'


def derive(c):
    d = datetime.date.fromisoformat(c["date_iso"])
    dh = f"{d.day} {MONTHS_GEN[d.month - 1]} {d.year}"
    return {
        "DATE_HUMAN": dh, "DATE_SHORT": f"{d.day} {MONTHS_GEN[d.month - 1]}",
        "WHEN_VALUE": dh, "WHEN_EXTRA": f"{WD[d.weekday()]}, {c['when_extra_tail']}",
        "EVENT_DATE_ISO": f"{c['date_iso']}T{c['time']}:00+03:00",
        "CAL_YEAR": str(d.year), "CAL_MONTH_INDEX": str(d.month - 1), "CAL_DAY": str(d.day),
        "DATE_DD": f"{d.day:02d}", "DATE_MM": f"{d.month:02d}", "DATE_YYYY": str(d.year),
        "DATE_NUMERIC": f"{d.day:02d} · {d.month:02d} · {d.year}",
    }


def program_html(rows):
    out = []
    for t, title, note in rows:
        nh = f'<div class="tl-note">{e(note)}</div>' if note else ""
        out.append(f'<div class="tl-item"><div class="tl-time">{e(t)}</div>'
                   f'<div class="tl-title">{e(title)}</div>{nh}</div>')
    return "\n        ".join(out)


def swatches_html(items):
    return "\n        ".join(
        f'<div class="swatch"><i style="background:{hx}"></i><span>{e(lb)}</span></div>'
        for hx, lb in items)


def faq_html(items):
    return "\n        ".join(
        f'<details><summary>{e(q)}</summary><div class="faq-body">{e(a)}</div></details>'
        for q, a in items)


def render(tpl, repl):
    out = tpl.replace("{{SCRIPT}}", SHARED_SCRIPT)
    for k, v in repl.items():
        out = out.replace("{{" + k + "}}", str(v))
    leftover = sorted({seg.split("}}")[0] for seg in out.split("{{")[1:]})
    if leftover:
        raise SystemExit(f"НЕЗАКРЫТЫЕ токены: {leftover}")
    return out


def build_concept(c, tpl_cache, guests_tpl):
    slug = c["slug"]
    jp = IMG_DIR / slug / "images.json"
    if not jp.exists():
        raise SystemExit(f"нет {jp} — сначала запустите fetch_images.py")
    uris = json.loads(jp.read_text(encoding="utf-8"))
    p, dd = c["palette"], derive(c)
    f = TEMPLATE_FONTS[c["template"]]
    g1, g2, g3 = c["gallery_captions"]

    base = {
        "LANG": "ru",
        "TITLE": f'{c["names"]} — {dd["DATE_HUMAN"]}',
        "OG_TITLE": f'{c["names"]} приглашают на свадьбу',
        "OG_DESC": f'{dd["DATE_HUMAN"]} · {c["city_venue"]}',
        "IMG_HERO": uris["hero"], "IMG_G1": uris["g1"], "IMG_G2": uris["g2"], "IMG_G3": uris["g3"],
        "GCAP1": e(g1), "GCAP2": e(g2), "GCAP3": e(g3),
        "NAMES": e(c["names"]), "INITIALS": e(c["initials"]),
        "HERO_EYEBROW": e(c["hero_eyebrow"]), "CITY_VENUE": e(c["city_venue"]),
        "INTRO_LEAD": e(c["intro_lead"]), "INTRO_BODY": e(c["intro_body"]),
        "WHERE_VALUE": e(c["where_value"]), "WHERE_EXTRA": e(c["where_extra"]),
        "MAP_URL": "https://yandex.ru/maps/?text=" + urllib.parse.quote(c["map_query"]),
        "PROGRAM_SUB": e(c["program_sub"]), "PROGRAM_ROWS": program_html(c["program"]),
        "DRESSCODE_NOTE": e(c["dresscode_note"]), "DRESSCODE_SWATCHES": swatches_html(c["dresscode"]),
        "FAQ_ITEMS": faq_html(c["faq"]),
        "RSVP_LEAD": e(c["rsvp_lead"]), "RSVP_EXTRA_LABEL": e(c["rsvp_extra_label"]),
        "RSVP_NOTE": e(c["rsvp_note"]), "FOOTER_LINE": e(c["footer_line"]),
        "VENUE_SHORT": e(c["venue_short"]),
        "RSVP_API": RSVP_API, "WEDDING_ID": slug,
        "TIME": e(c["time"]),
    }
    base.update(dd)
    base.update(f)
    base.update(p)

    out_dir = PORTF / dir_name(c)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render(tpl_cache[c["template"]], base), encoding="utf-8")
    (out_dir / "spisok-gostey.html").write_text(render(guests_tpl, base), encoding="utf-8")
    return c["template"], (out_dir / "index.html").stat().st_size / 1024


def build_index():
    cards = []
    for c in CONCEPTS:
        p, f, dd = c["palette"], TEMPLATE_FONTS[c["template"]], derive(c)
        cards.append(f"""
      <a class="card" href="{urllib.parse.quote(dir_name(c))}/index.html" style="--c-ink:{p['C_INK']};--c-bg:{p['C_BG']};--c-accent:{p['C_ACCENT']};--c-text:{p['C_TEXT']};--c-soft:{p['C_TEXT_SOFT']}">
        <div class="card-sw"><i style="background:{p['C_INK']}"></i><i style="background:{p['C_ACCENT']}"></i><i style="background:{p['C_BG2']}"></i><i style="background:{p['C_BG']}"></i></div>
        <div class="card-body">
          <div class="card-num">{c['order']} · шаблон {c['template']}</div>
          <div class="card-names">{e(c['names'])}</div>
          <div class="card-style">{e(c['style_name'])}</div>
          <div class="card-meta">{dd['DATE_HUMAN']} · {e(c['city_venue'])}</div>
        </div>
      </a>""")
    page = f"""<!DOCTYPE html><html lang="ru"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Портфолио свадебных приглашений</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Great+Vibes&family=Manrope:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;}} body{{margin:0;font-family:'Manrope',system-ui,sans-serif;background:#F1EDE7;color:#2A2420;line-height:1.6;-webkit-font-smoothing:antialiased;}}
  header{{text-align:center;padding:clamp(60px,10vw,110px) 24px 36px;}}
  header .script{{font-family:'Great Vibes',cursive;font-size:clamp(46px,9vw,74px);color:#8A5B53;line-height:1;}}
  header p{{max-width:540px;margin:16px auto 0;color:#6b6055;font-size:15px;}}
  .grid{{max-width:1120px;margin:0 auto;padding:16px 20px 100px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:22px;}}
  .card{{display:block;text-decoration:none;background:var(--c-bg);border:1px solid rgba(0,0,0,0.10);overflow:hidden;transition:transform .2s,box-shadow .2s;}}
  .card:hover{{transform:translateY(-4px);box-shadow:0 16px 40px rgba(0,0,0,0.13);}}
  .card-sw{{display:flex;height:80px;}} .card-sw i{{flex:1;display:block;}}
  .card-body{{padding:20px 22px 24px;color:var(--c-text);}}
  .card-num{{font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:var(--c-soft);}}
  .card-names{{font-family:'Great Vibes',cursive;font-size:34px;line-height:1.05;margin:6px 0 8px;color:var(--c-ink);}}
  .card-style{{font-size:13.5px;font-weight:600;color:var(--c-accent);}}
  .card-meta{{font-size:12.5px;color:var(--c-soft);margin-top:6px;}}
  footer{{text-align:center;padding:0 24px 80px;color:#8a7f72;font-size:13px;}}
</style></head><body>
  <header><div class="script">Портфолио</div>
  <p>Свадебные сайты-приглашения. 14 работ, семь вариантов компоновки: три базовых (A, B, C) и четыре по референсам (D, E, F, G). Откройте любую, чтобы посмотреть целиком.</p></header>
  <div class="grid">{''.join(cards)}
  </div>
  <footer>Каждый лендинг — отдельная страница с формой для ответов гостей и приватным списком.</footer>
</body></html>
"""
    (PORTF / "index.html").write_text(page, encoding="utf-8")


def main():
    tpl_cache = {k: (TPL_DIR / v).read_text(encoding="utf-8") for k, v in TEMPLATE_FILE.items()}
    guests_tpl = (TPL_DIR / "guests.template.html").read_text(encoding="utf-8")
    print("Сборка портфолио:")
    for c in CONCEPTS:
        t, kb = build_concept(c, tpl_cache, guests_tpl)
        print(f"  {dir_name(c):36s}  [{t}]  index.html {kb:6.0f} KB")
    build_index()
    print("  ПОРТФОЛИО/index.html — витрина собрана")

    # dir <-> slug для pack.js/shot.js (у них нет доступа к concepts.py)
    meta = [{"dir": dir_name(c), "slug": c["slug"], "order": c["order"], "names": c["names"]}
            for c in CONCEPTS]
    (PORTF / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ПОРТФОЛИО/_meta.json — соответствие «папка - slug» для скриптов в ТЕЛЕГА/скрипты")
    print("Готово.")


if __name__ == "__main__":
    main()
