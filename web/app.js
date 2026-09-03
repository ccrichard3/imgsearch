/* imgsearch · frontend logic — vanilla JS, no deps (offline-safe) */
'use strict';

const $ = (id) => document.getElementById(id);
const api = async (url, opts) => {
  const r = await fetch(url, opts);
  const ct = r.headers.get('content-type') || '';
  return ct.includes('application/json') ? r.json() : r.text();
};

const state = {
  mode: 'img',       // 'img' | 'txt'
  file: null,        // File for image search
  selected: null,    // selected result path
  running: false,
  pollTimer: null,
};

/* ----------------------------- toast ----------------------------- */
let toastTimer = null;
function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.classList.add('is-show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('is-show'), 3200);
}

/* ----------------------------- state / init ----------------------------- */
async function loadState() {
  const s = await api('/api/state');
  // model
  $('modelName').textContent = s.model.label.split(' ')[0] || s.model.label;
  const sel = $('modelSelect');
  sel.innerHTML = '';
  s.model.choices.forEach((label) => {
    const o = document.createElement('option');
    o.value = label; o.textContent = label;
    if (label === s.model.label) o.selected = true;
    sel.appendChild(o);
  });
  // roots
  renderRoots(s.roots);
  // index stats
  applyPending(s.pending);
  // port
  $('portInput').value = s.port;
  // offline
  const b = $('offlineBadge');
  b.textContent = s.offline ? '离线模式（本地缓存）' : '在线';
  b.className = 'badge ' + (s.offline ? 'badge--off' : 'badge--on');
  $('formatsNote').textContent = '支持：' + s.formats + '。首次使用某模型会联网下载权重，之后离线可用。';
  $('thresholdHint').textContent =
    `提示：启动时若变动图片少于 ${s.threshold} 张，会跳过自动编码以加快启动；` +
    `随时点上方按钮手动补索引即可。`;
  // index status
  applyIndex(s.index);
  if (s.index.running) startPolling();
}

function renderRoots(roots) {
  const list = $('rootList');
  list.innerHTML = '';
  if (!roots || !roots.length) {
    const e = document.createElement('div');
    e.className = 'rootlist__empty';
    e.textContent = '（尚未添加任何文件夹）';
    list.appendChild(e);
    return;
  }
  roots.forEach((r) => {
    const row = document.createElement('div');
    row.className = 'rootitem';
    const p = document.createElement('span');
    p.className = 'p'; p.textContent = r; p.title = r;
    const rm = document.createElement('button');
    rm.className = 'rootitem__rm'; rm.title = '移除'; rm.setAttribute('aria-label', '移除');
    rm.innerHTML = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>';
    rm.onclick = () => removeRoot(r);
    row.appendChild(p); row.appendChild(rm);
    list.appendChild(row);
  });
}

function applyPending(p) {
  if (!p) return;
  state.pending = p;
  $('statIndexed').textContent = p.indexed;
  $('statFiles').textContent = p.total_files;
  $('statTodo').textContent = p.todo;
  updateStatusPill();
}

function applyIndex(idx) {
  if (!idx) return;
  state.running = !!idx.running;
  state.pct = idx.pct || 0;
  state.idxErr = !!(idx.msg && idx.msg.indexOf('出错') >= 0);
  // 完整说明只放在「设置 → 索引」里，顶栏保持精简
  $('idxMsg').textContent = idx.msg || '';
  $('idxBar').style.width = Math.round((idx.pct || 0) * 100) + '%';
  $('btnReindex').disabled = idx.running;
  const tr = $('topReindex');
  if (tr) {
    tr.classList.toggle('is-busy', idx.running);
    tr.disabled = idx.running;
    tr.title = idx.running ? '正在索引…' : '重建 / 更新索引';
  }
  updateStatusPill();
}

