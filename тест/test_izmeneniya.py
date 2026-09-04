# -*- coding: utf-8 -*-
"""
Тесты под правки от 2026-09-04:

  • витрина САЙТ/ — глазами посетителя: нет «RSVP», нет «14 сайтов», нет «анкеты»
    и «перевода на карту»; есть «бриф» и объяснение, зачем он; на карточках работ —
    палитра; отзывы без служебной пометки; на «Как это работает» — платный доп
    «бумажное приглашение».
  • бумажное приглашение A5 — юнит-тесты генератора build_priglashenie.py:
    папки пар в ПОРТФОЛИО/ — «NN Имена» кириллицей, приглашение лежит в
    «<пара>/для печати/»; лицо = фото из шапки лендинга + тёплые слова,
    оборот = что/где/когда, без блока «добавить гостей» и без формы, все
    токены закрыты.

Запуск:  python тест/test_izmeneniya.py
         python -m unittest discover -s тест -p "test_*.py"
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAYT_DIST = ROOT / "САЙТ" / "dist"
BUILD_DIR = ROOT / "materialy" / "build"
PORTF = ROOT / "ПОРТФОЛИО"


def run(*args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, f"{args} упал:\n{r.stdout}\n{r.stderr}"
    return r.stdout


def build_all():
    run("САЙТ/build_sayt.py")
    run("materialy/build/build_priglashenie.py")


class StorefrontUserView(unittest.TestCase):
    """Что видит человек, открывший сайт."""

    @classmethod
    def setUpClass(cls):
        build_all()
        # страницы самой витрины (то, что читает будущий заказчик)
        cls.pages = {}
        for p in SAYT_DIST.glob("**/index.html"):
            rel = p.relative_to(SAYT_DIST)
            if rel.parts[0] == "works":          # лендинги пар — это отдельный продукт
                continue
            cls.pages["index" if rel.parent == Path(".") else rel.parent.name] = \
                p.read_text(encoding="utf-8")
        cls.all_html = "\n".join(cls.pages.values())
        # лендинги пар, вшитые в витрину
        cls.landings = [p.read_text(encoding="utf-8")
                        for p in SAYT_DIST.glob("works/*/index.html")]

    def test_vse_stranicy_sobrany(self):
        for slug in ("index", "portfolio", "kak-eto-rabotaet", "otzyvy"):
            self.assertIn(slug, self.pages, f"нет страницы {slug}")

    def test_net_nezakrytyh_tokenov(self):
        for name, html in self.pages.items():
            self.assertNotIn("{{", html, f"незакрытый токен на странице {name}")

    def test_net_slova_rsvp_na_vitrine(self):
        for name, html in self.pages.items():
            self.assertNotIn("RSVP", html, f"«RSVP» осталось на странице {name}")

    def test_landingi_bez_vidimogo_rsvp(self):
        # в разметке лендинга «RSVP» допустимо только как невидимый служебный
        # идентификатор (class="rsvp", id="rsvp", css-комментарий), но не как текст
        self.assertTrue(self.landings, "лендинги не попали в dist/works/")
        for html in self.landings:
            self.assertNotRegex(html, r">\s*RSVP\s*<")
            self.assertNotRegex(html, r'kicker[^>]*>\s*RSVP')

    def test_net_14_saytov(self):
        self.assertNotRegex(self.all_html, r"14\s+сайт")

    def test_net_ankety_i_perevoda_na_kartu(self):
        kak = self.pages["kak-eto-rabotaet"]
        self.assertNotIn("анкет", kak.lower())
        self.assertNotRegex(kak, r"[Пп]еревод\S*\s+\S*\s*карт")

    def test_est_brief_i_zachem_on(self):
        kak = self.pages["kak-eto-rabotaet"]
        self.assertIn("бриф", kak.lower())
        # объяснение «зачем», а не «что внутри»
        self.assertRegex(kak, r"чтобы сайт (получился про вас|был про вас)")

    def test_forma_obratnoy_svyazi_ponyatnym_yazykom(self):
        idx = self.pages["index"]
        self.assertIn("форма обратной связи для гостей", idx)

    def test_kartochki_rabot_pokazyvayut_palitru(self):
        for name in ("index", "portfolio"):
            html = self.pages[name]
            self.assertIn("work-palette", html, f"нет полоски палитры на {name}")
            dots = re.findall(r'<i style="background:#[0-9A-Fa-f]{3,8}"', html)
            self.assertGreaterEqual(len(dots), 5 * 4,
                                    f"на {name} мало цветных плашек: {len(dots)}")

    def test_otzyvy_bez_sluzhebnoy_pometki(self):
        self.assertNotIn('class="soon"', self.pages["otzyvy"])

    def test_bumazhnoe_priglashenie_kak_platnyy_dop(self):
        kak = self.pages["kak-eto-rabotaet"]
        self.assertIn("Бумажное приглашение", kak)
        self.assertRegex(kak, r"1\s*500")
        self.assertIn("A5", kak)


class PaperInvitationBuild(unittest.TestCase):
    """Юнит-тесты генератора бумажного приглашения."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(BUILD_DIR))
        run("materialy/build/build_priglashenie.py")
        import build_priglashenie as bp
        import build
        from concepts import CONCEPTS
        cls.bp = bp
        cls.dir_name = staticmethod(build.dir_name)
        cls.concepts = CONCEPTS

    def test_render_padaet_na_nezakrytom_tokene(self):
        with self.assertRaises(SystemExit):
            self.bp.render("привет {{НЕТ_ТАКОГО}} пока", {"NAMES": "тест"})

    def test_fields_zakryvaet_vse_tokeny_shablona(self):
        tpl = (ROOT / "shablon" / "priglashenie-A5.template.html").read_text(encoding="utf-8")
        for c in self.concepts:
            out = self.bp.render(tpl, self.bp.fields(c))   # бросит SystemExit, если что-то не закрыто
            self.assertNotIn("{{", out)

    def test_sobrany_vse_14(self):
        made = sorted(p.parent.parent.name for p in PORTF.glob("*/для печати/index.html"))
        self.assertEqual(len(made), len(self.concepts))

    def test_papki_kirillicej_nomer_i_imena(self):
        for c in self.concepts:
            self.assertTrue((PORTF / self.dir_name(c)).is_dir(),
                            f"нет папки «{self.dir_name(c)}» в ПОРТФОЛИО")

    def test_licо_shapka_plyus_teplye_slova(self):
        for c in self.concepts:
            html = (PORTF / self.dir_name(c) / "для печати" / "index.html").read_text(encoding="utf-8")
            front = html.split('aria-label="Оборотная сторона"')[0]
            self.assertIn(c["names"], front)
            self.assertIn(c["hero_eyebrow"], front)
            self.assertIn(c["intro_lead"][:40], front, f"нет текста под фото у {c['slug']}")
            self.assertIn('class="cover-photo"', front, f"нет фото на лицевой у {c['slug']}")
            self.assertIn("data:image/", front, f"фото не встроено (пустой src) у {c['slug']}")

    def test_oborot_chto_gde_kogda(self):
        import datetime
        for c in self.concepts:
            html = (PORTF / self.dir_name(c) / "для печати" / "index.html").read_text(encoding="utf-8")
            back = html.split('aria-label="Оборотная сторона"')[1]
            d = datetime.date.fromisoformat(c["date_iso"])
            self.assertIn("Что, где и когда", back)
            self.assertIn(str(d.year), back)
            self.assertIn(c["where_value"], back)
            self.assertIn(c["where_extra"], back)
            self.assertIn(c["time"], back)
            self.assertEqual(back.count('<i style="background:'), 5, f"дресс-код у {c['slug']}")

    def test_na_bumage_net_dobavit_gostey_i_formy(self):
        for c in self.concepts:
            html = (PORTF / self.dir_name(c) / "для печати" / "index.html").read_text(encoding="utf-8")
            # вырезаем data:-URI фото (в base64 случайно попадаются любые буквы)
            markup = re.sub(r"data:image/[^\"')]+", "", html).lower()
            self.assertNotIn("добавить гост", markup)
            self.assertNotIn("<form", markup)
            self.assertNotRegex(markup, r"\brsvp\b")

    def test_ssylka_na_lending_pary(self):
        for c in self.concepts:
            html = (PORTF / self.dir_name(c) / "для печати" / "index.html").read_text(encoding="utf-8")
            self.assertIn(f"pro-dvoih.ru/works/{c['slug']}/", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
