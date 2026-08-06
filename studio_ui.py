STUDIO_HTML = """<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Studio Lab</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{
    /* "Wire desk" — kontent dispetcherlik konsoli: grafit fon +
       signal-amber accent, jurnalistik "dispatch" hissi. */
    --navy:#0b0d11; --navy-deep:#07080b; --surface:#14171d; --surface-2:#1b1f27;
    --border:#252a34; --gold:#ff8a3d; --gold-deep:#d96b22; --text:#eceef3; --text-dim:#8b92a3; --text-faint:#4e5563;
    --green:#3ecf8e; --red:#e5484d; --blue:#5b8cff; --radius:8px; --radius-sm:4px;
    --font-display:'Space Grotesk', sans-serif;
    --font-body:'Manrope', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --font-mono:'IBM Plex Mono', ui-monospace, 'SFMono-Regular', monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body {
    background: var(--navy); color: var(--text);
    font-family: var(--font-body);
    overflow: hidden;
  }
  h1, h3, h4, .brand-name{ font-family: var(--font-display); letter-spacing: -.01em; }
  .stat-value, .l-stage .ring, .nav-item .count, .feed-time, .q-meta, .rp-sub,
  #budget-used, #budget-limit, .tag{ font-family: var(--font-mono); }
  ::-webkit-scrollbar{ width:8px; height:8px; }
  ::-webkit-scrollbar-thumb{ background:var(--border); border-radius:8px; }

  .shell{ display:grid; grid-template-columns: 220px 1fr 320px; height:100vh; }

  .mobile-topbar{ display:none; }
  .mobile-backdrop{ display:none; }
  .rp-close-mobile{ display:none; }

  @media (max-width: 900px){
    body{ overflow:auto; }
    .shell{ display:block; height:auto; min-height:100vh; }

    .mobile-topbar{
      display:flex; align-items:center; gap:12px; padding:12px 16px;
      background:var(--navy-deep); border-bottom:1px solid var(--border);
      position:sticky; top:0; z-index:60;
    }
    .mobile-menu-btn{
      background:var(--surface); border:1px solid var(--border); color:var(--text);
      width:36px; height:36px; border-radius:8px; font-size:17px; cursor:pointer; flex-shrink:0;
    }
    .mobile-topbar-title{ font-size:15px; font-weight:700; }

    .mobile-backdrop.show{
      display:block; position:fixed; inset:0; background:rgba(10,18,36,.6); z-index:90;
    }

    .sidebar{
      position:fixed; top:0; left:0; bottom:0; width:260px; max-width:82vw;
      z-index:100; transform:translateX(-100%); transition:transform .2s ease;
      box-shadow:4px 0 24px rgba(0,0,0,.4);
    }
    .sidebar.open{ transform:translateX(0); }

    main{ padding:14px 12px 60px; }
    .stat-strip{ flex-wrap:wrap; }
    .stat-item{ flex:0 0 50%; border-top:1px solid var(--border); }
    .stat-item:nth-child(-n+2){ border-top:none; }
    .stat-item:nth-child(2n+1){ border-left:none; }

    .rightpanel{
      position:fixed; inset:0; z-index:110; width:auto; height:100vh;
      transform:translateX(100%); transition:transform .2s ease;
      padding:16px 16px 24px;
    }
    .rightpanel.open{ transform:translateX(0); }
    .rp-close-mobile{
      display:flex; align-items:center; gap:6px; background:var(--surface);
      border:1px solid var(--border); color:var(--text); border-radius:8px;
      padding:8px 14px; font-size:13px; margin-bottom:16px; cursor:pointer;
    }
  }

  .sidebar{ background:var(--navy-deep); border-right:1px solid var(--border); overflow-y:auto; display:flex; flex-direction:column; }
  .brand{ display:flex; align-items:center; gap:9px; padding:16px 16px 12px; border-bottom:1px solid var(--border); }
  .project-switcher{ display:flex; gap:5px; padding:10px 14px; border-bottom:1px solid var(--border); }
  .project-switcher select{ flex:1; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-sm); color:var(--text); font-size:12px; padding:6px 7px; font-family:inherit; }
  .project-switcher select:focus{ outline:none; border-color:var(--gold); }
  .project-switcher .btn{ padding:0 10px; font-size:14px; line-height:1; }
  .brand-mark{ width:26px; height:26px; border-radius:var(--radius-sm); background:var(--gold); display:flex; align-items:center; justify-content:center; font-weight:700; font-size:11.5px; font-family:var(--font-mono); color:var(--navy-deep); flex-shrink:0; }
  .brand-name{ font-size:14.5px; font-weight:600; }
  .brand-name span{ font-weight:400; color:var(--text-faint); }
  nav.groups{ padding:10px 8px; flex:1; }
  .group{ margin-bottom:12px; }
  .group-label{ font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--text-faint); font-weight:600; font-family:var(--font-mono); padding:5px 10px 5px; }
  .nav-item{ display:flex; align-items:center; gap:8px; padding:6px 10px; margin:0; border-radius:var(--radius-sm); font-size:12.5px; color:var(--text-dim); cursor:pointer; border-left:2px solid transparent; }
  .nav-item:hover{ background:var(--surface); color:var(--text); }
  .nav-item.active{ background:var(--surface); color:var(--gold); border-left-color:var(--gold); }
  .nav-item .count{ margin-left:auto; font-size:10px; color:var(--text-faint); background:var(--surface-2); padding:1px 6px; border-radius:var(--radius-sm); }
  .nav-item.active .count{ color:var(--gold); }
  .sidebar-foot{ padding:10px 14px; border-top:1px solid var(--border); font-size:10.5px; color:var(--text-faint); display:flex; align-items:center; gap:7px; }
  .status-dot{ width:6px; height:6px; border-radius:50%; background:var(--green); flex-shrink:0; }
  .status-dot.error{ background:var(--red); }
  .status-dot.idle{ background:var(--text-faint); }

  main{ overflow-y:auto; padding:18px 22px 50px; }
  .view{ display:none; }
  .view.active{ display:block; }
  .page-head{ margin-bottom:14px; }
  .page-head h1{ font-size:17px; font-weight:700; }
  .page-head p{ color:var(--text-faint); font-size:12px; margin-top:2px; }

  .stat-strip{ display:flex; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); margin-bottom:14px; overflow:hidden; }
  .stat-item{ flex:1; padding:10px 14px; border-left:1px solid var(--border); }
  .stat-item:first-child{ border-left:none; }
  .stat-label{ font-size:10px; color:var(--text-faint); text-transform:uppercase; letter-spacing:.04em; }
  .stat-value{ font-size:21px; font-weight:600; margin-top:3px; }

  .lifecycle-card{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:14px 16px; margin-bottom:14px; }
  .lifecycle-card h3{ font-size:11.5px; color:var(--text-dim); font-weight:600; margin-bottom:12px; letter-spacing:.03em; }
  .lifecycle{ display:flex; align-items:center; }
  .l-stage{ flex:1; text-align:center; }
  .l-stage .ring{ width:40px; height:40px; border-radius:var(--radius-sm); border:1.5px solid var(--border); display:flex; align-items:center; justify-content:center; margin:0 auto 6px; font-size:14px; font-weight:600; background:var(--navy-deep); }
  .l-stage.pending .ring{ border-color:var(--gold); color:var(--gold); }
  .l-stage.done .ring{ border-color:var(--green); color:var(--green); }
  .l-stage.rej .ring{ border-color:var(--red); color:var(--red); }
  .l-stage .name{ font-size:11px; color:var(--text-dim); font-weight:500; }
  .l-connector{ flex:0 0 auto; width:40px; height:1px; background:var(--border); margin-top:-20px; }

  .panel{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:12px 14px; }
  .panel h3{ font-size:11.5px; color:var(--text-dim); font-weight:600; margin-bottom:9px; }
  .feed-item{ display:flex; gap:8px; padding:6px 0; border-bottom:1px solid var(--border); font-size:11.5px; align-items:flex-start; }
  .feed-item:last-child{ border-bottom:none; }
  .feed-dot{ width:5px; height:5px; border-radius:50%; margin-top:5px; flex-shrink:0; }
  .feed-dot.draft{ background:var(--gold); }
  .feed-dot.published{ background:var(--green); }
  .feed-dot.rejected{ background:var(--red); }
  .feed-text{ color:var(--text-dim); }
  .feed-text b{ color:var(--text); font-weight:600; }
  .feed-time{ margin-left:auto; color:var(--text-faint); font-size:10px; white-space:nowrap; }

  .queue-grid{ display:flex; flex-direction:column; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }
  .q-card{ display:flex; align-items:center; gap:10px; padding:9px 12px; cursor:pointer; border-top:1px solid var(--border); }
  .q-card:first-child{ border-top:none; }
  .q-card:hover{ background:var(--surface-2); }
  .q-card.selected{ background:var(--surface-2); box-shadow:inset 2px 0 0 var(--gold); }
  .q-card-main{ flex:1; min-width:0; }
  .q-title{ font-size:12.5px; font-weight:600; line-height:1.3; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .q-meta{ display:flex; gap:7px; font-size:10px; color:var(--text-faint); margin-top:2px; flex-wrap:wrap; }
  .tag{ display:inline-block; font-size:9.5px; padding:2px 6px; border-radius:var(--radius-sm); font-weight:600; letter-spacing:.03em; flex-shrink:0; }
  .tag.draft{ background:rgba(255,138,61,.12); color:var(--gold); }
  .tag.published{ background:rgba(62,207,142,.12); color:var(--green); }
  .tag.rejected{ background:rgba(229,72,77,.12); color:var(--red); }
  .empty{ color:var(--text-faint); font-size:12.5px; padding:16px 4px; }

  .btn{ font-family:var(--font-body); font-size:11.5px; font-weight:600; border:none; border-radius:var(--radius-sm); padding:6px 11px; cursor:pointer; }
  .btn:disabled{ opacity:.5; cursor:default; }
  .btn-gold{ background:var(--gold); color:var(--navy-deep); }
  .btn-ghost{ background:var(--surface-2); color:var(--text-dim); border:1px solid var(--border); }
  .btn-danger{ background:rgba(229,72,77,.12); color:var(--red); border:1px solid rgba(229,72,77,.3); }
  .btn-green{ background:var(--green); color:var(--navy-deep); }
  .btn-icon{ display:inline-flex; align-items:center; justify-content:center; padding:8px; }
  .btn-icon svg{ width:16px; height:16px; flex-shrink:0; }
  .btn-icon-sm{ display:inline-flex; align-items:center; justify-content:center; padding:6px; }
  .btn-icon-sm svg{ width:13px; height:13px; flex-shrink:0; }

  .studio-card{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:16px 18px; max-width:640px; }
  .studio-card .subtitle{ color:var(--text-faint); font-size:12px; margin-bottom:12px; }
  .input-tabs{ display:flex; gap:6px; margin-bottom:10px; }
  .input-tab{ font-size:11px; padding:5px 11px; border-radius:var(--radius-sm); background:var(--surface-2); color:var(--text-dim); border:1px solid var(--border); }
  .input-tab.active{ background:var(--gold); color:var(--navy-deep); font-weight:600; border-color:var(--gold); }
  .input-tab.disabled{ opacity:.4; cursor:default; }
  textarea, input[type=text]{ width:100%; background:var(--navy-deep); border:1px solid var(--border); border-radius:var(--radius-sm); color:var(--text); font-size:12.5px; padding:9px 11px; font-family:inherit; }
  textarea{ min-height:100px; resize:vertical; line-height:1.5; }
  textarea:focus, input[type=text]:focus{ outline:none; border-color:var(--gold); }
  .studio-actions{ display:flex; justify-content:space-between; align-items:center; margin-top:12px; }
  .ai-steps{ display:flex; gap:10px; flex-wrap:wrap; font-size:10px; color:var(--text-faint); font-family:var(--font-mono); }
  .ai-steps span::before{ content:'○ '; color:var(--gold); }

  .source-row{ display:flex; align-items:center; gap:10px; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-sm); padding:8px 12px; margin-bottom:6px; flex-wrap:wrap; }
  .source-row .s-url{ flex:1; min-width:160px; font-size:11.5px; color:var(--text-dim); word-break:break-all; }
  .source-row .s-url.inactive{ opacity:.4; text-decoration:line-through; }
  .source-meta-input{ width:52px; background:var(--navy-deep); border:1px solid var(--border); border-radius:var(--radius-sm); color:var(--text); font-size:11px; padding:4px 6px; text-align:center; font-family:var(--font-mono); }
  .source-cat-input{ width:96px; background:var(--navy-deep); border:1px solid var(--border); border-radius:var(--radius-sm); color:var(--text); font-size:11px; padding:4px 8px; }
  .add-source-row{ display:flex; gap:8px; margin-top:10px; flex-wrap:wrap; }
  .add-source-row input[type=text]#new-source-url{ flex:1; min-width:180px; }

  .kb-card{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:12px 14px; margin-bottom:9px; }
  .kb-card summary{ cursor:pointer; font-size:12.5px; font-weight:600; list-style:none; display:flex; align-items:center; justify-content:space-between; }
  .kb-card summary::-webkit-details-marker{ display:none; }
  .kb-card summary .count{ color:var(--text-faint); font-weight:400; font-size:11px; font-family:var(--font-mono); }
  .kb-card[open] summary{ margin-bottom:10px; }
  .term-row{ display:grid; grid-template-columns:1fr 1fr auto; gap:7px; margin-bottom:5px; }
  .field-label{ font-size:10px; color:var(--text-faint); margin-bottom:3px; display:block; }

  .rightpanel{ background:var(--navy-deep); border-left:1px solid var(--border); padding:16px 16px; overflow-y:auto; }
  .rp-empty{ height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; color:var(--text-faint); font-size:12px; gap:8px; }
  .rp-title{ font-size:13.5px; font-weight:700; margin-bottom:2px; font-family:var(--font-display); }
  .rp-sub{ font-size:10.5px; color:var(--text-faint); margin-bottom:12px; }
  .rp-section{ margin-bottom:12px; }
  .rp-label{ font-size:9.5px; letter-spacing:.05em; text-transform:uppercase; color:var(--text-faint); font-weight:600; margin-bottom:6px; }
  .rp-img{ width:100%; height:100px; border-radius:var(--radius-sm); background:var(--surface) center/cover no-repeat; border:1px solid var(--border); display:flex; align-items:center; justify-content:center; color:var(--text-faint); font-size:11px; }
  .rp-actions{ display:flex; gap:7px; margin-top:12px; }
  .rp-actions .btn{ flex:1; padding:8px 0; text-align:center; }
  .rp-link{ color:var(--gold); font-size:11px; text-decoration:none; }

  .toast{ position:fixed; bottom:20px; left:50%; transform:translateX(-50%); background:var(--surface-2); border:1px solid var(--border); color:#fff; padding:9px 16px; border-radius:var(--radius-sm); font-size:12.5px; opacity:0; transition:opacity .2s; pointer-events:none; z-index:100; }
  .toast.show{ opacity:1; }

  .modal-overlay{ position:fixed; inset:0; background:rgba(7,8,11,.65); backdrop-filter:blur(2px); display:flex; align-items:center; justify-content:center; z-index:200; opacity:0; pointer-events:none; transition:opacity .15s ease; }
  .modal-overlay.show{ opacity:1; pointer-events:auto; }
  .modal-box{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:20px 22px; max-width:360px; width:90%; transform:translateY(6px); transition:transform .15s ease; box-shadow:0 12px 32px rgba(0,0,0,.5); }
  .modal-overlay.show .modal-box{ transform:translateY(0); }
  .modal-box h4{ font-size:14.5px; font-weight:700; margin-bottom:7px; }
  .modal-box p{ font-size:12.5px; color:var(--text-dim); line-height:1.5; margin-bottom:18px; }
  .modal-actions{ display:flex; gap:8px; justify-content:flex-end; }
  .modal-actions .btn{ padding:8px 16px; }
</style>
</head>
<body>
<div class="mobile-topbar">
  <button class="mobile-menu-btn" onclick="toggleMobileSidebar()" aria-label="Menyu">☰</button>
  <div class="mobile-topbar-title" id="mobile-topbar-title">Dashboard</div>
</div>
<div class="mobile-backdrop" id="mobile-backdrop" onclick="closeMobileSidebar()"></div>
<div class="shell">

  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">SL</div>
      <div class="brand-name"><span>Studio</span> Lab</div>
    </div>
    <div class="project-switcher">
      <select id="project-select" onchange="switchProject(this.value)"></select>
      <button class="btn btn-ghost" onclick="createNewProject()" title="Yangi loyiha">+</button>
      <button class="btn btn-danger btn-icon-sm" onclick="deleteCurrentProject()" title="Loyihani o'chirish" aria-label="Loyihani o'chirish">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
      </button>
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
      <div class="group">
        <div class="group-label">Advanced</div>
        <div class="nav-item" data-view="prompts" onclick="switchView('prompts')">Prompts</div>
      </div>
    </nav>
    <div class="sidebar-foot"><span class="status-dot" id="status-dot" title="Yuklanmoqda..."></span> <span id="sidebar-foot-text">Yuklanmoqda...</span></div>
  </aside>

  <main>

    <div class="view active" id="view-dashboard">
      <div class="page-head" style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px;">
        <div><h1>Dashboard</h1><p id="dashboard-subtitle">AI-Powered Creative Operations</p></div>
        <div id="status-badge" style="display:flex; align-items:center; gap:6px; font-size:11px; color:var(--text-faint); white-space:nowrap; padding-top:2px;">
          <span class="status-dot" id="status-dot-2"></span><span id="status-badge-text">—</span>
        </div>
      </div>

      <div class="stat-strip">
        <div class="stat-item"><div class="stat-label">Bugungi nashrlar</div><div class="stat-value" id="kpi-today">—</div></div>
        <div class="stat-item"><div class="stat-label">Tasdiqlash kutmoqda</div><div class="stat-value" id="kpi-pending">—</div></div>
        <div class="stat-item"><div class="stat-label">Jami nashr etilgan</div><div class="stat-value" id="kpi-published">—</div></div>
        <div class="stat-item"><div class="stat-label">Faol manbalar</div><div class="stat-value" id="kpi-sources">—</div></div>
      </div>

      <div class="lifecycle-card" style="display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;">
        <div>
          <h3 style="margin-bottom:6px">KUNLIK API BYUDJETI</h3>
          <div style="font-size:12.5px; color:var(--text-dim)">Ichki xavfsizlik limiti (Gemini'ning haqiqiy kvotasiga aloqasi yo'q) — <span id="budget-used">—</span>/<span id="budget-limit">—</span> chaqiruv ishlatilgan</div>
        </div>
        <button class="btn btn-ghost" onclick="resetBudget()">Byudjetni tozalash</button>
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

    <div class="view" id="view-queue">
      <div class="page-head"><h1>Review Queue</h1><p>Tasdiqlashni kutayotgan postlar</p></div>
      <div class="queue-grid" id="queue-draft"><div class="empty">Yuklanmoqda...</div></div>
    </div>

    <div class="view" id="view-published">
      <div class="page-head"><h1>Published</h1><p>Tanlangan loyiha kanaliga chiqqan postlar</p></div>
      <div class="queue-grid" id="queue-published"><div class="empty">Yuklanmoqda...</div></div>
    </div>

    <div class="view" id="view-rejected">
      <div class="page-head"><h1>Rejected</h1><p>Rad etilgan postlar</p></div>
      <div class="queue-grid" id="queue-rejected"><div class="empty">Yuklanmoqda...</div></div>
    </div>

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

    <div class="view" id="view-sources">
      <div class="page-head"><h1>Sources · RSS</h1><p>Studio Lab AI shu manbalardan yangiliklarni oladi. Ustuvorlik (priority) yuqori bo'lgan manba birinchi tekshiriladi.</p></div>
      <div id="sources-list"><div class="empty">Yuklanmoqda...</div></div>
      <div class="add-source-row">
        <input type="text" id="new-source-url" placeholder="https://example.com/rss">
        <input type="text" id="new-source-category" class="source-cat-input" placeholder="kategoriya">
        <input type="number" id="new-source-priority" class="source-meta-input" placeholder="0" value="0">
        <button class="btn btn-gold" onclick="addSource()">Qo'shish</button>
      </div>
    </div>

    <div class="view" id="view-kb">
      <div class="page-head"><h1>Knowledge Base</h1><p>AI shu ma'lumotlardan foydalanib post yozadi</p></div>

      <details class="kb-card" open>
        <summary>Loyiha va kanal sozlamalari</summary>
        <div style="margin-top:10px">
          <span class="field-label">Soha tavsifi (AI shu sohaning tahlilchisi/muharriri sifatida yozadi)</span>
          <input type="text" id="domain-description" placeholder="masalan: Premier League football" style="margin-bottom:10px">
          <span class="field-label">Telegram kanali (haqiqiy yuborish manzili — masalan @KanalNomi yoki -100...)</span>
          <input type="text" id="telegram-channel-id" placeholder="@Inglizfutbol" style="margin-bottom:10px">
          <span class="field-label">Kanal yorlig'i (postning oxiriga qo'shiladigan matn)</span>
          <input type="text" id="channel-tag" placeholder="@Inglizfutbol" style="margin-bottom:10px">
          <span class="field-label">Uslub (tone)</span>
          <textarea id="tone-field" placeholder="professional uslubda, aniq va ishonchli..." style="min-height:44px"></textarea>
          <span class="field-label" id="gemini-key-label">Gemini API kalit (ixtiyoriy — bo'lmasa umumiy kalit ishlatiladi)</span>
          <input type="text" id="gemini-api-key" placeholder="AQ.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" autocomplete="off" style="margin-bottom:2px">
          <div style="font-size:10.5px; color:var(--text-faint); margin-bottom:10px">Bu loyiha shu kalit orqali ishlaydi va boshqa loyihalarning kunlik Gemini limitiga ta'sir qilmaydi. Bo'sh qoldirsangiz, saqlangan qiymat o'zgarmaydi.</div>
          <div style="margin-top:10px"><button class="btn btn-gold" onclick="saveChannelSettings()">Saqlash</button></div>
        </div>
      </details>

      <details class="kb-card">
        <summary>Kontent turlari <span class="count" id="ctypes-count"></span></summary>
        <div id="ctypes-rows"></div>
        <div style="display:flex; gap:8px; margin-top:8px">
          <button class="btn btn-ghost" onclick="addListRow('ctypes-rows')">+ qator</button>
          <button class="btn btn-gold" onclick="saveContentTypes()">Saqlash</button>
        </div>
      </details>

      <details class="kb-card">
        <summary>Nomlar tarjimasi (terminologiya) <span class="count" id="term-count"></span></summary>
        <div id="term-rows"></div>
        <div style="display:flex; gap:8px; margin-top:8px">
          <button class="btn btn-ghost" onclick="addTermRow('term-rows')">+ qator</button>
          <button class="btn btn-gold" onclick="saveTerminology()">Saqlash</button>
        </div>
      </details>

      <details class="kb-card">
        <summary>Taxalluslar <span class="count" id="nick-count"></span></summary>
        <div id="nick-rows"></div>
        <div style="display:flex; gap:8px; margin-top:8px">
          <button class="btn btn-ghost" onclick="addTermRow('nick-rows')">+ qator</button>
          <button class="btn btn-gold" onclick="saveNicknames()">Saqlash</button>
        </div>
      </details>

      <details class="kb-card">
        <summary>Maxsus atamalar (tarjima qoidalari) <span class="count" id="jargon-count"></span></summary>
        <div id="jargon-rows"></div>
        <div style="display:flex; gap:8px; margin-top:8px">
          <button class="btn btn-ghost" onclick="addTermRow('jargon-rows')">+ qator</button>
          <button class="btn btn-gold" onclick="saveJargon()">Saqlash</button>
        </div>
      </details>

      <details class="kb-card">
        <summary>Emoji lug'ati <span class="count" id="emoji-count"></span></summary>
        <div id="emoji-rows"></div>
        <div style="display:flex; gap:8px; margin-top:8px">
          <button class="btn btn-ghost" onclick="addTermRow('emoji-rows')">+ qator</button>
          <button class="btn btn-gold" onclick="saveEmojiLegend()">Saqlash</button>
        </div>
      </details>
    </div>

    <div class="view" id="view-prompts">
      <div class="page-head"><h1>Prompts</h1><p>3 agent (Researcher → Writer → Editor) uchun xom promptlar. Bo'sh qoldirilsa — standart prompt ishlatiladi.</p></div>

      <details class="kb-card" open>
        <summary>Researcher prompt</summary>
        <div style="margin-top:10px">
          <textarea id="prompt-researcher" style="min-height:220px; font-family:monospace; font-size:11.5px;" placeholder="Standart prompt ishlatilyapti..."></textarea>
        </div>
      </details>

      <details class="kb-card" open>
        <summary>Writer prompt</summary>
        <div style="margin-top:10px">
          <textarea id="prompt-writer" style="min-height:260px; font-family:monospace; font-size:11.5px;" placeholder="Standart prompt ishlatilyapti..."></textarea>
        </div>
      </details>

      <details class="kb-card" open>
        <summary>Editor prompt</summary>
        <div style="margin-top:10px">
          <textarea id="prompt-editor" style="min-height:160px; font-family:monospace; font-size:11.5px;" placeholder="Standart prompt ishlatilyapti..."></textarea>
        </div>
      </details>

      <div style="display:flex; gap:8px; margin-top:4px">
        <button class="btn btn-ghost" onclick="resetPromptsToDefault()">Standartga qaytarish</button>
        <button class="btn btn-gold" onclick="savePrompts()">Saqlash</button>
      </div>
    </div>

  </main>

  <aside class="rightpanel" id="rightpanel">
    <div class="rp-empty">
      <div>Postni tanlang — tafsilotlar shu yerda ko'rinadi</div>
    </div>
  </aside>

</div>

<div class="toast" id="toast"></div>

<div class="modal-overlay" id="confirm-modal">
  <div class="modal-box">
    <h4 id="confirm-modal-title"></h4>
    <p id="confirm-modal-message"></p>
    <input type="text" id="confirm-modal-input" style="display:none; width:100%; margin-bottom:16px;">
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="_confirmModalAnswer(false)">Bekor qilish</button>
      <button class="btn" id="confirm-modal-ok" onclick="_confirmModalAnswer(true)"></button>
    </div>
  </div>
</div>

<script>
  function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 1800);
  }

  let _confirmResolve = null;
  let _confirmModalMode = 'confirm';

  function showConfirmModal({ title, message, okLabel, okClass = 'btn-gold' }) {
    return new Promise(resolve => {
      _confirmResolve = resolve;
      _confirmModalMode = 'confirm';
      document.getElementById('confirm-modal-title').textContent = title;
      document.getElementById('confirm-modal-message').textContent = message;
      document.getElementById('confirm-modal-input').style.display = 'none';
      const okBtn = document.getElementById('confirm-modal-ok');
      okBtn.textContent = okLabel;
      okBtn.className = 'btn ' + okClass;
      document.getElementById('confirm-modal').classList.add('show');
    });
  }

  function showInputModal({ title, message = '', placeholder = '', okLabel = 'Yaratish', okClass = 'btn-gold' }) {
    return new Promise(resolve => {
      _confirmResolve = resolve;
      _confirmModalMode = 'input';
      document.getElementById('confirm-modal-title').textContent = title;
      document.getElementById('confirm-modal-message').textContent = message;
      const inputEl = document.getElementById('confirm-modal-input');
      inputEl.style.display = 'block';
      inputEl.value = '';
      inputEl.placeholder = placeholder;
      const okBtn = document.getElementById('confirm-modal-ok');
      okBtn.textContent = okLabel;
      okBtn.className = 'btn ' + okClass;
      document.getElementById('confirm-modal').classList.add('show');
      setTimeout(() => inputEl.focus(), 50);
    });
  }

  function _confirmModalAnswer(result) {
    document.getElementById('confirm-modal').classList.remove('show');
    const inputEl = document.getElementById('confirm-modal-input');
    const wasInput = _confirmModalMode === 'input';
    inputEl.style.display = 'none';
    if (_confirmResolve) {
      _confirmResolve(wasInput ? (result ? inputEl.value.trim() : null) : result);
      _confirmResolve = null;
    }
  }

  let currentProjectId = Number(localStorage.getItem('studiolab_project_id')) || null;
  let projectsList = [];

  function apiGet(path) {
    const sep = path.includes('?') ? '&' : '?';
    return fetch(`${path}${sep}project_id=${currentProjectId}`);
  }

  function apiPost(path, body) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: currentProjectId, ...(body || {}) }),
    });
  }

  const ASSET_TYPE_LABELS = { rss_news: 'RSS', manual: "Qo'lda kiritilgan" };
  function assetTypeLabel(type) {
    return ASSET_TYPE_LABELS[type] || type || '';
  }

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

  function hostFromUrl(url) {
    if (!url) return null;
    try {
      return new URL(url).hostname.replace(/^www\\./, '');
    } catch (e) {
      return null;
    }
  }

  const viewLoaded = {};
  const VIEW_TITLES = {
    dashboard: 'Dashboard', queue: 'Review Queue', published: 'Published',
    rejected: 'Rejected', sources: 'RSS Sources', kb: 'Knowledge Base',
    studio: 'AI Content Studio', prompts: 'Prompts',
  };

  function switchView(name) {
    document.querySelectorAll('.nav-item[data-view]').forEach(n => n.classList.toggle('active', n.dataset.view === name));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + name).classList.add('active');
    const titleEl = document.getElementById('mobile-topbar-title');
    if (titleEl) titleEl.textContent = VIEW_TITLES[name] || 'Studio Lab';
    closeMobileSidebar();
    if (!viewLoaded[name]) {
      viewLoaded[name] = true;
      if (name === 'queue') loadAssets('draft', 'queue-draft');
      if (name === 'published') loadAssets('published', 'queue-published');
      if (name === 'rejected') loadAssets('rejected', 'queue-rejected');
      if (name === 'sources') loadSources();
      if (name === 'kb') loadConfig();
      if (name === 'prompts') loadPrompts();
    }
  }

  function toggleMobileSidebar() {
    document.querySelector('.sidebar').classList.toggle('open');
    document.getElementById('mobile-backdrop').classList.toggle('show');
  }

  function closeMobileSidebar() {
    document.querySelector('.sidebar').classList.remove('open');
    document.getElementById('mobile-backdrop').classList.remove('show');
  }

  let assetCache = {};
  let lastPendingCount = null;

  async function loadStats() {
    try {
      const res = await apiGet('/api/studio/stats');
      const s = await res.json();
      document.getElementById('kpi-today').textContent = s.posts_today ?? '—';
      document.getElementById('kpi-pending').textContent = s.pending_review ?? '—';
      document.getElementById('kpi-published').textContent = s.published_total ?? '—';
      document.getElementById('kpi-sources').textContent = s.active_sources ?? '—';
      document.getElementById('budget-used').textContent = s.api_calls_used_today ?? '—';
      document.getElementById('budget-limit').textContent = s.api_calls_limit_today ?? '—';
      document.getElementById('lc-draft').textContent = s.pending_review ?? 0;
      document.getElementById('lc-published').textContent = s.published_total ?? 0;
      document.getElementById('lc-rejected').textContent = s.rejected_total ?? 0;
      document.getElementById('nav-count-draft').textContent = s.pending_review ?? 0;
      document.getElementById('nav-count-published').textContent = s.published_total ?? 0;
      document.getElementById('nav-count-rejected').textContent = s.rejected_total ?? 0;
      document.getElementById('nav-count-sources').textContent = s.total_sources ?? 0;

      const dot = document.getElementById('status-dot');
      const dot2 = document.getElementById('status-dot-2');
      const badgeText = document.getElementById('status-badge-text');
      if (s.project_status) {
        const cls = 'status-dot' + (s.project_status !== 'active' ? ' ' + s.project_status : '');
        const labels = { active: 'Faol', error: "Ishlamayapti", idle: "Hali ishlamagan" };
        const titles = { active: 'Faol', error: "Ishlamayapti (oxirgi post: " + fmtTime(s.last_run_at) + ")", idle: 'Hali hech narsa yaratilmagan' };
        if (dot) { dot.className = cls; dot.title = titles[s.project_status] || ''; }
        if (dot2) { dot2.className = cls; dot2.title = titles[s.project_status] || ''; }
        if (badgeText) badgeText.textContent = labels[s.project_status] || '';
      }

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

  async function resetBudget() {
    const ok = await showConfirmModal({
      title: 'Kunlik byudjetni tozalash',
      message: "Bu loyihaning bugungi ichki API hisoblagichi 0'ga tushiriladi. Google'ning haqiqiy Gemini kvotasiga ta'sir qilmaydi. Davom etasizmi?",
      okLabel: 'Tozalash',
      okClass: 'btn-gold',
    });
    if (!ok) return;
    try {
      const res = await apiPost('/api/studio/budget/reset', {});
      const data = await res.json();
      if (!res.ok) { toast(data.error || 'Xatolik'); return; }
      toast('Byudjet tozalandi');
      loadStats();
    } catch (e) {
      toast('Xatolik yuz berdi');
    }
  }

  async function loadActivityFeed() {
    const el = document.getElementById('activity-feed');
    try {
      const [draftRes, pubRes, rejRes] = await Promise.all([
        apiGet('/api/studio/assets?status=draft'),
        apiGet('/api/studio/assets?status=published'),
        apiGet('/api/studio/assets?status=rejected'),
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

  async function loadAssets(status, containerId) {
    const el = document.getElementById(containerId);
    try {
      const res = await apiGet('/api/studio/assets?status=' + status);
      const items = await res.json();
      items.forEach(a => assetCache[a.id] = a);
      if (!items.length) {
        if (status === 'draft') {
          el.innerHTML = `
            <div class="empty">
              <div style="margin-bottom:10px">Hozircha Review Queue bo'sh.</div>
              <button class="btn btn-gold" onclick="switchView('studio')">+ AI Content Studio'da post yaratish</button>
            </div>
          `;
        } else {
          el.innerHTML = '<div class="empty">Hozircha bu bo\\'limda post yo\\'q.</div>';
        }
        return;
      }
      el.innerHTML = items.map(a => {
        const host = hostFromUrl(a.source_url);
        return `
        <div class="q-card" data-id="${a.id}" onclick="openAsset(${a.id})">
          <div class="q-card-main">
            <div class="q-title">${escapeHtml((a.title || '').slice(0, 90))}</div>
            <div class="q-meta">
              ${host ? '<span>' + escapeHtml(host) + '</span>' : `<span>${escapeHtml(assetTypeLabel(a.type))}</span>`}
              <span>${fmtTime(a.created_at)}</span>
              ${a.score ? '<span>ball ' + a.score + '</span>' : ''}
            </div>
          </div>
          <span class="tag ${a.status}">${a.status.toUpperCase()}</span>
        </div>
      `;
      }).join('');
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
      <button class="rp-close-mobile" onclick="closeRightPanel()">← Orqaga</button>
      <div class="rp-title">${escapeHtml((a.title || '').slice(0, 60))}</div>
      <div class="rp-sub">${escapeHtml(assetTypeLabel(a.type))} · ${fmtTime(a.created_at)}${a.source_url ? ' · <a class="rp-link" href="' + escapeAttr(a.source_url) + '" target="_blank">manba</a>' : ''}</div>

      ${a.image_url ? `<div class="rp-section"><div class="rp-label">Rasm</div><div class="rp-img" style="background-image:url('${escapeAttr(a.image_url)}')"></div></div>` : ''}

      <div class="rp-section">
        <div class="rp-label">Post matni ${isDraft ? '(tahrirlash mumkin)' : ''}</div>
        <textarea id="rp-content" style="min-height:180px" ${isDraft ? '' : 'readonly'}>${escapeHtml(a.content || '')}</textarea>
      </div>

      ${isDraft ? `
        <div class="rp-actions">
          <button class="btn btn-ghost btn-icon" onclick="saveAsset(${a.id})" title="Saqlash" aria-label="Saqlash">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8"/><path d="M7 3v5h8"/></svg>
          </button>
          <button class="btn btn-green btn-icon" onclick="approveAsset(${a.id})" title="Tasdiqlash va yuborish" aria-label="Tasdiqlash va yuborish">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </button>
          <button class="btn btn-danger btn-icon" onclick="rejectAsset(${a.id})" title="Rad etish" aria-label="Rad etish">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          </button>
        </div>
      ` : ''}
    `;
    rp.classList.add('open');
  }

  function closeRightPanel() {
    document.getElementById('rightpanel').innerHTML = '<div class="rp-empty"><div>Postni tanlang — tafsilotlar shu yerda ko\\'rinadi</div></div>';
    document.getElementById('rightpanel').classList.remove('open');
    document.querySelectorAll('.q-card').forEach(c => c.classList.remove('selected'));
  }

  async function saveAsset(id) {
    try {
      const res = await apiPost('/api/studio/assets/update', { id, content: document.getElementById('rp-content').value });
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
    const ok = await showConfirmModal({
      title: 'Kanalga yuborish',
      message: 'Bu post kanalga yuboriladi. Tasdiqlaysizmi?',
      okLabel: 'Tasdiqlash va yuborish',
      okClass: 'btn-green',
    });
    if (!ok) return;
    try {
      const saved = await saveAsset(id);
      if (!saved) return;
      const res = await apiPost('/api/studio/assets/approve', { id });
      const data = await res.json();
      if (!res.ok) {
        console.error('[approveAsset] server error', res.status, data);
        toast('Yuborishda xato: ' + (data.error || res.status));
        return;
      }
      toast('Kanalga yuborildi ✅');
      closeRightPanel();
      refreshCurrentLists();
    } catch (e) {
      console.error('[approveAsset] exception', e);
      toast('Kutilmagan xato: ' + e.message);
    }
  }

  async function rejectAsset(id) {
    const ok = await showConfirmModal({
      title: 'Postni rad etish',
      message: 'Bu postni rad etasizmi?',
      okLabel: 'Rad etish',
      okClass: 'btn-danger',
    });
    if (!ok) return;
    try {
      const res = await apiPost('/api/studio/assets/reject', { id });
      const data = await res.json();
      if (!res.ok) {
        console.error('[rejectAsset] server error', res.status, data);
        toast('Rad etishda xato: ' + (data.error || res.status));
        return;
      }
      toast('Rad etildi');
      closeRightPanel();
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
      const res = await apiPost('/api/studio/assets/submit', { text });
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

  function focusNewSourceInput() {
    const input = document.getElementById('new-source-url');
    if (input) { input.scrollIntoView({ behavior: 'smooth', block: 'center' }); input.focus(); }
  }

  async function loadSources() {
    const el = document.getElementById('sources-list');
    try {
      const res = await apiGet('/api/studio/sources');
      const rows = await res.json();
      if (!rows.length) {
        el.innerHTML = `
          <div class="empty">
            <div style="margin-bottom:10px">Hozircha RSS manba yo'q — AI hech qayerdan yangilik ololmaydi.</div>
            <button class="btn btn-gold" onclick="focusNewSourceInput()">+ Birinchi RSS manba qo'shish</button>
          </div>
        `;
        return;
      }
      el.innerHTML = rows.map(r => `
        <div class="source-row">
          <span class="s-url ${r.active ? '' : 'inactive'}">${escapeHtml(r.url)}</span>
          <input type="text" class="source-cat-input" value="${escapeAttr(r.category || '')}" placeholder="kategoriya" onchange="updateSourceMeta(${r.id}, undefined, this.value)">
          <input type="number" class="source-meta-input" value="${r.priority ?? 0}" title="Ustuvorlik" onchange="updateSourceMeta(${r.id}, this.value, undefined)">
          <button class="btn btn-ghost" onclick="toggleSource(${r.id}, ${!r.active})">${r.active ? "O'chirish" : 'Yoqish'}</button>
          <button class="btn btn-danger" onclick="deleteSource(${r.id})">O'chirib tashlash</button>
        </div>
      `).join('');
    } catch (e) {
      el.innerHTML = '<div class="empty">Xatolik yuz berdi.</div>';
    }
  }

  async function updateSourceMeta(id, priority, category) {
    const body = { id };
    if (priority !== undefined) body.priority = priority;
    if (category !== undefined) body.category = category;
    try {
      const res = await apiPost('/api/studio/sources/update', body);
      const data = await res.json();
      if (!res.ok) { toast(data.error || 'Xatolik'); return; }
      toast('Saqlandi');
      if (priority !== undefined) loadSources();
    } catch (e) {
      toast('Saqlashda xatolik yuz berdi');
    }
  }

  async function addSource() {
    const input = document.getElementById('new-source-url');
    const catInput = document.getElementById('new-source-category');
    const prioInput = document.getElementById('new-source-priority');
    const url = input.value.trim();
    if (!url) return;
    const body = { url };
    if (catInput && catInput.value.trim()) body.category = catInput.value.trim();
    if (prioInput && prioInput.value.trim()) body.priority = prioInput.value.trim();
    const res = await apiPost('/api/studio/sources', body);
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    input.value = '';
    if (catInput) catInput.value = '';
    if (prioInput) prioInput.value = '0';
    toast('Manba qo\\'shildi');
    loadSources();
    loadStats();
  }

  async function toggleSource(id, active) {
    await apiPost('/api/studio/sources/toggle', { id, active });
    loadSources();
    loadStats();
  }

  async function deleteSource(id) {
    const ok = await showConfirmModal({
      title: "Manbani o'chirish",
      message: "Bu manbani butunlay o'chirib tashlaysizmi?",
      okLabel: "O'chirish",
      okClass: 'btn-danger',
    });
    if (!ok) return;
    await apiPost('/api/studio/sources/delete', { id });
    loadSources();
    loadStats();
  }

  function renderRows(containerId, dict) {
    const el = document.getElementById(containerId);
    const entries = Object.entries(dict || {});
    if (!entries.length) entries.push(['', '']);
    el.innerHTML = entries.map(([k, v]) => `
      <div class="term-row">
        <input type="text" class="term-key" value="${escapeAttr(k)}" placeholder="Kalit">
        <input type="text" class="term-val" value="${escapeAttr(v)}" placeholder="Qiymat">
        <button class="btn btn-danger btn-icon-sm" onclick="this.closest('.term-row').remove()" title="O'chirish" aria-label="O'chirish"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
      </div>
    `).join('');
    const countEl = document.getElementById(containerId.replace('-rows', '-count'));
    if (countEl) countEl.textContent = entries.length ? `(${entries.length})` : '';
  }

  function addTermRow(containerId) {
    const el = document.getElementById(containerId);
    const row = document.createElement('div');
    row.className = 'term-row';
    row.innerHTML = `
      <input type="text" class="term-key" placeholder="Inglizcha">
      <input type="text" class="term-val" placeholder="O'zbekcha">
      <button class="btn btn-danger btn-icon-sm" onclick="this.closest('.term-row').remove()" title="O'chirish" aria-label="O'chirish"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
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

  function renderListRows(containerId, list) {
    const el = document.getElementById(containerId);
    const items = (list && list.length) ? list : [''];
    el.innerHTML = items.map(v => `
      <div class="term-row" style="grid-template-columns:1fr auto">
        <input type="text" class="list-val" value="${escapeAttr(v)}" placeholder="masalan: TRANSFER">
        <button class="btn btn-danger btn-icon-sm" onclick="this.closest('.term-row').remove()" title="O'chirish" aria-label="O'chirish"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
      </div>
    `).join('');
    const countEl = document.getElementById(containerId.replace('-rows', '-count'));
    if (countEl) countEl.textContent = items.length ? `(${items.length})` : '';
  }

  function addListRow(containerId) {
    const el = document.getElementById(containerId);
    const row = document.createElement('div');
    row.className = 'term-row';
    row.style.gridTemplateColumns = '1fr auto';
    row.innerHTML = `
      <input type="text" class="list-val" placeholder="masalan: TRANSFER">
      <button class="btn btn-danger btn-icon-sm" onclick="this.closest('.term-row').remove()" title="O'chirish" aria-label="O'chirish"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
    `;
    el.appendChild(row);
  }

  function collectListRows(containerId) {
    const el = document.getElementById(containerId);
    const list = [];
    el.querySelectorAll('.list-val').forEach(input => {
      const v = input.value.trim();
      if (v) list.push(v);
    });
    return list;
  }

  async function saveTerminology() {
    const terminology = collectRows('term-rows');
    const res = await apiPost('/api/studio/config', { terminology });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    toast('Saqlandi');
    renderRows('term-rows', terminology);
  }

  async function saveNicknames() {
    const nicknames = collectRows('nick-rows');
    const res = await apiPost('/api/studio/config', { nicknames });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    toast('Saqlandi');
    renderRows('nick-rows', nicknames);
  }

  async function saveJargon() {
    const jargon = collectRows('jargon-rows');
    const res = await apiPost('/api/studio/config', { jargon });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    toast('Saqlandi');
    renderRows('jargon-rows', jargon);
  }

  async function saveEmojiLegend() {
    const emoji_legend = collectRows('emoji-rows');
    const res = await apiPost('/api/studio/config', { emoji_legend });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    toast('Saqlandi');
    renderRows('emoji-rows', emoji_legend);
  }

  async function saveContentTypes() {
    const content_types = collectListRows('ctypes-rows');
    const res = await apiPost('/api/studio/config', { content_types });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    toast('Saqlandi');
    renderListRows('ctypes-rows', content_types);
  }

  async function saveChannelSettings() {
    const domain_description = document.getElementById('domain-description').value.trim();
    const channel_tag = document.getElementById('channel-tag').value.trim();
    const telegram_channel_id = document.getElementById('telegram-channel-id').value.trim();
    const tone = document.getElementById('tone-field').value.trim();
    const gemini_api_key = document.getElementById('gemini-api-key').value.trim();
    const res = await apiPost('/api/studio/config', { domain_description, channel_tag, telegram_channel_id, tone, gemini_api_key });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    toast('Saqlandi');
    document.getElementById('gemini-api-key').value = '';
    loadConfig();
  }

  async function loadConfig() {
    try {
      const res = await apiGet('/api/studio/config');
      const cfg = await res.json();
      renderRows('term-rows', cfg.terminology);
      renderRows('nick-rows', cfg.nicknames);
      renderRows('jargon-rows', cfg.jargon);
      renderRows('emoji-rows', cfg.emoji_legend);
      renderListRows('ctypes-rows', cfg.content_types);
      document.getElementById('domain-description').value = cfg.domain_description || '';
      document.getElementById('channel-tag').value = cfg.channel_tag || '';
      document.getElementById('telegram-channel-id').value = cfg.telegram_channel_id || '';
      document.getElementById('tone-field').value = cfg.tone || '';
      const keyInput = document.getElementById('gemini-api-key');
      keyInput.value = '';
      keyInput.placeholder = cfg.gemini_api_key_set
        ? `saqlangan: ••••${cfg.gemini_api_key_hint || ''} (o'zgartirish uchun yangisini yozing)`
        : 'AQ.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (bo\\'lmasa umumiy kalit ishlatiladi)';
    } catch (e) {
      toast('Config yuklanmadi');
    }
  }

  let promptDefaults = {};

  async function loadPrompts() {
    try {
      const res = await apiGet('/api/studio/config');
      const cfg = await res.json();
      promptDefaults = cfg.prompt_defaults || {};
      const custom = cfg.prompts || {};
      document.getElementById('prompt-researcher').value = custom.researcher || promptDefaults.researcher || '';
      document.getElementById('prompt-writer').value = custom.writer || promptDefaults.writer || '';
      document.getElementById('prompt-editor').value = custom.editor || promptDefaults.editor || '';
    } catch (e) {
      toast('Promptlar yuklanmadi');
    }
  }

  async function savePrompts() {
    const prompts = {
      researcher: document.getElementById('prompt-researcher').value,
      writer: document.getElementById('prompt-writer').value,
      editor: document.getElementById('prompt-editor').value,
    };
    try {
      const res = await apiPost('/api/studio/config', { prompts });
      const data = await res.json();
      if (!res.ok) { toast(data.error || 'Xatolik'); return; }
      toast('Promptlar saqlandi');
    } catch (e) {
      toast('Saqlashda xatolik yuz berdi');
    }
  }

  async function resetPromptsToDefault() {
    const ok = await showConfirmModal({
      title: 'Standartga qaytarish',
      message: "Barcha 3 ta prompt standart (kod ichidagi) versiyaga qaytariladi. Davom etasizmi?",
      okLabel: 'Qaytarish',
      okClass: 'btn-danger',
    });
    if (!ok) return;
    document.getElementById('prompt-researcher').value = promptDefaults.researcher || '';
    document.getElementById('prompt-writer').value = promptDefaults.writer || '';
    document.getElementById('prompt-editor').value = promptDefaults.editor || '';
    try {
      const res = await apiPost('/api/studio/config', { prompts: {} });
      const data = await res.json();
      if (!res.ok) { toast(data.error || 'Xatolik'); return; }
      toast('Standartga qaytarildi');
    } catch (e) {
      toast('Xatolik yuz berdi');
    }
  }

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

  async function initProjects() {
    try {
      const res = await fetch('/api/studio/projects');
      projectsList = await res.json();
      if (!projectsList.length) {
        document.getElementById('sidebar-foot-text').textContent = 'Loyiha topilmadi';
        return;
      }
      if (!currentProjectId || !projectsList.some(p => p.id === currentProjectId)) {
        currentProjectId = projectsList[0].id;
        localStorage.setItem('studiolab_project_id', String(currentProjectId));
      }
      renderProjectSelect();
      updateSidebarFoot();
    } catch (e) {
      document.getElementById('sidebar-foot-text').textContent = 'Loyihalar yuklanmadi';
    }
  }

  function renderProjectSelect() {
    const sel = document.getElementById('project-select');
    sel.innerHTML = projectsList.map(p =>
      `<option value="${p.id}" ${p.id === currentProjectId ? 'selected' : ''}>${escapeHtml(p.name)}</option>`
    ).join('');
  }

  function updateSidebarFoot() {
    const p = projectsList.find(p => p.id === currentProjectId);
    const label = p ? `${p.name} loyihasi` : '';
    document.getElementById('sidebar-foot-text').textContent = label;
    const subtitle = document.getElementById('dashboard-subtitle');
    if (subtitle) subtitle.textContent = p ? `AI-Powered Creative Operations — ${label}` : 'AI-Powered Creative Operations';
  }

  function switchProject(idStr) {
    currentProjectId = Number(idStr);
    localStorage.setItem('studiolab_project_id', String(currentProjectId));
    updateSidebarFoot();
    assetCache = {};
    lastPendingCount = null;
    closeRightPanel();
    Object.keys(viewLoaded).forEach(k => { viewLoaded[k] = false; });
    loadStats();
    loadActivityFeed();
    const activeView = document.querySelector('.nav-item.active');
    if (activeView) switchView(activeView.dataset.view);
  }

  async function createNewProject() {
    const name = await showInputModal({
      title: 'Yangi loyiha',
      message: "Loyiha nomini kiriting (masalan: \\"Toy Company UZ\\"):",
      placeholder: 'Loyiha nomi',
      okLabel: 'Yaratish',
    });
    if (!name) return;
    try {
      const res = await fetch('/api/studio/projects', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (!res.ok) { toast(data.error || 'Xatolik'); return; }
      projectsList.push(data);
      switchProject(String(data.id));
      renderProjectSelect();
      toast(`Loyiha yaratildi: ${data.name}`);
    } catch (e) {
      toast('Loyiha yaratishda xatolik');
    }
  }

  async function deleteCurrentProject() {
    if (projectsList.length <= 1) { toast("Oxirgi loyihani o'chirib bo'lmaydi"); return; }
    const p = projectsList.find(p => p.id === currentProjectId);
    if (!p) return;
    const typed = await showInputModal({
      title: `"${p.name}" loyihasini o'chirish`,
      message: "Bu QAYTARIB BO'LMAYDIGAN amal — barcha postlar, manbalar va sozlamalar o'chib ketadi. Tasdiqlash uchun loyiha nomini yozing:",
      placeholder: p.name,
      okLabel: "Butunlay o'chirish",
      okClass: 'btn-danger',
    });
    if (typed !== p.name) { if (typed !== null) toast("Nom mos kelmadi — bekor qilindi"); return; }
    try {
      const res = await fetch('/api/studio/projects/delete', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: currentProjectId }),
      });
      const data = await res.json();
      if (!res.ok) { toast(data.error || 'Xatolik'); return; }
      projectsList = projectsList.filter(x => x.id !== currentProjectId);
      currentProjectId = projectsList[0].id;
      localStorage.setItem('studiolab_project_id', String(currentProjectId));
      renderProjectSelect();
      updateSidebarFoot();
      toast("Loyiha o'chirildi");
      switchProject(String(currentProjectId));
    } catch (e) {
      toast('Xatolik yuz berdi');
    }
  }

  (async () => {
    await initProjects();
    loadStats();
    loadActivityFeed();
    startPolling();
  })();
</script>
</body>
</html>
"""
