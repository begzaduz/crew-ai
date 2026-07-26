"""
studio_ui.py
─────────────────────────────────────────────────────────────
Studio Lab ichki dashboard — /studio yo'lida xizmat qiladi.

Bu HECH QANDAY loyihaga qattiq bog'lanmagan: chap paneldagi
loyihalar ro'yxati /api/studio/projects'dan dinamik o'qiladi.
Ingliz Futboli — hozircha yagona qator, lekin kod uni maxsus
holat sifatida ishlatmaydi.
"""

HTML_STUDIO_PAGE = """<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Studio Lab — Boshqaruv</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,500;0,600;1,500;1,600&family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{
    --navy-deep:#0E1830; --navy-surface:#162542; --navy-surface-2:#1B2C4F;
    --navy-border:#223154; --gold:#F2C14E; --ink:#F3F1EA; --slate:#8A93AC;
    --slate-dim:#5F6B8F; --teal:#3DD68C; --coral:#E2515A;
    --r-sm:8px; --r-md:12px; --r-lg:16px;
  }
  *{box-sizing:border-box; margin:0; padding:0;}
  html,body{background:var(--navy-deep); color:var(--ink); font-family:'Inter',sans-serif; min-height:100vh;}
  .mono{font-family:'JetBrains Mono',monospace;}

  /* ===== Login ===== */
  #login-screen{
    position:fixed; inset:0; background:var(--navy-deep);
    display:flex; align-items:center; justify-content:center; z-index:100;
  }
  .login-box{
    width:340px; background:var(--navy-surface); border:1px solid var(--navy-border);
    border-radius:var(--r-lg); padding:32px 28px;
  }
  .login-box .brand{display:flex; align-items:center; gap:9px; margin-bottom:22px;}
  .login-box .brand .dot{width:9px; height:9px; border-radius:50%; background:var(--gold);}
  .login-box .brand span{font-family:'Space Grotesk'; font-weight:600; font-size:17px;}
  .login-box h2{font-family:'Newsreader'; font-weight:600; font-size:19px; margin-bottom:6px;}
  .login-box p{font-size:12.5px; color:var(--slate); margin-bottom:18px; line-height:1.5;}
  .login-box input{
    width:100%; background:var(--navy-deep); border:1px solid var(--navy-border);
    color:var(--ink); padding:10px 12px; border-radius:8px; font-size:13px; margin-bottom:12px;
    font-family:'JetBrains Mono';
  }
  .login-box button{
    width:100%; background:var(--gold); color:#241a05; border:none;
    padding:11px; border-radius:8px; font-weight:600; font-size:13.5px; cursor:pointer;
  }
  .login-error{color:var(--coral); font-size:12px; margin-top:10px; display:none;}

  /* ===== Shell (reused from mockup) ===== */
  .shell{display:none; min-height:100vh;}
  .shell.ready{display:flex;}
  .rail{width:220px; flex-shrink:0; background:var(--navy-surface); border-right:1px solid var(--navy-border); display:flex; flex-direction:column; padding:20px 14px;}
  .rail-brand{display:flex; align-items:center; gap:9px; padding:4px 8px 22px;}
  .rail-brand .dot{width:9px; height:9px; border-radius:50%; background:var(--gold); flex-shrink:0;}
  .rail-brand span{font-family:'Space Grotesk'; font-weight:600; font-size:16.5px;}
  .rail-label{font-size:10.5px; letter-spacing:0.09em; color:var(--slate-dim); text-transform:uppercase; padding:4px 10px 8px; margin-top:8px;}
  .rail-item{display:flex; align-items:center; gap:10px; padding:9px 10px; border-radius:var(--r-sm); color:var(--slate); font-size:13.5px; font-weight:500; cursor:pointer; border:1px solid transparent;}
  .rail-item:hover{background:var(--navy-surface-2); color:var(--ink);}
  .rail-item.active{background:var(--navy-surface-2); color:var(--ink); border-color:var(--navy-border);}
  .dotstatus{width:6px; height:6px; border-radius:50%; background:var(--teal); margin-left:auto;}
  .rail-item.ghost{color:var(--slate-dim); font-style:italic; cursor:default; border:1px dashed var(--navy-border);}
  .rail-item.ghost:hover{background:transparent; color:var(--slate-dim);}
  .rail-foot{margin-top:auto; padding-top:16px; border-top:1px solid var(--navy-border);}
  .rail-user{display:flex; align-items:center; justify-content:space-between; padding:8px 10px;}
  .rail-user .role{font-size:11px; color:var(--slate-dim); cursor:pointer;}

  .main{flex:1; min-width:0; display:flex; flex-direction:column;}
  .topbar{display:flex; align-items:center; justify-content:space-between; padding:16px 28px; border-bottom:1px solid var(--navy-border);}
  .breadcrumb{font-size:13px; color:var(--slate);}
  .breadcrumb b{color:var(--ink); font-weight:600;}
  .content{padding:26px 28px 60px; max-width:1180px;}
  .view{display:none;} .view.active{display:block;}

  .hero-line{font-size:13px; color:var(--slate); margin-bottom:4px;}
  .hero-title{font-family:'Newsreader'; font-weight:600; font-size:26px; margin-bottom:26px;}

  .pipeline-card{background:var(--navy-surface); border:1px solid var(--navy-border); border-radius:var(--r-lg); padding:24px 26px 20px; margin-bottom:22px;}
  .pipeline-head{display:flex; align-items:baseline; justify-content:space-between; margin-bottom:22px;}
  .pipeline-head h2{font-family:'Space Grotesk'; font-size:14.5px; font-weight:600;}
  .pipeline-head span{font-size:11.5px; color:var(--slate-dim);}
  .pipeline-track{display:flex; align-items:flex-start; overflow-x:auto;}
  .p-node{display:flex; flex-direction:column; align-items:center; width:120px; flex-shrink:0;}
  .p-node .ring{width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:1.5px solid var(--navy-border); background:var(--navy-deep); font-family:'JetBrains Mono'; font-size:12px; font-weight:500; color:var(--slate); margin-bottom:10px;}
  .p-node.gold .ring{border-color:var(--gold); color:var(--gold); background:rgba(242,193,78,0.1);}
  .p-node .lbl{font-size:12px; font-weight:600; margin-bottom:2px; text-align:center;}
  .p-node .cnt{font-family:'JetBrains Mono'; font-size:11px; color:var(--slate-dim);}
  .p-line{flex:1; height:1.5px; margin-top:17px; background:var(--navy-border); min-width:24px;}
  .p-line.gold-fill{background:linear-gradient(90deg, var(--teal), var(--gold));}

  .metric-row{display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:22px;}
  .metric{background:var(--navy-surface); border:1px solid var(--navy-border); border-radius:var(--r-md); padding:16px 18px;}
  .metric .m-label{font-size:11.5px; color:var(--slate); margin-bottom:8px;}
  .metric .m-val{font-family:'Space Grotesk'; font-size:24px; font-weight:600;}
  .metric .m-sub{font-family:'JetBrains Mono'; font-size:11px; color:var(--slate-dim); margin-top:4px;}

  .proj-row{display:flex; align-items:center; gap:12px; padding:10px 0; cursor:pointer;}
  .proj-icon{width:34px; height:34px; border-radius:8px; flex-shrink:0; background:var(--navy-surface-2); border:1px solid var(--navy-border); display:flex; align-items:center; justify-content:center; font-size:15px;}
  .proj-name{font-size:13px; font-weight:600;} .proj-sub{font-size:11px; color:var(--slate-dim);}
  .panel{background:var(--navy-surface); border:1px solid var(--navy-border); border-radius:var(--r-md); padding:18px 20px;}
  .panel h3{font-family:'Space Grotesk'; font-size:13.5px; font-weight:600; margin-bottom:14px;}
  .empty-note{font-size:12.5px; color:var(--slate-dim); padding:14px 0; line-height:1.6;}

  .proj-header{display:flex; align-items:center; justify-content:space-between; margin-bottom:20px;}
  .proj-title-row{display:flex; align-items:center; gap:12px;}
  .proj-title-row h1{font-family:'Space Grotesk'; font-size:20px; font-weight:600;}
  .status-tag{font-size:10.5px; font-weight:600; padding:3px 9px; border-radius:20px; background:rgba(61,214,140,0.1); color:var(--teal); border:1px solid rgba(61,214,140,0.3);}
  .tabs{display:flex; gap:4px; border-bottom:1px solid var(--navy-border); margin-bottom:22px;}
  .tab{padding:9px 4px; margin-right:22px; font-size:13px; font-weight:500; color:var(--slate); cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-1px;}
  .tab:hover{color:var(--ink);} .tab.active{color:var(--gold); border-color:var(--gold);}
  .subview{display:none;} .subview.active{display:block;}

  .row-card{display:flex; align-items:center; justify-content:space-between; padding:13px 16px; background:var(--navy-surface); border:1px solid var(--navy-border); border-radius:var(--r-md); margin-bottom:8px;}
  .row-left{display:flex; align-items:center; gap:12px;}
  .row-dot{width:7px; height:7px; border-radius:50%; background:var(--teal); flex-shrink:0;}
  .row-dot.off{background:var(--slate-dim);}
  .row-name{font-size:13px; font-weight:600;} .row-sub{font-family:'JetBrains Mono'; font-size:10.5px; color:var(--slate-dim);}
  .toggle{width:36px; height:20px; border-radius:20px; background:var(--gold); position:relative; cursor:pointer; flex-shrink:0;}
  .toggle::after{content:''; position:absolute; top:2px; right:2px; width:16px; height:16px; border-radius:50%; background:#241a05;}
  .toggle.off{background:var(--navy-border);}
  .toggle.off::after{right:auto; left:2px; background:var(--slate-dim);}

  .agent-grid{display:grid; grid-template-columns:repeat(3,1fr); gap:14px;}
  .agent-card{background:var(--navy-surface); border:1px solid var(--navy-border); border-radius:var(--r-md); padding:18px;}
  .agent-step{font-family:'JetBrains Mono'; font-size:10.5px; color:var(--gold); margin-bottom:8px;}
  .agent-card h4{font-family:'Space Grotesk'; font-size:14px; font-weight:600; margin-bottom:8px;}
  .agent-card p{font-size:12px; color:var(--slate); line-height:1.55;}

  .queue-card{background:var(--navy-surface); border:1px solid var(--navy-border); border-radius:var(--r-md); padding:16px 18px; margin-bottom:10px;}
  .queue-top{display:flex; align-items:center; justify-content:space-between; margin-bottom:9px;}
  .queue-score{font-family:'JetBrains Mono'; font-size:10.5px; color:var(--gold); background:rgba(242,193,78,0.1); padding:2px 8px; border-radius:6px;}
  .queue-title{font-size:13.5px; font-weight:600; margin-bottom:5px; line-height:1.4;}
  .queue-excerpt{font-size:12px; color:var(--slate); line-height:1.55; margin-bottom:12px; white-space:pre-line;}
  .queue-actions{display:flex; gap:8px;}
  .btn{font-size:12px; font-weight:600; padding:7px 14px; border-radius:7px; cursor:pointer; border:1px solid transparent;}
  .btn-approve{background:var(--gold); color:#241a05;}
  .btn-reject{background:transparent; color:var(--slate); border-color:var(--navy-border);}

  .soon-tag{font-size:10px; font-weight:600; color:var(--slate-dim); border:1px dashed var(--navy-border); padding:2px 8px; border-radius:20px;}
  .cols{display:grid; grid-template-columns:1.3fr 1fr; gap:16px;}
  @media (max-width:820px){
    .rail{position:fixed; left:-240px; top:0; bottom:0; z-index:20;}
    .metric-row{grid-template-columns:1fr;} .cols{grid-template-columns:1fr;} .agent-grid{grid-template-columns:1fr;}
    .content{padding:20px 16px 50px;}
  }
</style>
</head>
<body>

<div id="login-screen">
  <div class="login-box">
    <div class="brand"><span class="dot"></span><span>studiolab</span></div>
    <h2>Boshqaruvga kirish</h2>
    <p>Admin token'ingizni kiriting. Bu token Railway'dagi STUDIO_ADMIN_TOKEN o'zgaruvchisida saqlangan.</p>
    <input type="password" id="token-input" placeholder="Token..." autofocus>
    <button onclick="doLogin()">Kirish</button>
    <div class="login-error" id="login-error">Token noto'g'ri yoki server bilan bog'lanib bo'lmadi.</div>
  </div>
</div>

<div class="shell" id="shell">
  <div class="rail">
    <div class="rail-brand"><span class="dot"></span><span>studiolab</span></div>
    <div class="rail-label">Umumiy</div>
    <div class="rail-item active" onclick="showDashboard()">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/></svg>
      Boshqaruv
    </div>
    <div class="rail-label">Loyihalar</div>
    <div id="rail-projects"></div>
    <div class="rail-item ghost">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      Yangi loyiha
    </div>
    <div class="rail-foot">
      <div class="rail-user"><span>Admin</span><span class="role" onclick="logout()">Chiqish</span></div>
    </div>
  </div>

  <div class="main">
    <div class="topbar">
      <div class="breadcrumb" id="crumb"><b>Boshqaruv</b></div>
    </div>
    <div class="content">

      <div class="view active" id="view-dashboard">
        <div class="hero-line" id="today-line"></div>
        <div class="hero-title">Xush kelibsiz — boshqaruv markazi</div>

        <div class="pipeline-card">
          <div class="pipeline-head"><h2>KONTENT HOLATI</h2><span id="pipeline-project-name"></span></div>
          <div class="pipeline-track" id="pipeline-track">
            <div class="empty-note">Loyiha tanlanmagan.</div>
          </div>
        </div>

        <div class="cols">
          <div class="panel">
            <h3>Loyihalar</h3>
            <div id="projects-panel"><div class="empty-note">Yuklanmoqda...</div></div>
          </div>
          <div class="panel">
            <h3>Qanday ishlaydi</h3>
            <div class="empty-note">Chap paneldan loyihani tanlang — u yerda manbalar, AI workflow, navbat va chiqish kanallarini boshqarasiz.</div>
          </div>
        </div>
      </div>

      <div class="view" id="view-project">
        <div class="proj-header">
          <div class="proj-title-row">
            <h1 id="proj-title">—</h1>
            <span class="status-tag" id="proj-status">faol</span>
          </div>
        </div>
        <div class="tabs">
          <div class="tab active" onclick="showSub('sources', this)">Manbalar</div>
          <div class="tab" onclick="showSub('workflow', this)">AI Workflow</div>
          <div class="tab" onclick="showSub('queue', this)">Navbat <span class="mono" id="queue-count" style="color:var(--gold)"></span></div>
          <div class="tab" onclick="showSub('outputs', this)">Chiqishlar</div>
        </div>

        <div class="subview active" id="sub-sources"><div class="empty-note">Yuklanmoqda...</div></div>
        <div class="subview" id="sub-workflow"><div class="empty-note">Yuklanmoqda...</div></div>
        <div class="subview" id="sub-queue"><div class="empty-note">Yuklanmoqda...</div></div>
        <div class="subview" id="sub-outputs"><div class="empty-note">Yuklanmoqda...</div></div>
      </div>

    </div>
  </div>
</div>

<script>
let TOKEN = localStorage.getItem('studio_token') || '';
let PROJECTS = [];
let CURRENT = null;

function api(path, opts) {
  opts = opts || {};
  opts.headers = Object.assign({'Content-Type': 'application/json'}, opts.headers || {});
  if (TOKEN) opts.headers['Authorization'] = 'Bearer ' + TOKEN;
  return fetch(path, opts).then(async res => {
    if (res.status === 401) { logout(); throw new Error('unauthorized'); }
    return res.json();
  });
}

function doLogin() {
  TOKEN = document.getElementById('token-input').value.trim();
  localStorage.setItem('studio_token', TOKEN);
  boot();
}

function logout() {
  localStorage.removeItem('studio_token');
  TOKEN = '';
  document.getElementById('shell').classList.remove('ready');
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('login-error').style.display = 'block';
}

function boot() {
  api('/api/studio/projects').then(projects => {
    PROJECTS = projects;
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('shell').classList.add('ready');
    renderRail();
    renderDashboard();
    const d = new Date();
    document.getElementById('today-line').textContent = d.toLocaleDateString('uz-UZ', {weekday:'long', day:'numeric', month:'long'});
    if (projects.length) selectProject(projects[0].slug, false);
  }).catch(() => {});
}

function renderRail() {
  const el = document.getElementById('rail-projects');
  const icons = {'ingliz-futboli': '⚽'};
  el.innerHTML = PROJECTS.map(p => `
    <div class="rail-item" onclick="selectProject('${p.slug}', true)" data-slug="${p.slug}">
      <span>${icons[p.slug] || '◆'}</span> ${p.name} <span class="dotstatus"></span>
    </div>
  `).join('');
}

function renderDashboard() {
  const el = document.getElementById('projects-panel');
  if (!PROJECTS.length) { el.innerHTML = '<div class="empty-note">Hali loyiha yo\\'q.</div>'; return; }
  el.innerHTML = PROJECTS.map(p => `
    <div class="proj-row" onclick="selectProject('${p.slug}', true); showDashboard();">
      <div class="proj-icon">⚽</div>
      <div style="flex:1"><div class="proj-name">${p.name}</div><div class="proj-sub">${p.status}</div></div>
    </div>
  `).join('');
}

function showDashboard() {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-dashboard').classList.add('active');
  document.querySelectorAll('.rail-item').forEach(r => r.classList.remove('active'));
  document.getElementById('crumb').innerHTML = '<b>Boshqaruv</b>';
}

async function selectProject(slug, switchView) {
  const proj = await api('/api/studio/project?slug=' + encodeURIComponent(slug));
  CURRENT = proj;
  document.querySelectorAll('.rail-item[data-slug]').forEach(r => r.classList.toggle('active', r.dataset.slug === slug));

  const [sources, queueAll, outputs, workflow] = await Promise.all([
    api('/api/studio/sources?project_id=' + proj.id),
    api('/api/studio/queue?project_id=' + proj.id),
    api('/api/studio/outputs?project_id=' + proj.id),
    api('/api/studio/workflow?project_id=' + proj.id).catch(() => null),
  ]);

  renderPipeline(proj, queueAll);
  document.getElementById('proj-title').textContent = proj.name;
  document.getElementById('queue-count').textContent = '· ' + queueAll.filter(a => a.status === 'draft').length;
  renderSources(sources);
  renderWorkflow(workflow);
  renderQueue(queueAll.filter(a => a.status === 'draft'));
  renderOutputs(outputs);

  if (switchView) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-project').classList.add('active');
    document.getElementById('crumb').innerHTML = 'Loyihalar / <b>' + proj.name + '</b>';
  }
}

function renderPipeline(proj, assets) {
  document.getElementById('pipeline-project-name').textContent = proj.name;
  const draft = assets.filter(a => a.status === 'draft').length;
  const approved = assets.filter(a => a.status === 'approved').length;
  const published = assets.filter(a => a.status === 'published').length;
  const track = document.getElementById('pipeline-track');

  if (!assets.length) {
    track.innerHTML = '<div class="empty-note">Hali kontent yo\\'q — eski avtomatik pipeline hali yangi tizimga ulanmagan, shuning uchun bu yerda hozircha bo\\'sh. Keyingi bosqichda ulanadi.</div>';
    return;
  }
  track.innerHTML = `
    <div class="p-node"><div class="ring">${draft}</div><div class="lbl">Navbatda</div><div class="cnt">draft</div></div>
    <div class="p-line"></div>
    <div class="p-node"><div class="ring">${approved}</div><div class="lbl">Tasdiqlangan</div><div class="cnt">approved</div></div>
    <div class="p-line gold-fill"></div>
    <div class="p-node gold"><div class="ring">${published}</div><div class="lbl">Chop etilgan</div><div class="cnt">published</div></div>
  `;
}

function renderSources(sources) {
  const el = document.getElementById('sub-sources');
  if (!sources.length) { el.innerHTML = '<div class="empty-note">Manba qo\\'shilmagan.</div>'; return; }
  el.innerHTML = sources.map(s => `
    <div class="row-card">
      <div class="row-left">
        <span class="row-dot ${s.enabled ? '' : 'off'}"></span>
        <div><div class="row-name">${s.name}</div><div class="row-sub">${(s.config.url || '').replace('https://','')}</div></div>
      </div>
      <div class="toggle ${s.enabled ? '' : 'off'}" onclick="toggleSource(${s.id}, ${!s.enabled}, this)"></div>
    </div>
  `).join('');
}

function toggleSource(id, newState, el) {
  api('/api/studio/sources/toggle', {method:'POST', body: JSON.stringify({id, enabled:newState})})
    .then(() => el.classList.toggle('off'));
}

function renderWorkflow(wf) {
  const el = document.getElementById('sub-workflow');
  if (!wf) { el.innerHTML = '<div class="empty-note">Workflow konfiguratsiyasi topilmadi.</div>'; return; }
  const c = wf.config || {};
  const termCount = c.terminology ? Object.keys(c.terminology).length : 0;
  el.innerHTML = `
    <div class="agent-grid">
      <div class="agent-card"><div class="agent-step">01 · TADQIQOT</div><h4>Researcher</h4><p>Maqoladan faktlarni ajratadi.</p></div>
      <div class="agent-card"><div class="agent-step">02 · YOZISH</div><h4>Writer</h4><p>Faktlar asosida ${c.language || '—'} tilida post yozadi. Ohang: ${c.tone || '—'}</p></div>
      <div class="agent-card"><div class="agent-step">03 · TAHRIR</div><h4>Editor</h4><p>Tekshiradi va tuzatadi. Model: ${c.model || '—'}</p></div>
    </div>
    <div class="panel" style="margin-top:14px"><h3>Brand Brain — terminologiya</h3><div class="empty-note">${termCount} ta atama lug'atda saqlangan (klub/futbolchi nomlari).</div></div>
  `;
}

function renderQueue(drafts) {
  const el = document.getElementById('sub-queue');
  if (!drafts.length) { el.innerHTML = '<div class="empty-note">Navbat bo\\'sh — hali tekshiruv kutayotgan kontent yo\\'q.</div>'; return; }
  el.innerHTML = drafts.map(a => `
    <div class="queue-card">
      <div class="queue-top"><span class="queue-score">score: ${a.score}</span></div>
      <div class="queue-title">${a.title || '(sarlavhasiz)'}</div>
      <div class="queue-excerpt">${(a.content || '').slice(0, 220)}</div>
      <div class="queue-actions">
        <button class="btn btn-approve" onclick="reviewAsset(${a.id}, 'approved')">Tasdiqlash</button>
        <button class="btn btn-reject" onclick="reviewAsset(${a.id}, 'rejected')">Rad etish</button>
      </div>
    </div>
  `).join('');
}

function reviewAsset(id, decision) {
  api('/api/studio/assets/review', {method:'POST', body: JSON.stringify({asset_id:id, decision, reviewer:'admin'})})
    .then(() => selectProject(CURRENT.slug, true));
}

function renderOutputs(outputs) {
  const el = document.getElementById('sub-outputs');
  const icons = {telegram:'✈️', instagram:'◐', linkedin:'in'};
  let html = outputs.map(o => `
    <div class="row-card">
      <div class="row-left">
        <span class="row-dot ${o.enabled ? '' : 'off'}"></span>
        <div><div class="row-name">${o.name}</div><div class="row-sub">${o.channel_type}</div></div>
      </div>
      <div class="toggle ${o.enabled ? '' : 'off'}" onclick="toggleOutput(${o.id}, ${!o.enabled}, this)"></div>
    </div>
  `).join('');
  const existing = new Set(outputs.map(o => o.channel_type));
  ['instagram', 'linkedin'].forEach(ch => {
    if (!existing.has(ch)) {
      html += `<div class="row-card" style="opacity:0.5"><div class="row-left"><div><div class="row-name">${ch[0].toUpperCase()+ch.slice(1)}</div><div class="row-sub">Ulanmagan</div></div></div><span class="soon-tag">Tez orada</span></div>`;
    }
  });
  el.innerHTML = html || '<div class="empty-note">Chiqish kanali sozlanmagan.</div>';
}

function toggleOutput(id, newState, el) {
  api('/api/studio/outputs/toggle', {method:'POST', body: JSON.stringify({id, enabled:newState})})
    .then(() => el.classList.toggle('off'));
}

function showSub(name, el) {
  document.querySelectorAll('.subview').forEach(v => v.classList.remove('active'));
  document.getElementById('sub-' + name).classList.add('active');
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
}

if (TOKEN) { boot(); } else { document.getElementById('login-screen').style.display = 'flex'; }
</script>
</body>
</html>
"""
