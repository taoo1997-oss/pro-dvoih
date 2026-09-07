/* RSVP-бэкенд свадебных лендингов.
   Один Worker на все свадьбы, разделение по полю wedding (slug пары).

   POST /rsvp   {wedding, name, guests:[], note}  -> {ok:true}
   GET  /rsvp?wedding=<slug>                       -> {list:[...], count, people}

   Данные полупубличные (кто знает ссылку — тот и видит), поэтому CORS открыт
   для всех: лендинги живут на разных доменах клиентов. */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type'
};

// Пределы — защита от мусора и раздувания базы.
const LIMITS = {
  wedding: 80,
  name: 120,
  note: 500,
  guestName: 120,
  guestsPerEntry: 20,
  bodyBytes: 10 * 1024,
  entriesPerWedding: 500
};

function json(data, status) {
  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers: Object.assign({ 'Content-Type': 'application/json' }, CORS_HEADERS)
  });
}

function err(status, error) {
  return json({ error: error }, status);
}

// slug пары: латиница/цифры/дефис/подчёркивание, как его отдаёт build.py.
function cleanWedding(v) {
  const s = String(v || '').trim().toLowerCase();
  if (!s || s.length > LIMITS.wedding) return null;
  if (!/^[a-z0-9_-]+$/.test(s)) return null;
  return s;
}

function cleanStr(v, max) {
  return String(v == null ? '' : v).replace(/\s+/g, ' ').trim().slice(0, max);
}

async function handlePost(request, env) {
  const raw = await request.text();
  if (raw.length > LIMITS.bodyBytes) return err(413, 'Слишком длинная заявка');

  let body;
  try { body = JSON.parse(raw); } catch (e) { return err(400, 'Некорректный JSON'); }

  const wedding = cleanWedding(body.wedding);
  if (!wedding) return err(400, 'Не указана свадьба');

  const name = cleanStr(body.name, LIMITS.name);
  if (!name) return err(400, 'Не указано имя');

  const note = cleanStr(body.note, LIMITS.note);

  let guests = Array.isArray(body.guests) ? body.guests : [];
  guests = guests
    .map(function (g) { return cleanStr(g, LIMITS.guestName); })
    .filter(Boolean)
    .slice(0, LIMITS.guestsPerEntry);

  const count = await env.DB.prepare('SELECT COUNT(*) AS n FROM rsvp WHERE wedding = ?')
    .bind(wedding).first();
  if (count && count.n >= LIMITS.entriesPerWedding) {
    return err(429, 'Достигнут предел заявок для этой свадьбы');
  }

  const ip = request.headers.get('CF-Connecting-IP') || '';
  await env.DB.prepare(
    'INSERT INTO rsvp (wedding, name, guests, note, ts, ip) VALUES (?,?,?,?,?,?)'
  ).bind(wedding, name, JSON.stringify(guests), note, Date.now(), ip).run();

  return json({ ok: true });
}

async function handleGet(request, env) {
  const url = new URL(request.url);
  const wedding = cleanWedding(url.searchParams.get('wedding'));
  if (!wedding) return err(400, 'Не указана свадьба');

  const res = await env.DB.prepare(
    'SELECT name, guests, note, ts FROM rsvp WHERE wedding = ? ORDER BY ts ASC'
  ).bind(wedding).all();

  const list = (res.results || []).map(function (row) {
    let g = [];
    try { g = JSON.parse(row.guests); } catch (e) { g = []; }
    return { name: row.name, guests: g, note: row.note || '', ts: row.ts };
  });

  let people = 0;
  list.forEach(function (e) { people += 1 + (e.guests ? e.guests.length : 0); });

  return json({ list: list, count: list.length, people: people });
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const path = new URL(request.url).pathname;
    try {
      if (path === '/rsvp' && request.method === 'POST') return await handlePost(request, env);
      if (path === '/rsvp' && request.method === 'GET') return await handleGet(request, env);
      return err(404, 'Не найдено');
    } catch (e) {
      return err(500, 'Внутренняя ошибка: ' + (e && e.message ? e.message : String(e)));
    }
  }
};
