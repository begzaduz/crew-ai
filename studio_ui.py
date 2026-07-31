STUDIO_HTML = """<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Studio Lab</title>
<style>
  :root{
    --navy:#0e1830; --navy-deep:#0a1224; --surface:#162542; --surface-2:#1b2c4e;
    --border:#223154; --gold:#f2c14e; --text:#ffffff; --text-dim:#a8b0c6; --text-faint:#5f6b8f;
    --green:#4fb77e; --red:#e2515a; --blue:#5b8cff; --radius:12px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body {
    background: var(--navy); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    overflow: hidden;
  }
  ::-webkit-scrollbar{ width:8px; height:8px; }
  ::-webkit-scrollbar-thumb{ background:var(--border); border-radius:8px; }

  .shell{ display:grid; grid-template-columns: 220px 1fr 320px; height:100vh; }
  @media (max-width: 900px){ .shell{ grid-template-columns: 1fr; } .sidebar, .rightpanel{ display:none; } }

  /* Sidebar */
  .sidebar{ background:var(--navy-deep); border-right:1px solid var(--border); overflow-y:auto; display:flex; flex-direction:column; }
  .brand{ display:flex; align-items:center; gap:10px; padding:20px 18px 16px; border-bottom:1px solid var(--border); }
  .brand-mark{ width:28px; height:28px; border-radius:8px; background:linear-gradient(135deg,var(--gold),#c99a2e); display:flex; align-items:center; justify-content:center; font-weight:700; font-size:13px; color:var(--navy-deep); flex-shrink:0; }
  .brand-name{ font-size:15px; font-weight:600; }
  .brand-name span{ font-weight:200; }
  nav.groups{ padding:12px 8px; flex:1; }
  .group{ margin-bottom:16px; }
  .group-label{ font-size:10px; letter-spacing:.06em; text-transform:uppercase; color:var(--text-faint); font-weight:600; padding:6px 10px 6px; }
  .nav-item{ display:flex; align-items:center; gap:9px; padding:8px 10px; margin:1px 0; border-radius:8px; font-size:13px; color:var(--text-dim); cursor:pointer; border-left:2px solid transparent; }
  .nav-item:hover{ background:var(--surface); color:var(--text); }
  .nav-item.active{ background:var(--surface); color:var(--gold); border-left-color:var(--gold); }
  .nav-item .count{ margin-left:auto; font-size:10.5px; color:var(--text-faint); background:var(--surface-2); padding:1px 7px; border-radius:20px; }
  .nav-item.active .count{ color:var(--gold); }
  .sidebar-foot{ padding:12px 18px; border-top:1px solid var(--border); font-size:11px; color:var(--text-faint); display:flex; align-items:center; gap:8px; }
  .status-dot{ width:7px; height:7px; border-radius:50%; background:var(--green); flex-shrink:0; }

  /* Main */
  main{ overflow-y:auto; padding:24px 28px 60px; }
  .view{ display:none; }
  .view.active{ display:block; }
  .page-head{ margin-bottom:20px; }
  .page-head h1{ font-size:19px; font-weight:700; }
  .page-head p{ color:var(--text-faint); font-size:12.5px; margin-top:3px; }

  .kpi-row{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px; }
  .kpi-card{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:14px 16px; }
  .kpi-card .label{ font-size:11px; color:var(--text-faint); }
  .kpi-card .value{ font-size:24px; font-weight:700; margin-top:6px; }

  .lifecycle-card{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:20px 22px; margin-bottom:20px; }
  .lifecycle-card h3{ font-size:12.5px; color:var(--text-dim); font-weight:600; margin-bottom:16px; letter-spacing:.02em; }
  .lifecycle{ display:flex; align-items:center; }
  .l-stage{ flex:1; text-align:center; }
  .l-stage .ring{ width:50px; height:50px; border-radius:50%; border:2px solid var(--border); display:flex; align-items:center; justify-content:center; margin:0 auto 8px; font-size:16px; font-weight:600; background:var(--surface); }
  .l-stage.pending .ring{ border-color:var(--gold); color:var(--gold); }
  .l-stage.done .ring{ border-color:var(--green); color:var(--green); }
  .l-stage.rej .ring{ border-color:var(--red); color:var(--red); }
  .l-stage .name{ font-size:11.5px; color:var(--text-dim); font-weight:500; }
  .l-connector{ flex:0 0 auto; width:50px; height:2px; background:var(--border); margin-top:-24px; }

  .panel{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:16px 18px; }
  .panel h3{ font-size:12.5px; color:var(--text-dim); font-weight:600; margin-bottom:12px; }
  .feed-item{ display:flex; gap:9px; padding:8px 0; border-bottom:1px solid var(--border); font-size:12px; align-items:flex-start; }
  .feed-item:last-child{ border-bottom:none; }
  .feed-dot{ width:6px; height:6px; border-radius:50%; margin-top:5px; flex-shrink:0; }
  .feed-dot.draft{ background:var(--gold); }
  .feed-dot.published{ background:var(--green); }
  .feed-dot.rejected{ background:var(--red); }
  .feed-text{ color:var(--text-dim); }
  .feed-text b{ color:var(--text); }
  .feed-time{ margin-left:auto; color:var(--text-faint); font-size:10.5px; white-space:nowrap; }

  .queue-grid{ display:grid; grid-template-columns:repeat(auto-fill, minmax(280px,1fr)); gap:12px; }
  .q-card{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:14px 16px; cursor:pointer; }
  .q-card:hover{ border-color:var(--gold); }
  .q-card.selected{ border-color:var(--gold); box-shadow:0 0 0 1px var(--gold) inset; }
  .q-title{ font-size:13.5px; font-weight:600; line-height:1.35; margin-bottom:8px; }
  .q-meta{ display:flex; gap:8px; font-size:10.5px; color:var(--text-faint); margin-bottom:10px; flex-wrap:wrap; }
  .status-chip{ display:inline-block; font-size:10px; padding:2px 8px; border-radius:20px; font-weight:600; }
  .status-chip.draft{ background:rgba(242,193,78,.12); color:var(--gold); }
  .status-chip.published{ background:rgba(79,183,126,.12); color:var(--green); }
  .status-chip.rejected{ background:rgba(226,81,90,.12); color:var(--red); }
  .empty{ color:var(--text-faint); font-size:13px; padding:20px 4px; }

  .btn{ font-size:11.5px; font-weight:600; border:none; border-radius:7px; padding:6px 11px; cursor:pointer; }
  .btn:disabled{ opacity:.5; cursor:default; }
  .btn-gold{ background:var(--gold); color:var(--navy-deep); }
  .btn-ghost{ background:var(--surface-2); color:var(--text-dim); border:1px solid var(--border); }
  .btn-danger{ background:rgba(226,81,90,.12); color:var(--red); border:1px solid rgba(226,81,90,.3); }

  .studio-card{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:20px 22px; max-width:640px; }
  .studio-card .subtitle{ color:var(--text-faint); font-size:12.5px; margin-bottom:16px; }
  .input-tabs{ display:flex; gap:6px; margin-bottom:12px; }
  .input-tab{ font-size:11.5px; padding:6px 12px; border-radius:7px; background:var(--surface-2); color:var(--text-dim); border:1px solid var(--border); }
  .input-tab.active{ background:var(--gold); color:var(--navy-deep); font-weight:600; border-color:var(--gold); }
  .input-tab.disabled{ opacity:.4; cursor:default; }
  textarea, input[type=text]{ width:100%; background:var(--navy-deep); border:1px solid var(--border); border-radius:8px; color:var(--text); font-size:13px; padding:10px 12px; font-family:inherit; }
  textarea{ min-height:110px; resize:vertical; line-height:1.5; }
  textarea:focus, input[type=text]:focus{ outline:none; border-color:var(--gold); }
  .studio-actions{ display:flex; justify-content:space-between; align-items:center; margin-top:14px; }
  .ai-steps{ display:flex; gap:12px; flex-wrap:wrap; font-size:10.5px; color:var(--text-faint); }
  .ai-steps span::before{ content:'○ '; color:var(--gold); }

  .source-row{ display:flex; align-items:center; gap:12px; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:12px 16px; margin-bottom:9px; }
  .source-row .s-url{ flex:1; font-size:12px; color:var(--text-dim); word-break:break-all; }
  .source-row .s-url.inactive{ opacity:.4; text-decoration:line-through; }
  .add-source-row{ display:flex; gap:8px; margin-top:12px; }
  .add-source-row input{ flex:1; }

  .kb-card{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:16px 18px; margin-bottom:14px; }
  .kb-card summary{ cursor:pointer; font-size:13px; font-weight:600; list-style:none; display:flex; align-items:center; justify-content:space-between; }
  .kb-card summary::-webkit-details-marker{ display:none; }
  .kb-card summary .count{ color:var(--text-faint); font-weight:400; font-size:11.5px; }
  .kb-card[open] summary{ margin-bottom:12px; }
  .term-row{ display:grid; grid-template-columns:1fr 1fr auto; gap:8px; margin-bottom:6px; }
  .field-label{ font-size:10.5px; color:var(--text-faint); margin-bottom:4px; display:block; }

  /* Right panel */
  .rightpanel{ background:var(--navy-deep); border-left:1px solid var(--border); padding:20px 18px; overflow-y:auto; }
  .rp-empty{ height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; color:var(--text-faint); font-size:12.5px; gap:10px; }
  .rp-title{ font-size:14.5px; font-weight:700; margin-bottom:3px; }
  .rp-sub{ font-size:11px; color:var(--text-faint); margin-bottom:16px; }
  .rp-section{ margin-bottom:16px; }
  .rp-label{ font-size:10px; letter-spacing:.05em; text-transform:uppercase; color:var(--text-faint); font-weight:600; margin-bottom:7px; }
  .rp-img{ width:100%; height:110px; border-radius:9px; background:var(--surface) center/cover no-repeat; border:1px solid var(--border); display:flex; align-items:center; justify-content:center; color:var(--text-faint); font-size:11px; }
  .rp-actions{ display:flex; gap:8px; margin-top:16px; }
  .rp-actions .btn{ flex:1; padding:9px 0; text-align:center; }
  .rp-link{ color:var(--gold); font-size:11.5px; text-decoration:none; }

  .toast{ position:fixed; bottom:20px; left:50%; transform:translateX(-50%); background:var(--surface-2); border:1px solid var(--border); color:#fff; padding:10px 18px; border-radius:8px; font-size:13px; opacity:0; transition:opacity .2s; pointer-events:none; z-index:100; }
  .toast.show{ opacity:1; }
</style>
</head>
<body>
<div class="shell">

  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">SL</div>
      <div class="brand-name"><span>Studio</span> Lab</div>
    </div>
    <nav class="groups">
      <div class="group">
        <div class="nav-item active" data-view="dashboard" onclick="switchView('dashboard')">Dashboard</div>
      </div>
      <div class="group">
        <div class="group-label">Content</div>
        <div class="nav-item" data-view="queue" onclick="switchView('queue')">Review Queue <span class="count" id="nav-count-draft">0</span></div>
        <div class="nav-item" data-view="published" onclick="switchView('published')">Published <span class="count" id="nav-count-published">0</span></div>
        <div class="nav-item" data-view="rejected" onclick="switchView('rejected')">Rejected <span class="count" id="nav-count-rejected">0</span></div>
      </div>
      <div class="group">
        <div class="group-label">Sources</div>
        <div class="nav-item" data-view="sources" onclick="switchView('sources')">RSS <span class="count" id="nav-count-sources">0</span></div>
      </div>
      <div class="group">
        <div class="group-label">Knowledge Base</div>
        <div class="nav-item" data-view="kb" onclick="switchView('kb')">Terminology &amp; Rules</div>
      </div>
      <div class="group">
        <div class="group-label">Create</div>
        <div class="nav-item" data-view="studio" onclick="switchView('studio')">AI Content Studio</div>
      </div>
    </nav>
    <div class="sidebar-foot"><span class="status-dot"></span> Ingliz Futboli loyihasi</div>
  </aside>

  <main>

    <!-- DASHBOARD -->
    <div class="view active" id="view-dashboard">
      <div class="page-head"><h1>Dashboard</h1><p>AI-Powered Creative Operations — Ingliz Futboli loyihasi</p></div>

      <div class="kpi-row">
        <div class="kpi-card"><div class="label">Bugungi nashrlar</div><div class="value" id="kpi-today">—</div></div>
        <div class="kpi-card"><div class="label">Tasdiqlash kutmoqda</div><div class="value" id="kpi-pending">—</div></div>
        <div class="kpi-card"><div class="label">Jami nashr etilgan</div><div class="value" id="kpi-published">—</div></div>
        <div class="kpi-card"><div class="label">Faol manbalar</div><div class="value" id="kpi-sources">—</div></div>
      </div>

      <div class="lifecycle-card">
        <h3>KONTENT HAYOT SIKLI</h3>
        <div class="lifecycle">
          <div class="l-stage pending"><div class="ring" id="lc-draft">0</div><div class="name">Review Queue</div></div>
          <div class="l-connector"></div>
          <div class="l-stage done"><div class="ring" id="lc-published">0</div><div class="name">Published</div></div>
          <div class="l-connector"></div>
          <div class="l-stage rej"><div class="ring" id="lc-rejected">0</div><div class="name">Rejected</div></div>
        </div>
      </div>

      <div class="panel">
        <h3>SO'NGGI FAOLIYAT</h3>
        <div id="activity-feed"><div class="empty">Yuklanmoqda...</div></div>
      </div>
    </div>

    <!-- REVIEW QUEUE -->
    <div class="view" id="view-queue">
      <div class="page-head"><h1>Review Queue</h1><p>Tasdiqlashni kutayotgan postlar</p></div>
      <div class="queue-grid" id="queue-draft"><div class="empty">Yuklanmoqda...</div></div>
    </div>

    <!-- PUBLISHED -->
    <div class="view" id="view-published">
      <div class="page-head"><h1>Published</h1><p>@Inglizfutbol kanaliga chiqqan postlar</p></div>
      <div class="queue-grid" id="queue-published"><div class="empty">Yuklanmoqda...</div></div>
    </div>

    <!-- REJECTED -->
    <div class="view" id="view-rejected">
      <div class="page-head"><h1>Rejected</h1><p>Rad etilgan postlar</p></div>
      <div class="queue-grid" id="queue-rejected"><div class="empty">Yuklanmoqda...</div></div>
    </div>

    <!-- AI CONTENT STUDIO -->
    <div class="view" id="view-studio">
      <div class="page-head"><h1>AI Content Studio</h1><p>Paste text, article, quote or URL. Studio Lab will transform it into a publication-ready post.</p></div>
      <div class="studio-card">
        <div class="input-tabs">
          <div class="input-tab active">Raw Text</div>
          <div class="input-tab disabled" title="Tez orada">Article URL</div>
          <div class="input-tab disabled" title="Tez orada">File Upload</div>
        </div>
        <div class="subtitle">Har qanday tildagi xom matn — AI tarjima qilib, formatga soladi</div>
        <textarea id="manual-text" placeholder="Matnni shu yerga joylang..."></textarea>
        <div class="studio-actions">
          <div class="ai-steps"><span>Tarjima</span><span>Faktlarni ajratish</span><span>Kanal formati</span><span>Sarlavha</span><span>Emoji</span></div>
          <button class="btn btn-gold" id="manual-submit-btn" onclick="submitManual()">Generate Draft</button>
        </div>
      </div>
    </div>

    <!-- SOURCES -->
    <div class="view" id="view-sources">
      <div class="page-head"><h1>Sources · RSS</h1><p>Studio Lab AI shu manbalardan yangiliklarni oladi</p></div>
      <div id="sources-list"><div class="empty">Yuklanmoqda...</div></div>
      <div class="add-source-row">
        <input type="text" id="new-source-url" placeholder="https://example.com/rss">
        <button class="btn btn-gold" onclick="addSource()">Qo'shish</button>
      </div>
    </div>

    <!-- KNOWLEDGE BASE -->
    <div class="view" id="view-kb">
      <div class="page-head"><h1>Knowledge Base</h1><p>AI shu ma'lumotlardan foydalanib post yozadi</p></div>

      <details class="kb-card" open>
        <summary>Nomlar tarjimasi (klub/futbolchi) <span class="count" id="term-count"></span></summary>
        <div id="term-rows"></div>
        <div style="display:flex; gap:8px; margin-top:8px">
          <button class="btn btn-ghost" onclick="addTermRow('term-rows')">+ qator</button>
          <button class="btn btn-gold" onclick="saveTerminology()">Saqlash</button>
        </div>
      </details>

      <details class="kb-card">
        <summary>Klub taxalluslari <span class="count" id="nick-count"></span></summary>
        <div id="nick-rows"></div>
        <div style="display:flex; gap:8px; margin-top:8px">
          <button class="btn btn-ghost" onclick="addTermRow('nick-rows')">+ qator</button>
          <button class="btn btn-gold" onclick="saveNicknames()">Saqlash</button>
        </div>
      </details>

      <details class="kb-card">
        <summary>Kanal qoidalari</summary>
        <div style="margin-top:10px">
          <span class="field-label">Kanal nomi</span>
          <input type="text" id="channel-tag" placeholder="@Inglizfutbol" style="margin-bottom:10px">
          <span class="field-label">Uslub (tone)</span>
          <textarea id="tone-field" placeholder="professional sport jurnalistikasi uslubida..." style="min-height:44px"></textarea>
          <div style="margin-top:10px"><button class="btn btn-gold" onclick="saveChannelSettings()">Saqlash</button></div>
        </div>
      </details>
    </div>

  </main>

  <aside class="rightpanel" id="rightpanel">
    <div class="rp-empty">
      <div>Postni tanlang — tafsilotlar shu yerda ko'rinadi</div>
    </div>
  </aside>

</div>

<div class="toast" id="toast"></div>

<script>
  function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 1800);
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.innerText = str || '';
    return div.innerHTML;
  }

  function fmtTime(iso) {
    if (!iso) return '';
    try {
      const then = new Date(iso).getTime();
      const diffMin = Math.max(0, Math.floor((Date.now() - then) / 60000));
      if (diffMin < 1) return 'hozirgina';
      if (diffMin < 60) return diffMin + ' daq oldin';
      const diffHour = Math.floor(diffMin / 60);
      if (diffHour < 24) return diffHour + ' soat oldin';
      return Math.floor(diffHour / 24) + ' kun oldin';
    } catch (e) { return ''; }
  }

  // ── View switching ─────────────────────────────────────
  const viewLoaded = {};
  function switchView(name) {
    document.querySelectorAll('.nav-item[data-view]').forEach(n => n.classList.toggle('active', n.dataset.view === name));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + name).classList.add('active');
    if (!viewLoaded[name]) {
      viewLoaded[name] = true;
      if (name === 'queue') loadAssets('draft', 'queue-draft');
      if (name === 'published') loadAssets('published', 'queue-published');
      if (name === 'rejected') loadAssets('rejected', 'queue-rejected');
      if (name === 'sources') loadSources();
      if (name === 'kb') loadConfig();
    }
  }

  // ── Dashboard ────────────────────────────────────────────
  let assetCache = {};
  let lastPendingCount = null; // polling: yangi draft kelganda bildirish uchun

  async function loadStats() {
    try {
      const res = await fetch('/api/studio/stats');
      const s = await res.json();
      document.getElementById('kpi-today').textContent = s.posts_today ?? '—';
      document.getElementById('kpi-pending').textContent = s.pending_review ?? '—';
      document.getElementById('kpi-published').textContent = s.published_total ?? '—';
      document.getElementById('kpi-sources').textContent = s.active_sources ?? '—';
      document.getElementById('lc-draft').textContent = s.pending_review ?? 0;
      document.getElementById('lc-published').textContent = s.published_total ?? 0;
      document.getElementById('lc-rejected').textContent = s.rejected_total ?? 0;
      document.getElementById('nav-count-draft').textContent = s.pending_review ?? 0;
      document.getElementById('nav-count-published').textContent = s.published_total ?? 0;
      document.getElementById('nav-count-rejected').textContent = s.rejected_total ?? 0;
      document.getElementById('nav-count-sources').textContent = s.total_sources ?? 0;

      if (typeof s.pending_review === 'number') {
        if (lastPendingCount !== null && s.pending_review > lastPendingCount) {
          toast('🆕 Yangi post Review Queue-ga qo\\'shildi');
        }
        lastPendingCount = s.pending_review;
      }
    } catch (e) {
      toast('Statistika yuklanmadi');
    }
  }

  async function loadActivityFeed() {
    const el = document.getElementById('activity-feed');
    try {
      const [draftRes, pubRes, rejRes] = await Promise.all([
        fetch('/api/studio/assets?status=draft'),
        fetch('/api/studio/assets?status=published'),
        fetch('/api/studio/assets?status=rejected'),
      ]);
      const [drafts, pub, rej] = await Promise.all([draftRes.json(), pubRes.json(), rejRes.json()]);
      const items = [
        ...drafts.map(a => ({ ...a, _kind: 'draft', _time: a.created_at })),
        ...pub.map(a => ({ ...a, _kind: 'published', _time: a.published_at || a.created_at })),
        ...rej.map(a => ({ ...a, _kind: 'rejected', _time: a.created_at })),
      ].sort((a, b) => new Date(b._time) - new Date(a._time)).slice(0, 8);

      if (!items.length) { el.innerHTML = '<div class="empty">Hozircha faoliyat yo\\'q.</div>'; return; }

      const labels = { draft: 'Review Queue-ga qo\\'shildi', published: 'Kanalga yuborildi', rejected: 'Rad etildi' };
      el.innerHTML = items.map(a => `
        <div class="feed-item">
          <div class="feed-dot ${a._kind}"></div>
          <div class="feed-text"><b>${labels[a._kind]}</b> — ${escapeHtml((a.title || '').slice(0, 60))}</div>
          <div class="feed-time">${fmtTime(a._time)}</div>
        </div>
      `).join('');
    } catch (e) {
      el.innerHTML = '<div class="empty">Xatolik yuz berdi.</div>';
    }
  }

  // ── Assets (Review Queue / Published / Rejected) ─────────
  async function loadAssets(status, containerId) {
    const el = document.getElementById(containerId);
    try {
      const res = await fetch('/api/studio/assets?status=' + status);
      const items = await res.json();
      items.forEach(a => assetCache[a.id] = a);
      if (!items.length) {
        el.innerHTML = '<div class="empty">Hozircha bu bo\\'limda post yo\\'q.</div>';
        return;
      }
      el.innerHTML = items.map(a => `
        <div class="q-card" data-id="${a.id}" onclick="openAsset(${a.id})">
          <div class="q-title">${escapeHtml((a.title || '').slice(0, 90))}</div>
          <div class="q-meta">
            <span>${escapeHtml(a.type || '')}</span>
            <span>${fmtTime(a.created_at)}</span>
            ${a.score ? '<span>ball: ' + a.score + '</span>' : ''}
          </div>
          <span class="status-chip ${a.status}">${a.status.toUpperCase()}</span>
        </div>
      `).join('');
    } catch (e) {
      el.innerHTML = '<div class="empty">Xatolik yuz berdi.</div>';
    }
  }

  function refreshCurrentLists() {
    loadStats();
    if (viewLoaded['queue']) loadAssets('draft', 'queue-draft');
    if (viewLoaded['published']) loadAssets('published', 'queue-published');
    if (viewLoaded['rejected']) loadAssets('rejected', 'queue-rejected');
    loadActivityFeed();
  }

  function openAsset(id) {
    const a = assetCache[id];
    if (!a) return;
    document.querySelectorAll('.q-card').forEach(c => c.classList.toggle('selected', Number(c.dataset.id) === id));
    const rp = document.getElementById('rightpanel');
    const isDraft = a.status === 'draft';
    rp.innerHTML = `
      <div class="rp-title">${escapeHtml((a.title || '').slice(0, 60))}</div>
      <div class="rp-sub">${escapeHtml(a.type || '')} · ${fmtTime(a.created_at)}${a.source_url ? ' · <a class="rp-link" href="' + escapeHtml(a.source_url) + '" target="_blank">manba</a>' : ''}</div>

      ${a.image_url ? `<div class="rp-section"><div class="rp-label">Rasm</div><div class="rp-img" style="background-image:url('${escapeHtml(a.image_url)}')"></div></div>` : ''}

      <div class="rp-section">
        <div class="rp-label">Post matni ${isDraft ? '(tahrirlash mumkin)' : ''}</div>
        <textarea id="rp-content" style="min-height:180px" ${isDraft ? '' : 'readonly'}>${escapeHtml(a.content || '')}</textarea>
      </div>

      ${isDraft ? `
        <div class="rp-actions">
          <button class="btn btn-ghost" onclick="saveAsset(${a.id})">Saqlash</button>
          <button class="btn btn-gold" onclick="approveAsset(${a.id})">Tasdiqlash va yuborish</button>
          <button class="btn btn-danger" onclick="rejectAsset(${a.id})">Rad etish</button>
        </div>
      ` : ''}
    `;
  }

  async function saveAsset(id) {
    try {
      const res = await fetch('/api/studio/assets/update', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ id, content: document.getElementById('rp-content').value })
      });
      const data = await res.json();
      if (!res.ok) { toast('Saqlashda xato: ' + (data.error || res.status)); return false; }
      toast('Saqlandi');
      return true;
    } catch (e) {
      console.error('[saveAsset]', e);
      toast('Saqlashda tarmoq xatosi: ' + e.message);
      return false;
    }
  }

  async function approveAsset(id) {
    if (!confirm('Bu post kanalga yuboriladi. Tasdiqlaysizmi?')) return;
    try {
      const saved = await saveAsset(id);
      if (!saved) return;
      const res = await fetch('/api/studio/assets/approve', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ id })
      });
      const data = await res.json();
      if (!res.ok) {
        console.error('[approveAsset] server error', res.status, data);
        toast('Yuborishda xato: ' + (data.error || res.status));
        return;
      }
      toast('Kanalga yuborildi ✅');
      document.getElementById('rightpanel').innerHTML = '<div class="rp-empty"><div>Postni tanlang — tafsilotlar shu yerda ko\\'rinadi</div></div>';
      refreshCurrentLists();
    } catch (e) {
      console.error('[approveAsset] exception', e);
      toast('Kutilmagan xato: ' + e.message);
    }
  }

  async function rejectAsset(id) {
    if (!confirm('Bu postni rad etasizmi?')) return;
    try {
      const res = await fetch('/api/studio/assets/reject', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ id })
      });
      const data = await res.json();
      if (!res.ok) {
        console.error('[rejectAsset] server error', res.status, data);
        toast('Rad etishda xato: ' + (data.error || res.status));
        return;
      }
      toast('Rad etildi');
      document.getElementById('rightpanel').innerHTML = '<div class="rp-empty"><div>Postni tanlang — tafsilotlar shu yerda ko\\'rinadi</div></div>';
      refreshCurrentLists();
    } catch (e) {
      console.error('[rejectAsset] exception', e);
      toast('Kutilmagan xato: ' + e.message);
    }
  }

  async function submitManual() {
    const textEl = document.getElementById('manual-text');
    const btn = document.getElementById('manual-submit-btn');
    const text = textEl.value.trim();
    if (!text) return;
    btn.disabled = true;
    btn.textContent = 'Ishlanmoqda...';
    try {
      const res = await fetch('/api/studio/assets/submit', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ text })
      });
      const data = await res.json();
      if (!res.ok) { toast(data.error || 'Xatolik'); return; }
      textEl.value = '';
      toast('Review Queue-ga qo\\'shildi');
      viewLoaded['queue'] = false;
      switchView('queue');
      refreshCurrentLists();
    } catch (e) {
      toast('Xatolik yuz berdi');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Generate Draft';
    }
  }

  // ── Sources ──────────────────────────────────────────────
  async function loadSources() {
    const el = document.getElementById('sources-list');
    try {
      const res = await fetch('/api/studio/sources');
      const rows = await res.json();
      if (!rows.length) { el.innerHTML = '<div class="empty">Hozircha manba yo\\'q.</div>'; return; }
      el.innerHTML = rows.map(r => `
        <div class="source-row">
          <span class="s-url ${r.active ? '' : 'inactive'}">${escapeHtml(r.url)}</span>
          <button class="btn btn-ghost" onclick="toggleSource(${r.id}, ${!r.active})">${r.active ? "O'chirish" : 'Yoqish'}</button>
          <button class="btn btn-danger" onclick="deleteSource(${r.id})">O'chirib tashlash</button>
        </div>
      `).join('');
    } catch (e) {
      el.innerHTML = '<div class="empty">Xatolik yuz berdi.</div>';
    }
  }

  async function addSource() {
    const input = document.getElementById('new-source-url');
    const url = input.value.trim();
    if (!url) return;
    const res = await fetch('/api/studio/sources', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    input.value = '';
    toast('Manba qo\\'shildi');
    loadSources();
    loadStats();
  }

  async function toggleSource(id, active) {
    await fetch('/api/studio/sources/toggle', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ id, active })
    });
    loadSources();
    loadStats();
  }

  async function deleteSource(id) {
    if (!confirm('Bu manbani butunlay o\\'chirib tashlaysizmi?')) return;
    await fetch('/api/studio/sources/delete', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ id })
    });
    loadSources();
    loadStats();
  }

  // ── Knowledge Base (terminology / nicknames / channel) ────
  function renderRows(containerId, dict) {
    const el = document.getElementById(containerId);
    const entries = Object.entries(dict || {});
    if (!entries.length) entries.push(['', '']);
    el.innerHTML = entries.map(([k, v]) => `
      <div class="term-row">
        <input type="text" class="term-key" value="${escapeHtml(k)}" placeholder="Inglizcha">
        <input type="text" class="term-val" value="${escapeHtml(v)}" placeholder="O'zbekcha">
        <button class="btn btn-danger" onclick="this.closest('.term-row').remove()">✕</button>
      </div>
    `).join('');
    const countEl = document.getElementById(containerId === 'term-rows' ? 'term-count' : 'nick-count');
    if (countEl) countEl.textContent = entries.length ? `(${entries.length})` : '';
  }

  function addTermRow(containerId) {
    const el = document.getElementById(containerId);
    const row = document.createElement('div');
    row.className = 'term-row';
    row.innerHTML = `
      <input type="text" class="term-key" placeholder="Inglizcha">
      <input type="text" class="term-val" placeholder="O'zbekcha">
      <button class="btn btn-danger" onclick="this.closest('.term-row').remove()">✕</button>
    `;
    el.appendChild(row);
  }

  function collectRows(containerId) {
    const el = document.getElementById(containerId);
    const dict = {};
    el.querySelectorAll('.term-row').forEach(row => {
      const k = row.querySelector('.term-key').value.trim();
      const v = row.querySelector('.term-val').value.trim();
      if (k && v) dict[k] = v;
    });
    return dict;
  }

  async function saveTerminology() {
    const terminology = collectRows('term-rows');
    const res = await fetch('/api/studio/config', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ terminology })
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    toast('Saqlandi');
    renderRows('term-rows', terminology);
  }

  async function saveNicknames() {
    const nicknames = collectRows('nick-rows');
    const res = await fetch('/api/studio/config', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ nicknames })
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    toast('Saqlandi');
    renderRows('nick-rows', nicknames);
  }

  async function saveChannelSettings() {
    const channel_tag = document.getElementById('channel-tag').value.trim();
    const tone = document.getElementById('tone-field').value.trim();
    const res = await fetch('/api/studio/config', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ channel_tag, tone })
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    toast('Saqlandi');
  }

  async function loadConfig() {
    try {
      const res = await fetch('/api/studio/config');
      const cfg = await res.json();
      renderRows('term-rows', cfg.terminology);
      renderRows('nick-rows', cfg.nicknames);
      document.getElementById('channel-tag').value = cfg.channel_tag || '';
      document.getElementById('tone-field').value = cfg.tone || '';
    } catch (e) {
      toast('Config yuklanmadi');
    }
  }

  // ── Polling — fon jarayoni (RSS avtomatik post qo'shishi,
  // boshqa admin tasdiqlashi va h.k.) natijalarini sahifani qo'lda
  // yangilamasdan ko'rsatish uchun. Tab fonda bo'lganda (document.hidden)
  // so'rov yubormaydi — resurs tejash uchun. Tab qayta ochilganda darhol
  // bir marta yangilaydi.
  const POLL_INTERVAL_MS = 25000;
  let pollTimer = null;

  function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(() => {
      if (document.hidden) return;
      refreshCurrentLists();
    }, POLL_INTERVAL_MS);
  }

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refreshCurrentLists();
  });

  // ── Boot ───────────────────────────────────────────────
  loadStats();
  loadActivityFeed();
  startPolling();
</script>
</body>
</html>
"""
