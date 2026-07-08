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

  /* ---- Yangiliklar feed: rasm-fon kartochkalar ---- */
  .feed { display: flex; flex-direction: column; gap: 14px; padding: 14px; }

  .post-card {
    position: relative;
    border-radius: 16px;
    overflow: hidden;
    min-height: 420px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    background: #162542 center / cover no-repeat;
  }
  .post-card.no-image { min-height: 260px; }
  .post-card::before {
    content: "";
    position: absolute; inset: 0;
    background: linear-gradient(180deg, rgba(14,24,48,0) 35%, rgba(14,24,48,0.55) 65%, rgba(14,24,48,0.96) 100%);
    pointer-events: none;
  }

  .post-actions {
    position: absolute;
    top: 14px; right: 12px;
    display: flex; flex-direction: column; gap: 10px;
    z-index: 3;
  }
  .post-actions button {
    width: 38px; height: 38px; border-radius: 50%;
    background: rgba(14,24,48,0.55); backdrop-filter: blur(4px);
    border: none; color: #fff; font-size: 17px;
    display: flex; align-items: center; justify-content: center;
  }
  .post-actions button.liked { color: #e2515a; }

  .post-body { position: relative; z-index: 2; padding: 18px; }
  .post-card.no-image .post-body { padding-top: 18px; }

  .post-tags {
    display: flex; gap: 6px; margin-bottom: 10px;
  }
  .post-tag {
    font-size: 11px; font-weight: 600; letter-spacing: 0.03em;
    color: #4a3400; background: #f2c14e;
    padding: 4px 10px; border-radius: 20px;
  }

  .post-title {
    font-size: 19px; font-weight: 700; line-height: 1.3;
    color: #ffffff; margin-bottom: 8px;
  }

  .post-snippet {
    font-size: 14px; line-height: 1.55; color: #d5dbea;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden; white-space: pre-line;
  }
  .post-snippet.expanded {
    -webkit-line-clamp: unset; overflow: visible;
  }

  .post-toggle {
    display: inline; color: #f2c14e; font-weight: 600; font-size: 14px;
    margin-left: 4px; cursor: pointer;
  }

  .post-footer {
    display: flex; align-items: center; gap: 8px;
    margin-top: 12px; font-size: 12px; color: #a9b2cc;
  }
  .post-footer .dot { color: #425079; }

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
  let currentPosts = [];
  const likedPosts = new Set();

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
    const rest = (raw || '').split('\\n').slice(1).join('\\n').trim();
    return { title, rest };
  }

  function togglePost(i) {
    const snippet = document.getElementById('snippet-' + i);
    const toggle = document.getElementById('toggle-' + i);
    const expanded = snippet.classList.toggle('expanded');
    toggle.innerText = expanded ? 'Kamroq' : 'Ko\\'proq';
  }

  function toggleLike(i, btn) {
    if (likedPosts.has(i)) {
      likedPosts.delete(i);
      btn.classList.remove('liked');
      btn.innerText = '🤍';
    } else {
      likedPosts.add(i);
      btn.classList.add('liked');
      btn.innerText = '❤️';
    }
  }

  function sharePost(i) {
    const p = currentPosts[i];
    if (!p) return;
    const s = splitTitle(p.post_text || p.title || '');
    const shareUrl = p.url || 'https://t.me/inglizfutboli_bot';
    if (tg && tg.openTelegramLink) {
      tg.openTelegramLink('https://t.me/share/url?url=' + encodeURIComponent(shareUrl) + '&text=' + encodeURIComponent(s.title));
    } else if (navigator.share) {
      navigator.share({ title: s.title, url: shareUrl });
    } else if (tg && tg.openLink) {
      tg.openLink(shareUrl);
    }
  }

  function openSourceFor(i) {
    const p = currentPosts[i];
    if (!p || !p.url) return;
    if (tg && tg.openLink) tg.openLink(p.url);
    else window.open(p.url, '_blank');
  }

  function renderPost(p, i, big) {
    const s = splitTitle(p.post_text || p.title || '');
    const bgStyle = p.image_url ? `style="background-image:url('${p.image_url}')"` : '';
    const noImageClass = p.image_url ? '' : ' no-image';
    return `
      <div class="post-card${noImageClass}" ${bgStyle}>
        <div class="post-actions">
          <button onclick="sharePost(${i})">↗</button>
          <button id="like-${i}" onclick="toggleLike(${i}, this)">🤍</button>
        </div>
        <div class="post-body">
          <div class="post-tags"><span class="post-tag">${big ? 'ASOSIY YANGILIK' : 'YANGILIK'}</span></div>
          <p class="post-title">${escapeHtml(s.title)}</p>
          <p class="post-snippet" id="snippet-${i}">${escapeHtml(s.rest || s.title)}</p>
          ${s.rest ? `<span class="post-toggle" id="toggle-${i}" onclick="togglePost(${i})">Ko'proq</span>` : ''}
          <div class="post-footer">
            <span>${formatDate(p.published_at)}</span>
            ${p.url ? `<span class="dot">&middot;</span><span class="post-toggle" onclick="openSourceFor(${i})">Manba</span>` : ''}
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
      currentPosts = posts;
      if (!posts.length) {
        el.innerHTML = '<div class="empty">Hozircha yangiliklar yo\\'q.</div>';
        return;
      }
      let html = '<div class="feed">';
      html += posts.map((p, i) => renderPost(p, i, i === 0)).join('');
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
