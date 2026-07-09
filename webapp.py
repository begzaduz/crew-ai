HTML_PAGE = """<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>ingliz futboli</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@100;200;300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    background: #0e1830;
    color: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    -webkit-tap-highlight-color: transparent;
    overflow-x: hidden;
  }
  #app { padding-bottom: 68px; min-height: 100vh; }
  
  header {
    padding: 14px 18px 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    border-bottom: 0.5px solid #223154;
    position: sticky;
    top: 0;
    background: #0e1830;
    z-index: 10;
  }
  header .logo-badge {
    width: 26px; height: 26px;
    border-radius: 50%;
    background: #162542;
    border: 0.5px solid #223154;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }
  header .logo-badge svg { width: 14px; height: 14px; color: #f2c14e; }
  header .logo { font-size: 22px; font-family: 'Poppins', sans-serif; letter-spacing: 0.01em; }
  header .logo .light { font-weight: 100; color: #ffffff; }
  header .logo .medium { font-weight: 600; color: #ffffff; }
  
  .tab { display: none; }
  .tab.active { display: block; }

  /* ---- Yangiliklar feed: ramkali kartalar, rasm chap tarafga tekis ---- */
  .feed {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px 14px;
  }

  .news-item {
    display: flex;
    align-items: stretch;
    height: 112px;
    background: #162542;
    border: 0.5px solid #223154;
    border-radius: 14px;
    overflow: hidden;
    cursor: pointer;
  }
  .news-item:active {
    opacity: 0.8;
  }

  .news-thumb {
    flex-shrink: 0;
    align-self: stretch;
    width: 112px;
    background: #243357 center / cover no-repeat;
  }
  .news-thumb.no-image {
    background: linear-gradient(135deg, #243357 0%, #0e1830 100%);
  }

  .news-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 6px;
    padding: 11px 14px;
  }

  .news-title {
    font-size: 13.5px;
    font-weight: 700;
    line-height: 1.26;
    color: #ffffff;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .news-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 10.5px;
    font-weight: 400;
    font-style: italic;
    letter-spacing: 0.01em;
    color: #ffffff;
    opacity: 0.55;
  }
  .news-meta .badge {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #243357 center / cover no-repeat;
    flex-shrink: 0;
  }

  /* ---- Yangilik tafsiloti (ichki sahifa) ---- */
  #news-detail { display: none; }
  #news-detail.active { display: block; }

  .detail-topbar {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    gap: 10px;
  }
  .detail-back {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #162542;
    border: 0.5px solid #223154;
    color: #ffffff;
    font-size: 17px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }
  .detail-back:active {
    opacity: 0.75;
  }

  .detail-image {
    margin: 0 14px 4px;
    height: 200px;
    border-radius: 16px;
    background: #243357 center / cover no-repeat;
  }
  .detail-image.no-image {
    background: linear-gradient(135deg, #243357 0%, #0e1830 100%);
  }

  .detail-body {
    padding: 16px 14px 24px;
  }
  .detail-meta {
    font-size: 11px;
    font-weight: 400;
    font-style: italic;
    letter-spacing: 0.01em;
    color: #ffffff;
    opacity: 0.55;
    margin-bottom: 8px;
  }
  .detail-title {
    font-size: 21px;
    font-weight: 800;
    line-height: 1.3;
    color: #ffffff;
    margin-bottom: 14px;
  }
  .detail-text {
    font-size: 14.5px;
    line-height: 1.65;
    color: #d5dbea;
    white-space: pre-line;
  }
  .detail-source {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 20px;
    color: #f2c14e;
    font-weight: 500;
    font-size: 12.5px;
    cursor: pointer;
  }
  .detail-source svg {
    width: 15px;
    height: 15px;
    flex-shrink: 0;
  }
  .detail-source:active {
    opacity: 0.7;
  }

  /* ---- Boshqa sahifa elementlari stabil saqlandi ---- */
  .empty, .loading { text-align: center; padding: 40px 20px; color: #5f6b8f; font-size: 14px; }
  .day-picker { display: flex; gap: 8px; overflow-x: auto; padding: 14px 14px 4px; }
  .day-btn {
    background: #243357; color: #8a93ac; font-size: 12.5px;
    padding: 7px 14px; border-radius: 8px; white-space: nowrap;
    border: none; flex-shrink: 0;
  }
  .day-btn.active { background: #f2c14e; color: #4a3400; font-weight: 600; }
  .section-label { font-size: 12px; letter-spacing: 0.05em; color: #8a93ac; padding: 10px 14px 8px; }
  
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
    padding: 10px 0 max(10px, env(safe-area-inset-bottom));
    z-index: 50;
  }
  nav button {
    flex: 1; background: transparent; border: none;
    display: flex; align-items: center; justify-content: center;
    padding: 6px 0; color: #5f6b8f;
    cursor: pointer;
    position: relative;
  }
  nav button svg {
    width: 25px; height: 25px;
    transition: transform 0.15s ease;
  }
  nav button.active { color: #f2c14e; }
  nav button.active svg { transform: scale(1.1); }
  nav button.active::before {
    content: "";
    position: absolute;
    top: -10px;
    left: 50%;
    transform: translateX(-50%);
    width: 22px;
    height: 3px;
    border-radius: 3px;
    background: #f2c14e;
  }

  /* ---- Kirish animatsiyasi (splash) ---- */
  #splash {
    position: fixed; inset: 0; z-index: 1000;
    background: #0e1830;
    display: flex; align-items: center; justify-content: center;
    animation: splashHide 0.6s ease forwards;
    animation-delay: 3.4s;
  }
  .splash-wrap {
    display: flex; flex-direction: column; align-items: center;
  }
  .splash-logo {
    font-size: 26px; font-family: 'Poppins', sans-serif; letter-spacing: 0.01em;
    display: flex;
  }
  .splash-logo .light {
    font-weight: 100; color: #ffffff;
    opacity: 0; transform: translateX(-22px);
    animation: splashIn 0.55s ease forwards;
    animation-delay: 0.15s;
  }
  .splash-logo .medium {
    font-weight: 600; color: #ffffff;
    opacity: 0; transform: translateX(22px);
    animation: splashIn 0.55s ease forwards;
    animation-delay: 0.35s;
  }
  @keyframes splashIn {
    to { opacity: 1; transform: translateX(0); }
  }
  @keyframes splashHide {
    to { opacity: 0; visibility: hidden; pointer-events: none; }
  }
</style>
</head>
<body>
<div id="splash">
  <div class="splash-wrap">
    <div class="splash-logo"><span class="light">ingliz</span><span class="medium">futboli</span></div>
  </div>
</div>
<div id="app">
  <header>
    <div class="logo-badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8.5"/><path d="M12 8.2l2.7 1.9-1 3.2h-3.4l-1-3.2z"/><path d="M12 8.2V4.7M9.3 10.1L6 7.8M14.7 10.1L18 7.8M9.9 13.6l-2.7 3M14.1 13.6l2.7 3"/></svg></div>
    <div class="logo"><span class="light">ingliz</span><span class="medium">futboli</span></div>
  </header>
  <div id="tab-news" class="tab active">
    <div id="news-list"><div class="loading">Yuklanmoqda...</div></div>
    <div id="news-detail"></div>
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
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="4.5" width="17" height="15" rx="2.5"/><line x1="7.5" y1="9" x2="16.5" y2="9"/><line x1="7.5" y1="12.5" x2="16.5" y2="12.5"/><line x1="7.5" y1="16" x2="12.5" y2="16"/></svg>
  </button>
  <button data-tab="matches" onclick="switchTab('matches')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8.5"/><path d="M12 8.2l2.7 1.9-1 3.2h-3.4l-1-3.2z"/><path d="M12 8.2V4.7M9.3 10.1L6 7.8M14.7 10.1L18 7.8M9.9 13.6l-2.7 3M14.1 13.6l2.7 3"/></svg>
  </button>
  <button data-tab="table" onclick="switchTab('table')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="4.5" width="17" height="15" rx="2"/><line x1="3.5" y1="9.7" x2="20.5" y2="9.7"/><line x1="3.5" y1="14.3" x2="20.5" y2="14.3"/><line x1="9.3" y1="4.5" x2="9.3" y2="19.5"/></svg>
  </button>
</nav>
<script>
  const tg = window.Telegram ? window.Telegram.WebApp : null;
  if (tg) { tg.ready(); tg.expand(); }

  setTimeout(() => {
    const splash = document.getElementById('splash');
    if (splash) splash.remove();
  }, 4050);

  const loaded = { news: false, matches: false, table: false };
  let currentPosts = [];

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.innerText = str || '';
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return (str || '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function switchTab(name) {
    if (name !== 'news' && document.getElementById('news-detail').classList.contains('active')) {
      closePost();
    }
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
      const then = new Date(iso).getTime();
      const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000));
      if (diffSec < 60) return 'hozirgina';
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return diffMin + ' daqiqa oldin';
      const diffHour = Math.floor(diffMin / 60);
      if (diffHour < 24) return diffHour + ' soat oldin';
      const diffDay = Math.floor(diffHour / 24);
      return diffDay + ' kun oldin';
    } catch (e) { return ''; }
  }

  function stripEmoji(str) {
    return (str || '')
      .replace(/\\p{Extended_Pictographic}/gu, '')
      .replace(/[\\u{1F1E6}-\\u{1F1FF}]/gu, '')
      .replace(/[\\u200D\\uFE0F]/g, '')
      .replace(/\\s{2,}/g, ' ')
      .trim();
  }

  function splitTitle(raw) {
    const lines = (raw || '').split('\\n').map(l => l.trim()).filter(Boolean);
    const title = lines[0] || '';
    const rest = (raw || '').split('\\n').slice(1).join('\\n').trim();
    return { title, rest };
  }

  function stripChannelTag(text) {
    return (text || '')
      .split('\\n')
      .filter(line => !/^@[\\w\\d_]+$/.test(line.trim()))
      .join('\\n')
      .replace(/\\n{3,}/g, '\\n\\n')
      .trim();
  }

  function openSourceFor(i) {
    const p = currentPosts[i];
    if (!p || !p.url) return;
    if (tg && tg.openLink) tg.openLink(p.url);
    else window.open(p.url, '_blank');
  }

  function renderPost(p, i) {
    const s = splitTitle(p.post_text || p.title || '');
    const bgStyle = p.image_url ? `style="background-image:url('${escapeAttr(p.image_url)}')"` : '';
    const noImageClass = p.image_url ? '' : ' no-image';
    return `
      <div class="news-item" onclick="openPost(${i})">
        <div class="news-thumb${noImageClass}" ${bgStyle}></div>
        <div class="news-content">
          <p class="news-title">${escapeHtml(stripEmoji(s.title))}</p>
          <div class="news-meta">
            <span>${formatDate(p.published_at)}</span>
          </div>
        </div>
      </div>
    `;
  }

  function sourceName(url) {
    try {
      const host = new URL(url).hostname.replace(/^www\\./, '');
      return host;
    } catch (e) {
      return 'Manba';
    }
  }

  function openPost(i) {
    const p = currentPosts[i];
    if (!p) return;
    const s = splitTitle(p.post_text || p.title || '');
    const bgStyle = p.image_url ? `style="background-image:url('${escapeAttr(p.image_url)}')"` : '';
    const noImageClass = p.image_url ? '' : ' no-image';
    const detail = document.getElementById('news-detail');
    detail.innerHTML = `
      <div class="detail-topbar">
        <button class="detail-back" onclick="closePost()">←</button>
      </div>
      <div class="detail-image${noImageClass}" ${bgStyle}></div>
      <div class="detail-body">
        <div class="detail-meta">${formatDate(p.published_at)}</div>
        <h1 class="detail-title">${escapeHtml(stripEmoji(s.title))}</h1>
        <p class="detail-text">${escapeHtml(stripChannelTag(s.rest || s.title))}</p>
        ${p.url ? `<div class="detail-source" onclick="openSourceFor(${i})"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="4.5" width="17" height="15" rx="2"/><line x1="7.5" y1="9" x2="16.5" y2="9"/><line x1="7.5" y1="12.5" x2="16.5" y2="12.5"/><line x1="7.5" y1="16" x2="12.5" y2="16"/></svg><span>${escapeHtml(sourceName(p.url))}</span></div>` : ''}
      </div>
    `;
    document.getElementById('news-list').style.display = 'none';
    detail.classList.add('active');
    window.scrollTo(0, 0);
  }

  function closePost() {
    document.getElementById('news-detail').classList.remove('active');
    document.getElementById('news-list').style.display = '';
  }

  async function loadNews() {
    loaded.news = true;
    const el = document.getElementById('news-list');
    try {
      const res = await fetch('/api/posts');
      const posts = await res.json();
      currentPosts = posts;
      if (!posts.length) {
        el.innerHTML = '<div class="empty">Hozircha yangiliklar yo\\'q.</div>';
        return;
      }
      let html = '<div class="feed">';
      html += posts.map((p, i) => renderPost(p, i)).join('');
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