/* 顶栏状态胶囊：精简显示，不堆砌说明 */
function updateStatusPill() {
  const txt = $('statustxt');
  const dot = $('statusdot');
  if (state.running) {
    txt.textContent = '索引中 ' + Math.round((state.pct || 0) * 100) + '%';
    dot.className = 'dot is-run';
    return;
  }
  if (state.idxErr) {
    txt.textContent = '索引出错';
    dot.className = 'dot is-warn';
    return;
  }
  const p = state.pending;
  txt.textContent = p
    ? (p.todo > 0 ? `就绪 · 库 ${p.total_files} · 待索引 ${p.todo}` : `就绪 · 库 ${p.total_files} 张`)
    : '就绪';
  dot.className = 'dot is-ok';
}

/* ----------------------------- polling ----------------------------- */
function startPolling() {
  if (state.pollTimer) return;
  state.pollTimer = setInterval(async () => {
    const idx = await api('/api/index/status');
    applyIndex(idx);
    if (!idx.running) {
      clearInterval(state.pollTimer); state.pollTimer = null;
      const s = await api('/api/state');   // refresh stats once done
      applyPending(s.pending);
    }
  }, 1000);
}

/* ----------------------------- mode toggle ----------------------------- */
function setMode(m) {
  state.mode = m;
  const img = m === 'img';
  $('segImg').setAttribute('aria-selected', String(img));
  $('segTxt').setAttribute('aria-selected', String(!img));
  $('rowImg').classList.toggle('hidden', !img);
  $('rowTxt').classList.toggle('hidden', img);
  if (!img) $('txtInput').focus();
}

/* ----------------------------- search ----------------------------- */
function setBusy(btn, busy, label) {
  btn.disabled = busy;
  if (busy) {
    if (!btn.dataset._html) btn.dataset._html = btn.innerHTML;
    btn.textContent = label || '搜索中…';
  } else if (btn.dataset._html) {
    btn.innerHTML = btn.dataset._html;   // 恢复含图标的原始内容
    delete btn.dataset._html;
  }
}

async function searchText() {
  const q = $('txtInput').value.trim();
  if (!q) { toast('请输入描述文字。'); return; }
  const btn = $('btnTxt');
  setBusy(btn, true);
  $('resultCount').textContent = '搜索中…';
  try {
    const res = await api('/api/search/text', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query: q, top_k: +$('topk').value, min_sim: +$('minsim').value }),
    });
    renderResults(res);
  } catch (e) { toast('搜索失败：' + e); }
  finally { setBusy(btn, false); }
}

async function searchImage() {
  if (!state.file) { toast('请先拖入或选择一张查询图片。'); return; }
  const btn = $('btnImg');
  setBusy(btn, true, '搜索中…');
  $('resultCount').textContent = '搜索中…';
  try {
    const fd = new FormData();
    fd.append('file', state.file);
    fd.append('top_k', $('topk').value);
    fd.append('min_sim', $('minsim').value);
    const res = await api('/api/search/image', { method: 'POST', body: fd });
    renderResults(res);
  } catch (e) { toast('搜索失败：' + e); }
  finally { setBusy(btn, false); }
}

function renderResults(res) {
  const box = $('results');
  box.innerHTML = '';
  state.selected = null;
  $('btnReveal').disabled = true;
  $('btnOpen').disabled = true;

  if (!res.ok && (!res.results || !res.results.length)) {
    $('resultCount').textContent = res.msg || '无结果';
    box.appendChild(emptyBlock(res.msg || '无结果。'));
    return;
  }
  const list = res.results || [];
  const filtered = (res.total != null && res.total > list.length)
    ? `（已按阈值过滤 ${res.total - list.length} 条）` : '';
  $('resultCount').innerHTML = `共 <b>${list.length}</b> 条结果 ${filtered}`;

  if (!list.length) { box.appendChild(emptyBlock('无结果（可调低相似度阈值）。')); return; }

  const grid = document.createElement('div');
  grid.className = 'cc-grid';
  list.forEach((r, i) => {
    const fig = document.createElement('figure');
    fig.className = 'cc-cell';
    fig.dataset.path = r.path;
    fig.title = r.name + '\n' + r.path + '\n（双击在访达中显示）';
    fig.style.animationDelay = Math.min(i * 12, 240) + 'ms';

    const img = document.createElement('img');
    img.src = r.thumb; img.loading = 'lazy'; img.alt = r.name;

    const cap = document.createElement('figcaption');
    const sim = document.createElement('span');
    sim.className = 'sim'; sim.textContent = r.sim.toFixed(3);
    const nm = document.createElement('span');
    nm.className = 'nm'; nm.textContent = r.name;
    cap.appendChild(sim); cap.appendChild(nm);

    fig.appendChild(img); fig.appendChild(cap);
    grid.appendChild(fig);
  });
  box.appendChild(grid);
  box.scrollIntoView({ block: 'nearest' });
}

