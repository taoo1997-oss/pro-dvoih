/*
  Публикация постов-работ + закрепа в канал через Bot API.
  Запуск (из этой папки, один раз: npm install):
    node post.js --dry        — показать, что будет опубликовано, ничего не отправляя
    node post.js --pinned     — только закреп (пост + закрепить)
    node post.js --no-pinned  — только работы, без закрепа
    node post.js              — закреп + все работы
  Токен бота — в файле token.txt рядом (или переменная окружения BOT_TOKEN).
*/

const fs = require('fs');
const path = require('path');

const BOT_TOKEN = (process.env.BOT_TOKEN
  || fs.readFileSync(path.join(__dirname, 'token.txt'), 'utf8')).trim();
const CHANNEL = '@sait_vmesto_otkrytki';
const CONTACT = '@fuchiji_k'; // личный ник для «Заказать → ...»

// папка со скринами: ../скрины относительно этого файла
const SKR = path.join(__dirname, '..', 'скрины');
const PHOTOS = ['1-обложка.jpg', '2-приглашение.jpg', '5-галерея.jpg', '6-дресс-код.jpg'];
const DRY = process.argv.includes('--dry');
const API = (m) => `https://api.telegram.org/bot${BOT_TOKEN}/${m}`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// slug -> { pair, title, desc, tags }
const W = {
  '01-pyotr-i-anna-dusty-rose':   ['Пётр и Анна', 'Пыльная роза', 'Тёплый закатный кадр на всю обложку, имена каллиграфией по центру, мягкая пыльно-розовая палитра. Классика для загородной свадьбы в усадьбе.', '#пыльная_роза #классика'],
  '02-dmitriy-i-mariya-toskana':  ['Дмитрий и Мария', 'Тоскана', 'Выездная свадьба у моря: обложка-разворот, тёплый песочный и оливковый, секции в две колонки. Для тех, кто женится на юге или за границей.', '#тоскана #выездная'],
  '03-aleksandr-i-ekaterina-izumrud': ['Александр и Екатерина', 'Классика в изумруде', 'Глубокий изумруд и золото, капитель в заголовках, центрированная композиция. Строгий, вечерний — для торжества в ресторане.', '#изумруд #классика'],
  '04-nikita-i-olga-minimal':     ['Никита и Ольга', 'Минимал', 'Ничего лишнего: чёрная плашка с именами, крупные номера секций, много воздуха. Для пары, которая не любит рюши.', '#минимал'],
  '05-ivan-i-sofya-lavanda':      ['Иван и Софья', 'Прованс', 'Лаванда, тёплый лён, мягкий свет. Обложка-разворот, спокойная типографика. Для свадьбы на природе, в лавандовых тонах.', '#прованс #лаванда'],
  '06-roman-i-viktoriya-boho':    ['Роман и Виктория', 'Модерн-бохо', 'Терракота, сухоцветы, свободная сетка. Тёплый богемный стиль без цыганщины — для лофта, ангара или свадьбы в поле.', '#бохо #модерн'],
  '07-georgiy-i-alisa-more':      ['Георгий и Алиса', 'Морское побережье', 'Приглушённый синий и песок, имена на тёмной полосе поверх фото. Для свадьбы у воды — Калининград, Сочи, Крым.', '#море #побережье'],
  '08-artyom-i-darya-zima':       ['Артём и Дарья', 'Зимняя свадьба', 'Холодный свет, серебро, глубокий синий, обложка на весь экран. Для декабря–февраля — торжества в тепле с видом на снег.', '#зима'],
  '09-kirill-i-polina-botanika':  ['Кирилл и Полина', 'Ботаника', 'Живая зелень, эвкалипт, естественный свет, мозаичная галерея во всю ширину. Для свадьбы в оранжерее, ботсаду или на веранде.', '#ботаника #зелень'],
  '10-maksim-i-kseniya-rustik':   ['Максим и Ксения', 'Рустик', 'Тёплый закат, дерево, полевые цветы. Уютный деревенский стиль — для свадьбы на ферме, в шатре, на сеновале.', '#рустик'],
  '11-mihail-i-elena-ref1':       ['Михаил и Елена', 'Фотополоса с датой', 'Три фото в ряд и огромная дата поверх, акварельная зелень по углам. Современно и графично — сразу видно, когда и куда.', '#фотополоса #минимал'],
  '12-andrey-i-olga-ref2':        ['Андрей и Ольга', 'Save the date, ч/б', 'Полноэкранное чёрно-белое фото, тонкая линейная флора, серифная классика. Сдержанно и дорого на вид.', '#чб #savethedate'],
  '13-kirill-i-marina-ref3':      ['Кирилл и Марина', 'Крупный почерк', 'Имена гигантским живым почерком поверх ч/б фото, дата моноширинным шрифтом. Смелая обложка, которую запоминают.', '#почерк #чб'],
  '14-nikolay-i-darya-ref4':      ['Николай и Дарья', 'Кинообложка', 'Зациклённое немое ч/б видео фоном на первом экране, плавный зум. Максимальный эффект при открытии ссылки — видео вшито, грузится сразу.', '#видео #кинообложка'],
};

