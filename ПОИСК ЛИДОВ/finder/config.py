"""Загрузка настроек из config.json рядом с проектом (с дефолтами)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"

DEFAULTS = {
    "keywords_wedding": ["свадеб", "свадьб", "wedding", "венчан", "молодожен",
                         "молодожён", "невест", "жених", "бракосочетан", "помолвк"],
    "keywords_site": ["лендинг", "landing", "сайт", "приглашени", "invite", "invitation",
                      "one page", "onepage", "одностраничник", "одностраничн",
                      "промостраниц", "микросайт", "tilda", "тильда", "визитк"],
    "keywords_negative": ["фотограф", "видеограф", "видеосъём", "видеосъем", "монтаж видео",
                          "ведущий", "тамада", "платье", "торт", "букет", "флорист",
                          "декор зала", "оформление зала", "стилист", "макияж",
                          "печать приглашен", "полиграф", "типограф"],
    "phrases_bonus": ["сайт-приглашение", "свадебный сайт", "свадебный лендинг",
                      "лендинг на свадьбу", "сайт на свадьбу", "wedding landing",
                      "wedding site", "wedding invitation", "пригласительный сайт"],
    "fl_ru_feeds": ["https://www.fl.ru/rss/projects.xml",
                    "https://www.fl.ru/rss/projects.xml?category=5",
                    "https://www.fl.ru/rss/projects.xml?category=8",
                    "https://www.fl.ru/rss/all.xml"],
    "kwork_pages": 4,
    "kwork_categories": ["", "11", "13"],
    "telegram_channels": ["workzavr", "rabota_freelancer", "udalenka_it"],
    "manual_links": [],
}


def load_config(path=None):
    cfg = dict(DEFAULTS)
    p = Path(path) if path else CONFIG_PATH
    if p.exists():
        try:
            user = json.loads(p.read_text(encoding="utf-8"))
            for k, v in user.items():
                if k.startswith("_"):
                    continue
                cfg[k] = v
        except (json.JSONDecodeError, OSError):
            pass
    return cfg