function emptyBlock(msg) {
  const d = document.createElement('div');
  d.className = 'empty';
  d.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>';
  const b = document.createElement('b'); b.textContent = msg;
  d.appendChild(b);
  return d;
}

/* result selection (single-click select, double-click reveal) */
$('results').addEventListener('click', (e) => {
  const cell = e.target.closest('.cc-cell');
  if (!cell) return;
  document.querySelectorAll('.cc-cell.cc-selected').forEach((x) => x.classList.remove('cc-selected'));
  cell.classList.add('cc-selected');
  state.selected = cell.dataset.path;
  $('btnReveal').disabled = false;
  $('btnOpen').disabled = false;
});
$('results').addEventListener('dblclick', (e) => {
  const cell = e.target.closest('.cc-cell');
  if (!cell) return;
  state.selected = cell.dataset.path;
  revealSelected();
});

async function revealSelected() {
  if (!state.selected) return;
  const r = await api('/api/reveal', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ path: state.selected }),
  });
  if (!r.ok) toast(r.msg);
}
async function openSelected() {
  if (!state.selected) return;
  const r = await api('/api/open', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ path: state.selected }),
  });
  if (!r.ok) toast(r.msg);
}

/* ----------------------------- image input ----------------------------- */
function setQueryFile(file) {
  if (!file || !file.type.startsWith('image/')) return;
  state.file = file;
  setMode('img');
  const url = URL.createObjectURL(file);
  const t = $('dropThumb');
  t.src = url; t.classList.remove('hidden');
  $('dropEmpty').classList.add('hidden');
  $('dropTitle').textContent = '已选择图片';
  $('dropName').textContent = file.name || '（剪贴板图片）';
  searchImage();
}

$('fileInput').addEventListener('change', (e) => {
  if (e.target.files && e.target.files[0]) setQueryFile(e.target.files[0]);
});

/* full-page drag & drop */
function fileUriToPath(uri) {
  const line = (uri || '').split('\n').map((s) => s.trim()).find((s) => s && !s.startsWith('#')) || '';
  if (line.startsWith('file://')) {
    try { return decodeURIComponent(new URL(line).pathname); } catch (_) { return ''; }
  }
  return line;
}

let dragDepth = 0;
window.addEventListener('dragenter', (e) => {
  if (e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files')) {
    dragDepth++; $('dnd').classList.add('is-show');
  }
});
window.addEventListener('dragover', (e) => { e.preventDefault(); });
window.addEventListener('dragleave', () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) $('dnd').classList.remove('is-show'); });
window.addEventListener('drop', async (e) => {
  e.preventDefault();
  dragDepth = 0; $('dnd').classList.remove('is-show');
  if (!e.dataTransfer) return;

  // directory dragged from Finder → add as a library root
  const items = e.dataTransfer.items;
  let isDir = false;
  if (items && items.length && items[0].webkitGetAsEntry) {
    const entry = items[0].webkitGetAsEntry();
    if (entry && entry.isDirectory) isDir = true;
  }
  if (isDir) {
    const path = fileUriToPath(e.dataTransfer.getData('text/uri-list') || e.dataTransfer.getData('text/plain'));
    if (path) { addRoot(path); openDrawer(); }
    else toast('无法读取该文件夹路径（浏览器限制）。请在「设置 → 库文件夹」粘贴完整路径。');
    return;
  }
  // otherwise: image search
  if (e.dataTransfer.files && e.dataTransfer.files[0]) setQueryFile(e.dataTransfer.files[0]);
});