// порядок публикации: сильные вперёд
const ORDER = [
  '07-georgiy-i-alisa-more', '09-kirill-i-polina-botanika', '02-dmitriy-i-mariya-toskana',
  '14-nikolay-i-darya-ref4', '06-roman-i-viktoriya-boho', '12-andrey-i-olga-ref2',
  '01-pyotr-i-anna-dusty-rose', '10-maksim-i-kseniya-rustik', '05-ivan-i-sofya-lavanda',
  '03-aleksandr-i-ekaterina-izumrud', '13-kirill-i-marina-ref3', '11-mihail-i-elena-ref1',
  '08-artyom-i-darya-zima', '04-nikita-i-olga-minimal',
];

const OFFER = [
  `<b>Сайт-приглашение на свадьбу — под ключ за 3–4 дня</b>`,
  ``,
  `Делаю персональные сайты-приглашения вместо бумажных открыток. Один экран прокрутки, ваш дизайн, открывается по ссылке — отправляете гостям в WhatsApp или Telegram одним сообщением.`,
  ``,
  `<b>Цена — 3 500 ₽. Всё включено.</b>`,
  ``,
  `<b>Что вы получаете</b>`,
  `• Обложка с вашим фото и именами каллиграфией`,
  `• Дата, время, адрес с картой и маршрутом`,
  `• Обратный отсчёт до дня свадьбы`,
  `• Программа дня — тайминг для гостей`,
  `• Галерея ваших фотографий`,
  `• Блок «Дресс-код» с палитрой цветов`,
  `• Ответы на частые вопросы гостей`,
  `• Форма RSVP — гости подтверждают участие онлайн: кто придёт, +1, аллергии, пожелания`,
  `• Приватная страница со списком гостей — только для вас, ответы приходят в реальном времени`,
  `• Идеально открывается на телефоне`,
  `• Ссылка работает постоянно, без рекламы и чужих логотипов`,
  ``,
  `<b>Как это происходит</b>`,
  `1. Пишете мне в личку → ${CONTACT}`,
  `2. Присылаю анкету на 10–15 минут: имена, дата, место, ваша история, фото. Там же выбираете макет и палитру`,
  `3. Перевод 3 500 ₽ на карту — работа стартует сразу`,
  `4. Через 3–4 дня присылаю готовый сайт`,
  `5. 2 круга правок — меняем тексты, фото, цвета`,
  `6. Финальная ссылка. Отправляете гостям`,
  ``,
  `<b>Дополнительно</b>`,
  `• Срочно, за 24 часа — +1 500 ₽`,
  `• Ещё круг правок — +500 ₽`,
  `• Английская версия — +1 200 ₽`,
  ``,
  `Примеры работ — в постах ниже. Выбирайте стиль и пишите → ${CONTACT}`,
].join('\n');

async function postPinned() {
  if (DRY) {
    console.log(`\n=== ЗАКРЕП ===\n${OFFER.replace(/<\/?b>/g, '')}\n${'='.repeat(50)}`);
    return;
  }
  const j = await tg('sendMessage', jsonForm({
    chat_id: CHANNEL, text: OFFER, parse_mode: 'HTML', disable_web_page_preview: 'true',
  }));
  if (!j.ok) { console.log(`ERR закреп: ${j.error_code} ${j.description}`); return; }
  const mid = j.result.message_id;
  const pin = await tg('pinChatMessage', jsonForm({
    chat_id: CHANNEL, message_id: mid, disable_notification: 'true',
  }));
  console.log(`OK  закреп → https://t.me/${CHANNEL.slice(1)}/${mid}` +
    (pin.ok ? ' (закреплён)' : ` (закрепить не вышло: ${pin.description} — закрепи вручную)`));
}

