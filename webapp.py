# Telegram Mini App — @Inglizfutbol
# main.py shu HTML_PAGE ni "/" va "/webapp" yo'llarida qaytaradi.

HTML_PAGE = """<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>ingliz futboli</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  background: #0e1830;
  color: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  -webkit-tap-highlight-color: transparent;
}
#app { padding-bottom: 76px; min-height: 100vh; }
header {
  padding: 14px 18px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 0.5px solid #223154;
  position: sticky;
  top: 0;
  background: #0e1830;
  z-index: 10;
}
header .logo { font-size: 19px; }
header .logo .light { font-weight: 400; color: #c7d1e8; }
header .logo .bold { font-weight: 700; color: #ffffff; }
.tab { display: none; }
.tab.active { display: block; }

/* ── Yangiliklar feed: to'liq balandlikdagi rasm fon + gradient ── */
.news-feed { display: flex; flex-direction: column; gap: 10px; padding: 14px 14px 4px; }

.news-card {
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  background-color: #182a45;
  background-size: cover;
  background-position: center;
}
.news-card.hero { height: 62vh; min-height: 420px; }
.news-card.small { height: 38vh; min-height: 250px; }

/* pastdan yuqoriga gradient — matn o'qiladi, rasm ko'p qismi ochiq qoladi */
.news-card::after {
  content: "";
  position: absolute;
  left: 0; right: 0; bottom: 0;
  height: 55%;
  background: linear-gradient(to top,
    rgba(9,15,30,0.97) 0%,
    rgba(9,15,30,0.88) 28%,
    rgba(9,15,30,0.45) 62%,
    rgba(9,15,30,0) 100%);
  pointer-events: none;
}

.news-card .badge {
  position: absolute;
  top: 12px;
  left: 14px;
  z-index: 2;
  font-size: 11px;
  letter-spacing: 0.06em;
  color: #201607;
  font-weight: 700;
  background: #f2c14e;
  padding: 4px 10px;
  border-radius: 20px;
}

.news-card .card-body {
  position: absolute;
  left: 0; right: 0; bottom: 0;
  z-index: 2;
  padding: 14px 16px 14px;
}

.news-card .card-title {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.3;
  margin-bottom: 6px;
  text-shadow: 0 1px 3px rgba(0,0,0,0.35);
}
.news-card.small .card-title { font-size: 15px; }

.news-card .card-desc {
  font-size: 13.5px;
  color: #d7e0f0;
  line-height: 1.4;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.news-card .card-desc.expanded {
  -webkit-line-clamp: unset;
  display: block;
  overflow: visible;
}
.news-card .card-desc .more-link {
  color: #f2c14e;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
}

.news-card .card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #9fb0c9;
}
.news-card .card-meta .tag {
  background: rgba(255,255,255,0.12);
  padding: 3px 9px;
  border-radius: 20px;
  font-weight: 600;
  color: #cdd8ea;
}

.empty, .loading { text-align: center; padding: 40px 20px; color: #5f6b8f; font-size: 14px; }
.day-picker { display: flex; gap: 8px; overflow-x: auto; padding: 14px 14px 4px; }
.day-btn {
  background: #243357; color: #8a93ac; font-size: 12.5px;
  padding: 7px 14px; border-radius: 8px; white-space: nowrap;
  border: none; flex-shrink: 0;
}
.day-btn.active { background: #f2c14e; color: #4a3400; font-weight: 600; }
.section-label {
  font-size: 12px; letter-spacing: 0.05em; color: #8a93ac;
  padding: 10px 14px 8px;
}
.match-card {
  background: #162542; border: 0.5px solid #223154; border-radius: 12px;
  padding: 14px; margin: 0 14px 10px; display: flex; align-items: center; justify-content: space-between;
}
.match-card .team { text-align: center; flex: 1; }
.match-card .crest { width: 28px; height: 28px; border-radius: 50%; background: #243357; margin: 0 auto 6px; background-size: cover; }
.match-card .team-name { font-size: 12.5px; color: #ffffff; }
.match-card .center { text-align: center; padding: 0 10px; }
.match-card .score { font-size: 22px; font-weight: 700; color: #ffffff; }
.match-card .time { font-size: 15px; color: #8a93ac; }
.match-card .live { display: flex; align-items: center; gap: 4px; justify-content: center; margin-top: 4px; }
.match-card .live .dot { width: 6px; height: 6px; border-radius: 50%; background: #e2515a; }
.match-card .live span { font-size: 11px; color: #e2515a; letter-spacing: 0.03em; }
.table-wrap { margin: 4px 14px 14px; background: #162542; border: 0.5px solid #223154; border-radius: 12px; overflow: hidden; }
.table-row { display: grid; grid-template-columns: 26px 1fr 30px 30px; gap: 8px; padding: 9px 12px; align-items: center; border-top: 0.5px solid #223154; }
.table-row.head { border-top: none; font-size: 11px; color: #5f6b8f; }
.table-row .pos { font-size: 13px; color: #ffffff; }
.table-row .pos.relegation { color: #e2515a; }
.table-row .team { font-size: 13.5px; color: #ffffff; }
.table-row .stat { font-size: 13px; color: #8a93ac; text-align: right; }
.table-row .pts { font-size: 13.5px; font-weight: 600; color: #ffffff; text-align: right; }
nav {
  position: fixed; bottom: 0; left: 0; right: 0;
  display: flex; background: #0e1830; border-top: 0.5px solid #223154;
  padding: 8px 0 max(8px, env(safe-area-inset-bottom));
}
nav button {
  flex: 1; background: transparent; border: none;
  display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 4px 0; color: #5f6b8f; font-size: 10.5px;
}
nav button.active { color: #f2c14e; }
</style>
</head>
<body>
<div id="app">
<header>
<div class="logo"><span class="light">ingliz</span><span class="bold">futboli</span></div>
</header>

<div id="tab-news" class="tab active">
<div id="news-content"><div class="loading">Yuklanmoqda...</div></div>
</div>

<div id="tab-matches" class="tab">
<div class="day-picker" id="day-picker"></div>
<div id="matches-content"><div class="loading">Yuklanmoqda...</div></div>
</div>

<div id="tab-table" class="tab">
<div id="table-content"><div class="loading">Yuklanmoqda...</div></div>
</div>
</div>

<nav>
<button class="active" data-tab="news" onclick="switchTab('news')">
<span style="font-size:20px;">📰</span>
<span>Yangiliklar</span>
</button>
<button data-tab="matches" onclick="switchTab('matches')">
<span style="font-size:20px;">⚽</span>
<span>O'yinlar</span>
</button>
<button data-tab="table" onclick="switchTab('table')">
<span style="font-size:20px;">📊</span>
<span>Jadval</span>
</button>
</nav>

<script>
const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) { tg.ready(); tg.expand(); }

const loaded = { news: false, matches: false, table: false };
let newsData = [];

function escapeHtml(str) {
  const div = document.createElement('div');
  div.innerText = str || '';
  return div.innerHTML;
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  if (!loaded[name]) {
    if (name === 'news') loadNews();
    if (name === 'matches') { initDayPicker(); loadMatches(currentDate()); }
    if (name === 'table') loadTable();
  }
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString('uz-UZ', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  } catch (e) { return ''; }
}

function splitTitle(raw) {
  const lines = (raw || '').split('\\n').map(l => l.trim()).filter(Boolean);
  const title = lines[0] || '';
  const rest = (raw || '').split('\\n').slice(1).join(' ').replace(/\\s+/g, ' ').trim();
  return { title, rest };
}

function descHtml(idx, rest, expanded) {
  if (!rest) return '';
  const link = expanded
    ? '<span class="more-link" onclick="toggleDesc(event,' + idx + ')">Kamroq</span>'
    : '<span class="more-link" onclick="toggleDesc(event,' + idx + ')">... Ko\\'proq</span>';
  return escapeHtml(rest) + ' ' + link;
}

function toggleDesc(evt, idx) {
  evt.stopPropagation();
  const el = document.getElementById('desc-' + idx);
  if (!el) return;
  const post = newsData[idx];
  const s = splitTitle(post.post_text || post.title || '');
  const expanded = el.classList.toggle('expanded');
  el.innerHTML = descHtml(idx, s.rest, expanded);
}

function newsCardHtml(post, idx, variant) {
  const s = splitTitle(post.post_text || post.title || '');
  const bg = post.image_url
    ? `background-image:url('${post.image_url}');`
    : 'background-image:linear-gradient(160deg,#24427c,#1d3a6e);';
  const badge = variant === 'hero' ? '<span class="badge">ASOSIY YANGILIK</span>' : '';
  const tag = variant === 'hero' ? 'Manba' : 'Yangilik';
  return `
    <div class="news-card ${variant}" style="${bg}">
      ${badge}
      <div class="card-body">
        <p class="card-title">${escapeHtml(s.title)}</p>
        <p class="card-desc" id="desc-${idx}">${descHtml(idx, s.rest, false)}</p>
        <div class="card-meta">
          <span>${formatDate(post.published_at)}</span>
          <span class="tag">${tag}</span>
        </div>
      </div>
    </div>
  `;
}

async function loadNews() {
  loaded.news = true;
  const el = document.getElementById('news-content');
  try {
    const res = await fetch('/api/posts');
    const posts = await res.json();
    if (!posts.length) {
      el.innerHTML = '<div class="empty">Hozircha yangiliklar yo\\'q.</div>';
      return;
    }
    newsData = posts;
    const [first, ...rest] = posts;
    let html = '<div class="news-feed">';
    html += newsCardHtml(first, 0, 'hero');
    html += rest.map((p, i) => newsCardHtml(p, i + 1, 'small')).join('');
    html += '</div>';
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = `<div class="empty">Xatolik yuz berdi.</div>`;
    loaded.news = false;
  }
}

function currentDate() {
  const active = document.querySelector('.day-btn.active');
  return active ? active.dataset.date : new Date().toISOString().slice(0, 10);
}

function initDayPicker() {
  const picker = document.getElementById('day-picker');
  const labels = ["Kecha", "Bugun", "Ertaga"];
  const today = new Date();
  let html = '';
  for (let i = -1; i <= 1; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    const dateStr = d.toISOString().slice(0, 10);
    const active = i === 0 ? 'active' : '';
    html += `<button class="day-btn ${active}" data-date="${dateStr}" onclick="selectDay(this)">${labels[i + 1]}</button>`;
  }
  picker.innerHTML = html;
}

function selectDay(btn) {
  document.querySelectorAll('.day-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadMatches(btn.dataset.date);
}

async function loadMatches(dateStr) {
  const el = document.getElementById('matches-content');
  el.innerHTML = '<div class="loading">Yuklanmoqda...</div>';
  try {
    const res = await fetch('/api/matches?date=' + dateStr);
    const matches = await res.json();
    if (matches === null) {
      el.innerHTML = '<div class="empty">O\\'yinlar hozircha ulanmagan.</div>';
      return;
    }
    if (!matches.length) {
      el.innerHTML = '<div class="empty">Bu sanada Premier-liga o\\'yinlari yo\\'q.</div>';
      return;
    }
    el.innerHTML = '<div class="section-label">PREMIER-LIGA</div>' + matches.map(m => {
      const isLive = m.status === 'jonli' || m.status === 'tanaffus';
      const isFinished = m.status === 'tugadi';
      let center;
      if (isLive || isFinished) {
        center = `
          <div class="score">${m.home_score ?? 0} &ndash; ${m.away_score ?? 0}</div>
          ${isLive ? `<div class="live"><span class="dot"></span><span>JONLI</span></div>` : ''}
        `;
      } else {
        const t = new Date(m.utc_date);
        center = `<div class="time">${t.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })}</div>`;
      }
      const homeCrest = m.home_crest ? `style="background-image:url('${m.home_crest}')"` : '';
      const awayCrest = m.away_crest ? `style="background-image:url('${m.away_crest}')"` : '';
      return `
        <div class="match-card">
          <div class="team"><div class="crest" ${homeCrest}></div><span class="team-name">${escapeHtml(m.home)}</span></div>
          <div class="center">${center}</div>
          <div class="team"><div class="crest" ${awayCrest}></div><span class="team-name">${escapeHtml(m.away)}</span></div>
        </div>
      `;
    }).join('');
  } catch (e) {
    el.innerHTML = '<div class="empty">Xatolik yuz berdi.</div>';
  }
}

async function loadTable() {
  loaded.table = true;
  const el = document.getElementById('table-content');
  try {
    const res = await fetch('/api/standings');
    const rows = await res.json();
    if (rows === null) {
      el.innerHTML = '<div class="empty">Jadval hozircha ulanmagan.</div>';
      return;
    }
    let html = `
      <div class="section-label">PREMIER-LIGA JADVALI</div>
      <div class="table-wrap">
        <div class="table-row head"><span>#</span><span>Klub</span><span style="text-align:right">O'</span><span style="text-align:right">O</span></div>
    `;
    html += rows.map(r => `
      <div class="table-row">
        <span class="pos ${r.position >= 18 ? 'relegation' : ''}">${r.position}</span>
        <span class="team">${escapeHtml(r.team)}</span>
        <span class="stat">${r.played}</span>
        <span class="pts">${r.points}</span>
      </div>
    `).join('');
    html += '</div>';
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = '<div class="empty">Xatolik yuz berdi.</div>';
    loaded.table = false;
  }
}

loadNews();
</script>
</body>
</html>
"""
