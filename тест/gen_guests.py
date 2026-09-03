# -*- coding: utf-8 -*-
"""
Генерит 100 заявок RSVP в формате лендинга ({name, guests[], note, ts}) и
собирает статичный список-гостей-100.html — тот же шаблон guests.template.html,
но с вшитыми данными, открывается файлом без window.storage.

Запуск:  python тест/gen_guests.py
"""
import json
import random
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLUG = "test-egor-i-valeriya-shalfej"
STORAGE_KEY = "guest_list_test_egor_i_valeriya_shalfej"
LP_DIR = HERE / "output" / SLUG

random.seed(21082027)

M_FIRST = ["Александр", "Дмитрий", "Максим", "Иван", "Никита", "Егор", "Артём",
           "Илья", "Кирилл", "Михаил", "Роман", "Андрей", "Сергей", "Павел",
           "Владимир", "Антон", "Денис", "Григорий", "Фёдор", "Тимур"]
F_FIRST = ["Анна", "Мария", "Екатерина", "Ольга", "Дарья", "Валерия", "Софья",
           "Полина", "Ксения", "Виктория", "Алиса", "Елена", "Марина", "Юлия",
           "Наталья", "Ирина", "Татьяна", "Вера", "Алёна", "Кристина"]
LAST = ["Смирнов", "Кузнецов", "Попов", "Соколов", "Лебедев", "Козлов", "Новиков",
        "Морозов", "Петров", "Волков", "Соловьёв", "Васильев", "Зайцев", "Павлов",
        "Семёнов", "Голубев", "Виноградов", "Богданов", "Воробьёв", "Фёдоров",
        "Михайлов", "Беляев", "Тарасов", "Белов", "Комаров", "Орлов", "Киселёв",
        "Макаров", "Андреев", "Ковалёв"]

NOTES = [
    "", "", "", "", "", "", "",
    "Нужен трансфер от площади Минина, нас двое.",
    "У ребёнка аллергия на орехи.",
    "Приедем на своей машине, останемся на ночь.",
    "Вегетарианское меню, пожалуйста.",
    "Будем чуть позже — доедем к церемонии.",
    "Возьмём с собой сына, 5 лет, нужен детский стул.",
    "Без лактозы, если можно.",
    "Спасибо за приглашение, очень ждём!",
]


def lastname(base, female):
    return base + ("а" if female and not base.endswith(("ой", "их")) else "")


def person(female=None):
    female = random.random() < 0.5 if female is None else female
    fn = random.choice(F_FIRST if female else M_FIRST)
    ln = lastname(random.choice(LAST), female)
    return f"{fn} {ln}"


entries = []
now = int(time.time() * 1000)
for i in range(100):
    female_lead = random.random() < 0.5
    name = person(female_lead)
    roll = random.random()
    extras = []
    if roll < 0.34:                       # пара
        extras = [person(not female_lead)]
    elif roll < 0.5:                      # пара + ребёнок
        extras = [person(not female_lead), random.choice(F_FIRST + M_FIRST)]
    elif roll < 0.58:                     # семья 3+
        extras = [person(not female_lead)] + [random.choice(F_FIRST + M_FIRST)
                                              for _ in range(random.randint(2, 3))]
    # остальное — соло
    entries.append({
        "name": name,
        "guests": extras,
        "note": random.choice(NOTES),
        "ts": now - (100 - i) * random.randint(30_000, 4_000_000),
    })

people = sum(1 + len(e["guests"]) for e in entries)
(HERE / "гости-100.json").write_text(
    json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")

# --- статичная страница: тот же шаблон, данные вшиты ----------------------
tpl = (HERE.parent / "shablon" / "guests.template.html").read_text(encoding="utf-8")
pal = {
    "C_INK": "#2F352A", "C_BG": "#F2EFE6", "C_BG2": "#E4E1D2",
    "C_ACCENT": "#7E8A6A", "C_ACCENT_DEEP": "#5E6A4C",
    "C_LINE": "rgba(47,53,42,0.16)", "C_TEXT": "#33372C", "C_TEXT_SOFT": "#6B6E5C",
    "FONT_LINK": "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,"
                 "wght@0,400;0,500;0,600;1,400;1,500&family=Manrope:wght@400;500;600;700"
                 "&family=Great+Vibes&display=swap",
    "FONT_HEAD": "'Cormorant Garamond', 'Times New Roman', serif",
    "FONT_TEXT": "'Manrope', system-ui, sans-serif",
    "FONT_NAME": "'Great Vibes', 'Segoe Script', cursive",
    "NAMES": "Егор и Валерия", "DATE_HUMAN": "21 августа 2027",
    "VENUE_SHORT": "клуб «Сосновка»", "STORAGE_KEY": STORAGE_KEY,
}
for k, v in pal.items():
    tpl = tpl.replace("{{" + k + "}}", v)

# подменяем renderGuestList: вместо window.storage — вшитый массив
inject = ("var res = {value: JSON.stringify(" + json.dumps(entries, ensure_ascii=False) + ")};")
tpl = tpl.replace("var res = await window.storage.get('" + STORAGE_KEY + "', true);", inject)
(HERE / "список-гостей-100.html").write_text(tpl, encoding="utf-8")

print(f"заявок: {len(entries)}   человек придёт: {people}")
print(f"  гости-100.json")
print(f"  список-гостей-100.html  (открывается файлом, {len(tpl)//1024} KB)")

# как залить в опубликованный артефакт — через консоль браузера
snippet = (
    "// вставить в консоль на опубликованном лендинге (F12 → Console):\n"
    "await window.storage.set('" + STORAGE_KEY + "',\n"
    "  JSON.stringify(" + json.dumps(entries, ensure_ascii=False) + "), true);\n"
)
(HERE / "залить-100-в-артефакт.js.txt").write_text(snippet, encoding="utf-8")
print(f"  залить-100-в-артефакт.js.txt  (консольный сниппет)")
