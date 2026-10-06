// Кадры «как это видит гость» для витрины: лендинг 01 на ширине телефона.
// Кладёт jpg в САЙТ/assets/phone/, build_sayt.py потом режет их в webp.
// Запуск (puppeteer-core живёт в ТЕЛЕГА/скрипты):
//   node САЙТ/snap_phone.js
const path = require('path');
const fs = require('fs');
const { pathToFileURL } = require('url');
const puppeteer = require(path.join(__dirname, '..', 'ТЕЛЕГА', 'скрипты', 'node_modules', 'puppeteer-core'));

const EDGE = process.env.BROWSER || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const DIR = path.join(__dirname, '..', 'ПОРТФОЛИО', '01 Пётр и Анна');
const OUT = path.join(__dirname, 'assets', 'phone');
const W = 390, H = 844, DPR = 2;

const KILL_ANIM = `
  *,*::before,*::after{animation-duration:0s!important;animation-delay:0s!important;transition:none!important}
  .reveal,[class*="reveal"]{opacity:1!important;transform:none!important;filter:none!important}
  html{scroll-behavior:auto!important}
`;

// Демо-ответы для кадра со списком гостей. Имена вымышленные, как и пара.
const DEMO = { list: [
  { name: 'Ольга Смирнова', guests: ['Денис Смирнов'] },
  { name: 'Тётя Лида', guests: [], note: 'Без мяса, пожалуйста' },
  { name: 'Игорь Ковалёв', guests: ['Наташа', 'Миша (5 лет)'] },
  { name: 'Вера Андреевна', guests: [] },
  { name: 'Саша Белов', guests: ['Катя Белова'], note: 'Будем к 15:00' },
]};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await puppeteer.launch({ executablePath: EDGE, headless: 'new',
    args: ['--hide-scrollbars', '--force-color-profile=srgb'] });
  const pg = await b.newPage();
  await pg.setViewport({ width: W, height: H, deviceScaleFactor: DPR, isMobile: true, hasTouch: true });
  await pg.goto(pathToFileURL(path.join(DIR, 'index.html')).href, { waitUntil: 'networkidle0', timeout: 90000 });
  await pg.addStyleTag({ content: KILL_ANIM });
  await pg.evaluate(() => document.fonts && document.fonts.ready);
  // прокрутка до конца, чтобы ленивые фото подгрузились
  await pg.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 500) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 80)); }
    scrollTo(0, 0);
  });
  await sleep(1200);

  const shot = async (name, sel, offset = 0) => {
    await pg.evaluate((s, o) => {
      const el = s && document.querySelector(s);
      scrollTo(0, el ? el.getBoundingClientRect().top + scrollY + o : 0);
    }, sel, offset);
    await sleep(500);
    await pg.screenshot({ path: path.join(OUT, name + '.jpg'), type: 'jpeg', quality: 84 });
    console.log('  ' + name);
  };
  await shot('cover', null);
  await shot('details', '#details');
  await shot('program', '#program');
  await shot('dress', '#dresscode');
  await shot('rsvp', '#rsvp');

  // длинная лента для телефона на первом экране: от обложки до начала галереи
  const stripH = await pg.evaluate(() => {
    const g = document.querySelector('#gallery');
    return Math.round(g.getBoundingClientRect().top + scrollY);
  });
  await pg.evaluate(() => scrollTo(0, 0));
  await sleep(300);
  await pg.screenshot({ path: path.join(OUT, 'strip.jpg'), type: 'jpeg', quality: 80,
    clip: { x: 0, y: 0, width: W, height: stripH }, captureBeyondViewport: true });
  console.log('  strip (' + stripH + 'px)');

  // список гостей с демо-ответами вместо настоящего бэкенда
  const p2 = await b.newPage();
  await p2.setViewport({ width: W, height: H, deviceScaleFactor: DPR, isMobile: true, hasTouch: true });
  await p2.setRequestInterception(true);
  p2.on('request', (r) => {
    if (r.url().includes('rsvp-backend')) {
      r.respond({ status: 200, contentType: 'application/json', headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify(DEMO) });
    } else r.continue();
  });
  await p2.goto(pathToFileURL(path.join(DIR, 'spisok-gostey.html')).href, { waitUntil: 'networkidle0', timeout: 90000 });
  await p2.addStyleTag({ content: KILL_ANIM });
  await sleep(800);
  await p2.screenshot({ path: path.join(OUT, 'list.jpg'), type: 'jpeg', quality: 84 });
  console.log('  list');

  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
