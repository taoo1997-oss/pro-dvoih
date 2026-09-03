const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

// путь к Chromium-браузеру: Edge по умолчанию, можно переопределить через BROWSER
const EDGE = process.env.BROWSER || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const ROOT = path.join(__dirname, '..', '..');       // корень проекта
const PORT = path.join(ROOT, 'portfolio');
const OUT = path.join(__dirname, '..', 'скрины');    // для телеграм/скрины

const KILL_ANIM = `
  *,*::before,*::after{animation-duration:0s!important;animation-delay:0s!important;transition:none!important}
  .reveal,[class*="reveal"]{opacity:1!important;transform:none!important;filter:none!important}
`;

// section id -> имя файла. intro (без id) обрабатывается отдельно.
const SECTIONS = [
  ['details', 'дата-и-отсчёт'],
  ['program', 'программа'],
  ['gallery', 'галерея'],
  ['dresscode', 'дресс-код'],
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      let y = 0;
      const timer = setInterval(() => {
        window.scrollBy(0, 400);
        y += 400;
        if (y >= document.body.scrollHeight + 1000) {
          clearInterval(timer);
          window.scrollTo(0, 0);
          resolve();
        }
      }, 60);
    });
  });
  await sleep(600);
}

(async () => {
  const dirs = fs.readdirSync(PORT)
    .filter((d) => /^\d\d-/.test(d) && fs.existsSync(path.join(PORT, d, 'index.html')))
    .sort();

  const browser = await puppeteer.launch({
    executablePath: EDGE,
    headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars', '--force-color-profile=srgb'],
  });

  const manifest = [];

  for (const slug of dirs) {
    const file = 'file:///' + path.join(PORT, slug, 'index.html').replace(/\\/g, '/');
    const outDir = path.join(OUT, slug);
    fs.rmSync(outDir, { recursive: true, force: true });
    fs.mkdirSync(outDir, { recursive: true });

    const page = await browser.newPage();
    const files = [];
    try {
      await page.setViewport({ width: 1512, height: 950, deviceScaleFactor: 2 });
      await page.goto(file, { waitUntil: 'networkidle0', timeout: 90000 });
      await page.addStyleTag({ content: KILL_ANIM });
      try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch {}
      await autoScroll(page);

      // 1 — обложка (первый экран)
      await page.screenshot({ path: path.join(outDir, '1-обложка.jpg'), type: 'jpeg', quality: 92 });
      files.push('1-обложка.jpg');

      // 2 — приглашение (секция «красивых слов»: без id, не hero)
      const intro = await page.evaluateHandle(() => {
        const secs = [...document.querySelectorAll('section')];
        return secs.find((s) => !s.id && !s.classList.contains('hero')) || null;
      });
      const introEl = intro.asElement();
      let n = 2;
      if (introEl) {
        await introEl.evaluate((e) => e.scrollIntoView({ block: 'center' }));
        await sleep(350);
        try {
          await introEl.screenshot({ path: path.join(outDir, '2-приглашение.jpg'), type: 'jpeg', quality: 90 });
          files.push('2-приглашение.jpg');
          n = 3;
        } catch {}
      }

      // 3..6 — секции по id
      for (const [id, name] of SECTIONS) {
        const el = await page.$('#' + id);
        if (!el) continue;
        await el.evaluate((e) => e.scrollIntoView({ block: 'center' }));
        await sleep(350);
        const fname = `${n}-${name}.jpg`;
        try {
          await el.screenshot({ path: path.join(outDir, fname), type: 'jpeg', quality: 90 });
          files.push(fname);
          n++;
        } catch {}
      }

      console.log(`OK  ${slug}  (${files.length} шт.: ${files.join(', ')})`);
      manifest.push({ slug, files });
    } catch (e) {
      console.log(`ERR ${slug}: ${e.message}`);
      manifest.push({ slug, error: e.message });
    } finally {
      await page.close();
    }
  }

  fs.writeFileSync(path.join(OUT, '_manifest.json'), JSON.stringify(manifest, null, 2));
  await browser.close();
  console.log('\nГотово: ' + OUT);
})();