/* paste image anywhere */
window.addEventListener('paste', (e) => {
  const items = (e.clipboardData || {}).items || [];
  for (const it of items) {
    if (it.type && it.type.startsWith('image/')) { setQueryFile(it.getAsFile()); break; }
  }
});

/* ----------------------------- settings actions ----------------------------- */
function openDrawer() {
  $('scrim').classList.add('is-open');
  $('drawer').classList.add('is-open');
  $('drawer').setAttribute('aria-hidden', 'false');
}
function closeDrawer() {
  $('scrim').classList.remove('is-open');
  $('drawer').classList.remove('is-open');
  $('drawer').setAttribute('aria-hidden', 'true');
}

async function addRoot(path) {
  const p = (path || '').trim();
  if (!p) { toast('请输入文件夹路径。'); return; }
  const r = await api('/api/roots', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ path: p, action: 'add' }),
  });
  toast(r.msg);
  if (r.ok) { $('rootInput').value = ''; renderRoots(r.roots); startPolling(); refreshStats(); }
}
async function removeRoot(path) {
  const r = await api('/api/roots', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ path, action: 'remove' }),
  });
  toast(r.msg);
  if (r.ok) { renderRoots(r.roots); startPolling(); refreshStats(); }
}
async function refreshStats() {
  const s = await api('/api/state');
  applyPending(s.pending); applyIndex(s.index);
}

async function reindex() {
  const r = await api('/api/reindex', { method: 'POST' });
  if (r.ok) { applyIndex(r.index); startPolling(); }
  else toast(r.msg);
}

async function changeModel(label) {
  const r = await api('/api/model', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ label }),
  });
  toast(r.msg);
  if (r.ok) {
    $('modelName').textContent = r.model.label.split(' ')[0];
    $('modelPathDetail').classList.add('hidden');   // 路径面板可能已过期，收起
    startPolling(); refreshStats();
  }
}

async function savePort() {
  const r = await api('/api/port', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ port: +$('portInput').value }),
  });
  toast(r.msg);
}

/* ----------------------------- model storage location ----------------------------- */
function escHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}
function mpRow(k, vHtml) {
  return '<div class="modelpath__row"><span class="modelpath__k">' + k +
    '</span><span class="modelpath__v">' + vHtml + '</span></div>';
}
async function toggleModelPath() {
  const box = $('modelPathDetail');
  if (!box.classList.contains('hidden')) { box.classList.add('hidden'); return; }
  box.classList.remove('hidden');
  box.innerHTML = mpRow('', '读取中…');
  let info;
  try { info = await api('/api/model/paths'); }
  catch (e) { box.innerHTML = mpRow('', '读取失败：' + escHtml(e)); return; }
  const kindTag = info.active_kind === 'manual'
    ? '<span class="tag tag--ok">手动目录</span>'
    : info.active_kind === 'hf-cache'
      ? '<span class="tag tag--ok">HF 缓存</span>'
      : '<span class="tag tag--warn">尚未下载</span>';
  const activeVal = info.active
    ? escHtml(info.active) + kindTag
    : '尚未下载（首次搜索会联网下载；或按下方手动放置）' + kindTag;
  box.innerHTML =
    mpRow('系统', escHtml(info.os) + ' · 模型 ' + escHtml(info.model_name)) +
    mpRow('当前加载自', activeVal) +
    mpRow('手动放置目录（推荐）', escHtml(info.manual_dir)) +
    mpRow('HF 缓存目录', escHtml(info.hf_cache)) +
    '<div class="modelpath__actions">' +
      '<button class="btn btn--sm" id="mpOpen">打开文件夹</button>' +
      '<button class="btn btn--sm" id="mpCopy">复制手动目录路径</button>' +
    '</div>';
  $('mpOpen').onclick = async () => {
    const r = await api('/api/model/reveal', { method: 'POST' });
    toast(r.msg || (r.ok ? '已打开' : '无法打开'));
  };
  $('mpCopy').onclick = async () => {
    try { await navigator.clipboard.writeText(info.manual_dir); toast('已复制：' + info.manual_dir); }
    catch (_) { toast('复制失败，请手动选择路径复制：\n' + info.manual_dir); }
  };
}

