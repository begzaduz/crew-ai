STUDIO_HTML = """<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Studio Lab — AI Workflow</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0e1830; color: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    padding: 24px 18px 60px;
  }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .sub { color: #8a93ac; font-size: 13px; margin-bottom: 24px; }
  h2 { font-size: 15px; color: #f2c14e; margin: 28px 0 10px; letter-spacing: 0.02em; }
  .card {
    background: #162542; border: 0.5px solid #223154; border-radius: 12px;
    padding: 14px; margin-bottom: 8px;
  }
  .row { display: flex; align-items: center; gap: 10px; }
  .row + .row { margin-top: 8px; }
  input[type=text], textarea {
    background: #0e1830; border: 0.5px solid #223154; border-radius: 8px;
    color: #fff; padding: 9px 11px; font-size: 13.5px; flex: 1;
    font-family: inherit;
  }
  textarea { min-height: 60px; resize: vertical; width: 100%; }
  button {
    background: #f2c14e; color: #4a3400; border: none; border-radius: 8px;
    padding: 9px 14px; font-size: 13px; font-weight: 600; cursor: pointer;
    white-space: nowrap;
  }
  button:active { opacity: 0.8; }
  button.secondary { background: #243357; color: #fff; }
  button.danger { background: #3a1c22; color: #e2515a; }
  .source-url { flex: 1; font-size: 13px; word-break: break-all; }
  .source-url.inactive { opacity: 0.4; text-decoration: line-through; }
  .term-row { display: grid; grid-template-columns: 1fr 1fr auto; gap: 8px; margin-bottom: 8px; }
  .empty { color: #5f6b8f; font-size: 13px; padding: 10px 0; }
  .toast {
    position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
    background: #223154; color: #fff; padding: 10px 18px; border-radius: 8px;
    font-size: 13px; opacity: 0; transition: opacity 0.2s; pointer-events: none;
  }
  .toast.show { opacity: 1; }
  .field-label { font-size: 11px; color: #8a93ac; margin-bottom: 4px; display: block; }
</style>
</head>
<body>
  <h1>Studio Lab — AI Workflow</h1>
  <div class="sub">Ingliz Futboli loyihasi: RSS manbalar va terminologiya boshqaruvi</div>

  <h2>RSS MANBALAR</h2>
  <div id="sources-list"><div class="empty">Yuklanmoqda...</div></div>
  <div class="card row" style="margin-top:10px">
    <input type="text" id="new-source-url" placeholder="https://example.com/rss">
    <button onclick="addSource()">Qo'shish</button>
  </div>

  <h2>TERMINOLOGIYA (klub/futbolchi tarjimalari)</h2>
  <div class="card">
    <div id="term-rows"></div>
    <div class="row" style="margin-top:6px">
      <button class="secondary" onclick="addTermRow('terminology')">+ qator</button>
      <button onclick="saveTerminology()">Saqlash</button>
    </div>
  </div>

  <h2>KLUB TAXALLUSLARI</h2>
  <div class="card">
    <div id="nick-rows"></div>
    <div class="row" style="margin-top:6px">
      <button class="secondary" onclick="addTermRow('nicknames')">+ qator</button>
      <button onclick="saveNicknames()">Saqlash</button>
    </div>
  </div>

  <h2>KANAL SOZLAMALARI</h2>
  <div class="card">
    <span class="field-label">Kanal nomi</span>
    <input type="text" id="channel-tag" placeholder="@Inglizfutbol" style="width:100%; margin-bottom:12px">
    <span class="field-label">Uslub (tone)</span>
    <textarea id="tone-field" placeholder="professional sport jurnalistikasi uslubida..."></textarea>
    <div class="row" style="margin-top:10px">
      <button onclick="saveChannelSettings()">Saqlash</button>
    </div>
  </div>

  <div class="toast" id="toast"></div>

<script>
  let currentConfig = { terminology: {}, nicknames: {}, channel_tag: '', tone: '' };

  function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 1800);
  }

  async function loadSources() {
    const el = document.getElementById('sources-list');
    try {
      const res = await fetch('/api/studio/sources');
      const rows = await res.json();
      if (!rows.length) {
        el.innerHTML = '<div class="empty">Hozircha manba yo\\'q.</div>';
        return;
      }
      el.innerHTML = rows.map(r => `
        <div class="card row">
          <span class="source-url ${r.active ? '' : 'inactive'}">${escapeHtml(r.url)}</span>
          <button class="secondary" onclick="toggleSource(${r.id}, ${!r.active})">${r.active ? "O'chirish" : 'Yoqish'}</button>
          <button class="danger" onclick="deleteSource(${r.id})">O'chirib tashlash</button>
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
  }

  async function toggleSource(id, active) {
    await fetch('/api/studio/sources/toggle', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ id, active })
    });
    loadSources();
  }

  async function deleteSource(id) {
    if (!confirm('Bu manbani butunlay o\\'chirib tashlaysizmi?')) return;
    await fetch('/api/studio/sources/delete', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ id })
    });
    loadSources();
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.innerText = str || '';
    return div.innerHTML;
  }

  function renderRows(containerId, dict) {
    const el = document.getElementById(containerId);
    const entries = Object.entries(dict || {});
    if (!entries.length) entries.push(['', '']);
    el.innerHTML = entries.map(([k, v], i) => `
      <div class="term-row" data-idx="${i}">
        <input type="text" class="term-key" value="${escapeHtml(k)}" placeholder="Inglizcha">
        <input type="text" class="term-val" value="${escapeHtml(v)}" placeholder="O'zbekcha">
        <button class="danger" onclick="this.closest('.term-row').remove()">✕</button>
      </div>
    `).join('');
  }

  function addTermRow(kind) {
    const containerId = kind === 'terminology' ? 'term-rows' : 'nick-rows';
    const el = document.getElementById(containerId);
    const row = document.createElement('div');
    row.className = 'term-row';
    row.innerHTML = `
      <input type="text" class="term-key" placeholder="Inglizcha">
      <input type="text" class="term-val" placeholder="O'zbekcha">
      <button class="danger" onclick="this.closest('.term-row').remove()">✕</button>
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
    toast('Terminologiya saqlandi');
  }

  async function saveNicknames() {
    const nicknames = collectRows('nick-rows');
    const res = await fetch('/api/studio/config', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ nicknames })
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Xatolik'); return; }
    toast('Taxalluslar saqlandi');
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
    toast('Sozlamalar saqlandi');
  }

  async function loadConfig() {
    try {
      const res = await fetch('/api/studio/config');
      currentConfig = await res.json();
      renderRows('term-rows', currentConfig.terminology);
      renderRows('nick-rows', currentConfig.nicknames);
      document.getElementById('channel-tag').value = currentConfig.channel_tag || '';
      document.getElementById('tone-field').value = currentConfig.tone || '';
    } catch (e) {
      toast('Config yuklanmadi');
    }
  }

  loadSources();
  loadConfig();
</script>
</body>
</html>
"""
