"""Оценка релевантности запроса: свадебный это лендинг или нет, бюджет, корзина."""
import re
import unicodedata

_WS = re.compile(r"\s+")


def normalize(text):
    """К нижнему регистру, ё→е, убрать html-теги и лишние пробелы."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(text))
    text = unicodedata.normalize("NFKC", text).lower().replace("ё", "е")
    return _WS.sub(" ", text).strip()


# --- бюджет -------------------------------------------------------------------
_MONEY_KW = ("бюджет", "бюдж", "цена", "стоимост", "оплат", "заплач", "заплат",
             "прайс", "гонорар", "за работу", "вознагражд", "плачу")
_MONEY = re.compile(
    r"(?P<cur>\$|€)?\s*"
    r"(?P<num>\d[\d\s]{0,8}\d|\d)\s*"
    r"(?P<unit>тыс(?:яч|\.)?|т\.?\s?р\.?|к\b|k\b|руб\w*|р\.|₽|\$|000\b)?",
    re.I,
)


def parse_budget(text):
    """Бюджет в рублях (int) или None. Нужен денежный сигнал:
    либо ключевое слово рядом, либо валюта/«тыс»/«к» у числа."""
    t = normalize(text)
    best = None
    for m in _MONEY.finditer(t):
        digits = re.sub(r"\D", "", m.group("num"))
        if not digits:
            continue
        val = int(digits)
        unit = (m.group("unit") or "").lower()
        cur = m.group("cur") or ""
        before = t[max(0, m.start() - 22):m.start()]
        has_kw = any(k in before for k in _MONEY_KW)
        has_unit = bool(unit) or bool(cur)
        if not (has_kw or has_unit):
            continue  # просто число (например «3 фото», «2026 год»)
        if unit.startswith(("тыс", "т.", "тр", "т р", "к", "k")) or unit == "000":
            val *= 1000
        if "$" in (unit + cur) or "€" in cur:
            val *= 95
        # отсечь явные «годы» без денежного контекста
        if 1990 <= val <= 2099 and not has_kw and unit in ("", "000"):
            continue
        if 300 <= val <= 5_000_000:
            best = val if best is None else max(best, val)
    return best


# --- скоринг ----------------------------------------------------------------
def _has_any(text, terms):
    return [w for w in terms if w in text]


def score_lead(title, description, cfg, age_hours=None):
    """
    Возвращает dict: score, bucket ('exact'|'similar'|'drop'), reasons, budget,
    matched (список сработавших слов).
    """
    t = normalize((title or "") + " . " + (description or ""))
    wed = _has_any(t, [normalize(w) for w in cfg["keywords_wedding"]])
    site = _has_any(t, [normalize(w) for w in cfg["keywords_site"]])
    neg = _has_any(t, [normalize(w) for w in cfg["keywords_negative"]])
    phr = _has_any(t, [normalize(w) for w in cfg["phrases_bonus"]])
    budget = parse_budget(t)

    score = 0.0
    reasons = []
    if wed and site:
        score += 5
        reasons.append("свадьба + сайт")
    if phr:
        score += 2
        reasons.append("точная фраза: " + ", ".join(phr[:2]))
    if "приглашени" in t and "сайт" in t:
        score += 1
    if budget:
        score += 1
        reasons.append(f"бюджет ~{budget:,}".replace(",", " ") + " ₽")
    if neg and not site:
        score -= 4
        reasons.append("похоже на другую услугу: " + ", ".join(neg[:2]))
    if age_hours is not None:
        if age_hours <= 24:
            score += 2
        elif age_hours <= 72:
            score += 1

    if wed and site and score >= 5:
        bucket = "exact"
    elif site and any(k in t for k in ("лендинг", "landing", "одностранич", "промостраниц", "промо-страниц")) \
            and not wed and score > -2 and not (neg and not site):
        bucket = "similar"
    else:
        bucket = "drop"

    return {
        "score": round(score, 1),
        "bucket": bucket,
        "reasons": reasons,
        "budget": budget,
        "matched": {"wedding": wed, "site": site, "negative": neg, "phrases": phr},
    }
