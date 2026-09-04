// Комплект «для гостей без интернета» + PDF бумажного приглашения.
//
// Для каждой работы (или одной, если передать номер) делает:
//   ПОРТФОЛИО/<slug>/dlya-gostey/priglashenie-sayt.pdf   — весь лендинг одним PDF
//   ПОРТФОЛИО/<slug>/dlya-gostey/screens/NN-*.png        — экраны лендинга картинками
//   ПОРТФОЛИО/<slug>/priglashenie/priglashenie-A5.pdf    — бумажное приглашение (A5, 2 стр.)
//
// Бумажный HTML-макет A5 создаёт python materialy/build/build_priglashenie.py —
// запусти его перед этим скриптом.
//
// Запуск:  node pack.js           — все 14 работ
//          node pack.js 03        — только 03-...
//          BROWSER="C:\\...\\chrome.exe" node pack.js
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const EDGE = process.env.BROWSER || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const ROOT = path.join(__dirname, '..', '..');
const PORT = path.join(ROOT, 'ПОРТФОЛИО');
const ONLY = process.argv[2] || null;   // '03' -> только работа, чей slug начинается с '03-'

const KILL_ANIM = `
  *,*::before,*::after{animation-duration:0s!important;animation-delay:0s!important;transition:none!important}
  .reveal,[class*="reveal"]{opacity:1!important;transform:none!important;filter:none!important}
`;

const SECTIONS = [
  ['details', 'дата-и-адрес'],
  ['program', 'программа'],
  ['gallery', 'галерея'],
  ['dresscode', 'дресс-код'],
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const fileUrl = (p) => 'file:///' + p.replace(/\\/g, '/');

async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      let y = 0;
      const t = setInterval(() => {
        window.scrollBy(0, 400); y += 400;
        if (y >= document.body.scrollHeight + 1000) { clearInterval(t); window.scrollTo(0, 0); resolve(); }
      }, 60);
    });
  });
  await sleep(500);
}

async function landingPack(browser, slug) {
  const src = path.join(PORT, slug, 'index.html');
  if (!fs.existsSync(src)) { console.log(`skip ${slug}: нет index.html`); return; }

  const outDir = path.join(PORT, slug, 'dlya-gostey');
  const shotDir = path.join(outDir, 'screens');
  fs.rmSync(outDir, { recursive: true, force: true });
  fs.mkdirSync(shotDir, { recursive: true });

  const page = await browser.newPage();
  try {
    await page.setViewport({ width: 900, height: 1200, deviceScaleFactor: 2 });
    await page.goto(fileUrl(src), { waitUntil: 'networkidle0', timeout: 90000 });
    await page.addStyleTag({ content: KILL_ANIM });
    try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch {}
    await autoScroll(page);

    // весь лендинг → PDF (A4, с фоном)
    await page.pdf({
      path: path.join(outDir, 'priglashenie-sayt.pdf'),
      format: 'A4', printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 },
    });

    // экраны картинками
    await page.screenshot({ path: path.join(shotDir, '1-обложка.png'), type: 'png' });
    const intro = (await page.evaluateHandle(() => {
      const s = [...document.querySelectorAll('section')];
      return s.find((x) => !x.id && !x.classList.contains('hero')) || null;
    })).asElement();
    let n = 2;
    if (intro) {
      await intro.evaluate((el) => el.scrollIntoView({ block: 'center' }));
      await sleep(300);
      try { await intro.screenshot({ path: path.join(shotDir, '2-приглашение.png'), type: 'png' }); n = 3; } catch {}
    }
    for (const [id, name] of SECTIONS) {
      const el = await page.$('#' + id);
      if (!el) continue;
      await el.evaluate((x) => x.scrollIntoView({ block: 'center' }));
      await sleep(300);
      try { await el.screenshot({ path: path.join(shotDir, `${n}-${name}.png`), type: 'png' }); n++; } catch {}
    }
    console.log(`OK  ${slug}  → dlya-gostey/ (PDF + ${n - 1} экранов)`);
  } catch (e) {
    console.log(`ERR ${slug}: ${e.message}`);
  } finally {
    await page.close();
  }
}

async function invitePdf(browser, slug) {
  const src = path.join(PORT, slug, 'priglashenie', 'index.html');
  if (!fs.existsSync(src)) { console.log(`skip ${slug}: нет priglashenie/index.html — сначала build_priglashenie.py`); return; }
  const page = await browser.newPage();
  try {
    await page.goto(fileUrl(src), { waitUntil: 'networkidle0', timeout: 60000 });
    try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch {}
    await sleep(300);
    await page.pdf({
      path: path.join(PORT, slug, 'priglashenie', 'priglashenie-A5.pdf'),
      width: '148mm', height: '210mm', printBackground: true, pageRanges: '1-2',
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    console.log(`OK  ${slug}  → priglashenie/priglashenie-A5.pdf`);
  } catch (e) {
    console.log(`ERR ${slug} (A5): ${e.message}`);
  } finally {
    await page.close();
  }
}

(async () => {
  let dirs = fs.readdirSync(PORT)
    .filter((d) => /^\d\d-/.test(d) && fs.existsSync(path.join(PORT, d, 'index.html')))
    .sort();
  if (ONLY) dirs = dirs.filter((d) => d.startsWith(ONLY.replace(/\D.*$/, '').padStart(2, '0') + '-'));
  if (!dirs.length) { console.log('нечего собирать'); return; }

  const browser = await puppeteer.launch({
    executablePath: EDGE, headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars', '--force-color-profile=srgb'],
  });
  for (const slug of dirs) {
    await landingPack(browser, slug);
    await invitePdf(browser, slug);
  }
  await browser.close();
  console.log('\nГотово.');
})();