function caption(slug) {
  const [pair, title, desc, tags] = W[slug];
  return (
    `<b>«${esc(title)}» · ${esc(pair)}</b>\n\n` +
    `${esc(desc)}\n\n` +
    `Внутри: отсчёт до свадьбы, программа дня, галерея, дресс-код, форма RSVP и приватный список гостей.\n\n` +
    `Под ключ — 3 500 ₽, 3–4 дня. Заказать → ${CONTACT}\n\n` +
    `${tags}`
  );
}

async function tg(method, form) {
  const res = await fetch(API(method), { method: 'POST', body: form });
  const j = await res.json();
  if (!j.ok && j.error_code === 429) {
    const wait = (j.parameters?.retry_after || 5) + 1;
    console.log(`  429, жду ${wait}с…`);
    await sleep(wait * 1000);
    return tg(method, form);
  }
  return j;
}

async function postWork(slug, idx) {
  const dir = path.join(SKR, slug);
  const pics = PHOTOS.filter((p) => fs.existsSync(path.join(dir, p)));
  if (!pics.length) { console.log(`SKIP ${slug}: нет картинок`); return; }

  const cap = caption(slug);
  if (DRY) {
    console.log(`\n[${idx + 1}/14] ${slug}  (${pics.length} фото)\n${cap}\n${'─'.repeat(50)}`);
    return;
  }

  const form = new FormData();
  form.append('chat_id', CHANNEL);
  const media = pics.map((p, i) => ({
    type: 'photo',
    media: `attach://p${i}`,
    ...(i === 0 ? { caption: cap, parse_mode: 'HTML' } : {}),
  }));
  form.append('media', JSON.stringify(media));
  pics.forEach((p, i) => {
    const buf = fs.readFileSync(path.join(dir, p));
    form.append(`p${i}`, new Blob([buf], { type: 'image/jpeg' }), p);
  });

  const j = await tg('sendMediaGroup', form);
  if (j.ok) {
    const mid = j.result[0].message_id;
    console.log(`OK  [${idx + 1}/14] ${slug} → https://t.me/${CHANNEL.slice(1)}/${mid}`);
  } else {
    console.log(`ERR [${idx + 1}/14] ${slug}: ${j.error_code} ${j.description}`);
  }
}

(async () => {
  if (!DRY && !/^@[\w]+$/.test(CONTACT)) {
    console.error(`CONTACT выглядит неправильно: ${CONTACT}`);
    process.exit(1);
  }
  if (!DRY) {
    const me = await (await fetch(API('getMe'))).json();
    if (!me.ok) { console.error('Плохой токен'); process.exit(1); }
    const test = await tg('sendMessage', jsonForm({ chat_id: CHANNEL, text: '.' }));
    if (!test.ok) { console.error(`Бот не может писать в канал: ${test.description}. Добавь бота админом с правом публикации.`); process.exit(1); }
    await tg('deleteMessage', jsonForm({ chat_id: CHANNEL, message_id: test.result.message_id }));
    console.log('Связь с каналом ок. Публикую…');
  }

  const ONLY_PINNED = process.argv.includes('--pinned');
  const SKIP_PINNED = process.argv.includes('--no-pinned');

  if (!SKIP_PINNED) {
    await postPinned();
    if (!DRY && !ONLY_PINNED) await sleep(4000);
  }
  if (ONLY_PINNED) { console.log('\nТолько закреп. Готово.'); return; }

  for (let i = 0; i < ORDER.length; i++) {
    await postWork(ORDER[i], i);
    if (!DRY && i < ORDER.length - 1) await sleep(6000);
  }
  console.log('\nГотово.');
})();

function jsonForm(obj) {
  const f = new FormData();
  for (const [k, v] of Object.entries(obj)) f.append(k, String(v));
  return f;
}
