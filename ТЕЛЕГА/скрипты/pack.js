// Комплект «для гостей без интернета» + PDF бумажного приглашения.
//
// Для каждой пары в ПОРТФОЛИО/<NN Имена>/ делает:
//   пдф и пнг версии/экраны/NN-*.png   — экраны лендинга картинками
//   пдф и пнг версии/приглашение.pdf   — те же экраны, собранные в один PDF
//                                         (по экрану на страницу A4, без искажений — не рендер с нуля,
//                                         поэтому не «расползается», как раньше при печати всего лендинга)
//   для печати/priglashenie-A5.pdf     — бумажное приглашение (A5, 2 стр.); HTML для него делает
//                                         python materialy/build/build_priglashenie.py — прогони его первым
//
// Запуск:  node pack.js           — все пары
//          node pack.js 03        — только пара №03
//          BROWSER="C:\\...\\chrome.exe" node pack.js
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const EDGE = process.env.BROWSER || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const ROOT = path.join(__dirname, '..', '..');
const PORT = path.join(ROOT, 'ПОРТФОЛИО');
const ONLY = process.argv[2] || null;   // '03' -> только пара, чья папка начинается с '03 '

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

// PDF из уже снятых картинок: каждая на своей A4-странице, вписана целиком без обрезки
// и без искажений (max-width/max-height:100%) — выглядит так же, как сами PNG.
async function pdfFromScreens(browser, shots, outPath) {
  const pages = shots.map(({ file }) => {
    const b64 = fs.readFileSync(file).toString('base64');
    return `<section class="pg"><img src="data:image/png;base64,${b64}"></section>`;
  }).join('');
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
    *{margin:0;padding:0;box-sizing:border-box}
    html,body{background:#fff}
    .pg{ width:210mm; height:297mm; display:flex; align-items:center; justify-content:center;
         overflow:hidden; page-break-after:always; }
    .pg:last-child{ page-break-after:auto; }
    .pg img{ max-width:100%; max-height:100%; display:block; }
    @page{ size:A4; margin:0; }
  </style></head><body>${pages}</body></html>`;
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: 'load' });
  // load-событие не всегда гарантирует, что огромные data:-URI успели отрисоваться —
  // ждём decode() каждой картинки явно, иначе PDF иногда уходит почти пустым.
  await page.evaluate(() => Promise.all(
    [...document.images].map((img) => img.decode().catch(() => {}))
  ));
  await page.pdf({ path: outPath, printBackground: true, preferCSSPageSize: true });
  await page.close();
}

async function landingPack(browser, dir) {
  const src = path.join(PORT, dir, 'index.html');
  if (!fs.existsSync(src)) { console.log(`skip ${dir}: нет index.html`); return; }

  const outDir = path.join(PORT, dir, 'пдф и пнг версии');
  const shotDir = path.join(outDir, 'экраны');
  fs.rmSync(outDir, { recursive: true, force: true });
  fs.mkdirSync(shotDir, { recursive: true });

  const page = await browser.newPage();
  const shots = [];
  try {
    await page.setViewport({ width: 900, height: 1200, deviceScaleFactor: 2 });
    await page.goto(pathToFileURL(src).href, { waitUntil: 'networkidle0', timeout: 90000 });
    await page.addStyleTag({ content: KILL_ANIM });
    try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch {}
    await autoScroll(page);

    async function grab(name, el) {
      const buf = await (el || page).screenshot({ type: 'png' });
      const file = path.join(shotDir, `${name}.png`);
      fs.writeFileSync(file, buf);
      // в pdfFromScreens картинку берём заново с диска, а не тот же buffer из памяти —
      // Chromium иногда встраивает в PDF версию картинки в разрешении по факту скрина
      // (единицы килобайт) вместо полной, если base64-кодировать буфер напрямую сразу
      // после screenshot(); файл с диска этого не делает.
      shots.push({ name, file });
    }

    await grab('1-обложка');

    // приглашение (секция «красивых слов»: без id, не hero)
    const introHandle = await page.evaluateHandle(() => {
      const secs = [...document.querySelectorAll('section')];
      return secs.find((s) => !s.id && !s.classList.contains('hero')) || null;
    });
    const introEl = introHandle.asElement();
    let n = 2;
    if (introEl) {
      await introEl.evaluate((e) => e.scrollIntoView({ block: 'center' }));
      await sleep(350);
      try { await grab('2-приглашение', introEl); n = 3; } catch {}
    }

    for (const [id, name] of SECTIONS) {
      const el = await page.$('#' + id);
      if (!el) continue;
      await el.evaluate((e) => e.scrollIntoView({ block: 'center' }));
      await sleep(350);
      try { await grab(`${n}-${name}`, el); n++; } catch {}
    }

    await pdfFromScreens(browser, shots, path.join(outDir, 'приглашение.pdf'));
    console.log(`OK  ${dir}  → пдф и пнг версии/ (${shots.length} экранов + PDF)`);
  } catch (e) {
    console.log(`ERR ${dir}: ${e.message}`);
  } finally {
    await page.close();
  }
}

async function invitePdf(browser, dir) {
  const src = path.join(PORT, dir, 'для печати', 'index.html');
  if (!fs.existsSync(src)) {
    console.log(`skip ${dir}: нет «для печати»/index.html — сначала python materialy/build/build_priglashenie.py`);
    return;
  }
  const page = await browser.newPage();
  try {
    await page.goto(pathToFileURL(src).href, { waitUntil: 'networkidle0', timeout: 60000 });
    try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch {}
    await sleep(300);
    await page.pdf({
      path: path.join(PORT, dir, 'для печати', 'priglashenie-A5.pdf'),
      width: '148mm', height: '210mm', printBackground: true, pageRanges: '1-2',
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    console.log(`OK  ${dir}  → для печати/priglashenie-A5.pdf`);
  } catch (e) {
    console.log(`ERR ${dir} (A5): ${e.message}`);
  } finally {
    await page.close();
  }
}

(async () => {
  let dirs = fs.readdirSync(PORT, { withFileTypes: true })
    .filter((d) => d.isDirectory() && /^\d\d /.test(d.name) && fs.existsSync(path.join(PORT, d.name, 'index.html')))
    .map((d) => d.name)
    .sort();
  if (ONLY) dirs = dirs.filter((d) => d.startsWith(String(ONLY).padStart(2, '0') + ' '));
  if (!dirs.length) { console.log('нечего собирать'); return; }

  const browser = await puppeteer.launch({
    executablePath: EDGE, headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars', '--force-color-profile=srgb'],
  });
  for (const dir of dirs) {
    await landingPack(browser, dir);
    await invitePdf(browser, dir);
  }
  await browser.close();
  console.log('\nГотово.');
})();
