from finder.matching import normalize, parse_budget, score_lead


def test_normalize_strips_tags_and_yo():
    assert normalize("<p>Привет  ЁЖ</p>") == "привет еж"
    assert normalize(None) == ""


def test_parse_budget_variants():
    assert parse_budget("бюджет 12000 руб") == 12000
    assert parse_budget("Бюджет: до 15 000 ₽") == 15000
    assert parse_budget("оплата 10 т.р.") == 10000
    assert parse_budget("заплачу 8к") == 8000
    assert parse_budget("около 20 тыс руб") == 20000
    assert parse_budget("$300") == 300 * 95
    assert parse_budget("сделаю за спасибо") is None
    assert parse_budget("нужно к 2026 году") is None  # год не бюджет


def test_score_exact(cfg):
    r = score_lead("Нужен сайт-приглашение на свадьбу",
                   "Свадебный лендинг на Tilda, бюджет 12000 руб", cfg, age_hours=2)
    assert r["bucket"] == "exact"
    assert r["budget"] == 12000
    assert r["matched"]["wedding"] and r["matched"]["site"]


def test_score_similar(cfg):
    r = score_lead("Landing page для онлайн-курса",
                   "Сделать лендинг на Tilda, бюджет 20000", cfg)
    assert r["bucket"] == "similar"


def test_score_drop_wedding_video(cfg):
    r = score_lead("Смонтировать свадебное видео",
                   "Монтаж свадебного видео из материала", cfg)
    assert r["bucket"] == "drop"


def test_score_drop_unrelated(cfg):
    r = score_lead("Нужен бухгалтер на аутсорс", "Ведение ООО на УСН", cfg)
    assert r["bucket"] == "drop"