async function quitApp() {
  state.quitting = true;   // 抑制 pagehide 再次发送
  try { await api('/api/quit', { method: 'POST' }); } catch (_) { /* 进程可能已退出 */ }
  document.body.innerHTML =
    '<div style="display:grid;place-items:center;min-height:100vh;font-family:var(--font-ui);color:var(--ink-1);text-align:center;padding:24px">'
    + '<div><h1 style="color:var(--ink-0)">⏻ imgsearch 已退出</h1>'
    + '<p>进程已结束，模型内存与端口均已释放。可关闭此标签页；需要时再双击图标启动。</p></div></div>';
}

/* 关闭网页即退出：标签页真正卸载时给服务发一个退出信标。
   用 sendBeacon（unload 阶段唯一可靠的发送方式）。
   刷新守卫：拦截 Cmd/Ctrl+R、F5 时置位 reloading，避免刷新误杀进程；
   页面重新加载后该标志自然清空。 */
let reloading = false;
window.addEventListener('keydown', (e) => {
  if (e.key === 'F5' || ((e.metaKey || e.ctrlKey) && (e.key === 'r' || e.key === 'R'))) {
    reloading = true;
  }
});
window.addEventListener('pagehide', () => {
  if (reloading || state.quitting) return;
  try { navigator.sendBeacon('/api/quit'); } catch (_) { /* ignore */ }
});

/* ----------------------------- wiring ----------------------------- */
$('segImg').onclick = () => setMode('img');
$('segTxt').onclick = () => setMode('txt');
$('btnImg').onclick = searchImage;
$('btnTxt').onclick = searchText;
$('txtInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') searchText(); });
$('btnReveal').onclick = revealSelected;
$('btnOpen').onclick = openSelected;

$('openSettings').onclick = openDrawer;
$('modelChip').onclick = openDrawer;
$('closeSettings').onclick = closeDrawer;
$('scrim').onclick = closeDrawer;
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });

$('modelSelect').onchange = (e) => changeModel(e.target.value);
$('btnAddRoot').onclick = () => addRoot($('rootInput').value);
$('rootInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') addRoot($('rootInput').value); });
$('btnReindex').onclick = reindex;
$('btnSavePort').onclick = savePort;
$('btnModelPath').onclick = toggleModelPath;

/* 右上角物理按钮 */
$('topReindex').onclick = () => { reindex(); };
$('topQuit').onclick = quitApp;   // 直接退出，不弹二次确认

$('topk').addEventListener('input', (e) => { $('topkVal').textContent = e.target.value; });
$('minsim').addEventListener('input', (e) => { $('minsimVal').textContent = (+e.target.value).toFixed(2); });

/* ----------------------------- first-run onboarding ----------------------------- */
function maybeOnboard() {
  let seen = false;
  try { seen = localStorage.getItem('imgsearch_onboarded') === '1'; } catch (_) { /* ignore */ }
  if (!seen) $('onbo').classList.add('is-open');
}
$('onboStart').onclick = () => {
  try { localStorage.setItem('imgsearch_onboarded', '1'); } catch (_) { /* ignore */ }
  $('onbo').classList.remove('is-open');
  // 库为空的新用户：顺手打开设置，引导添加图库
  if (!state.pending || !state.pending.total_files) openDrawer();
};

setMode('img');
loadState().then(maybeOnboard).catch((e) => { toast('初始化失败：' + e); maybeOnboard(); });
