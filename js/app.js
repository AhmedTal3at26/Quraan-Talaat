/* =========================================================================
   مصحف الخطاط طلعت فتحي محمد — القارئ
   ========================================================================= */
import { QuranData, toArabicDigits } from './data.js';
import { PageSource } from './pagesource.js';

/* ------------------------------------------------------------------ state */
const LS = { pos:'qt.position', marks:'qt.bookmarks', cfg:'qt.settings' };
const defaults = {
  layout:'single', dir:'rtl', gap:10, bright:100,
  mode:'image', keys:true, theme:'dark',
  reciter:'Alafasy_128kbps'
};

const RECITERS = [
  ['Alafasy_128kbps', 'مشاري العفاسي'],
  ['Husary_128kbps', 'محمود خليل الحصري'],
  ['Minshawy_Murattal_192kbps', 'محمد صديق المنشاوي (مرتّل)'],
  ['Abdul_Basit_Murattal_192kbps', 'عبد الباسط عبد الصمد (مرتّل)'],
  ['Sudais_128kbps', 'عبد الرحمن السديس'],
  ['Shatri_128kbps', 'أبو بكر الشاطري'],
  ['Menshawi_16kbps', 'المنشاوي (مجوّل)']
];

const PAGE_AR = 701.575/488.976;
const S = {
  data:null, src:null, pages:[], cur:0,
  cfg:{ ...defaults }, marks:[],
  fit:1, scale:1, zoom:1, tx:0, ty:0,
  holds:new Map(), pending:new Set(), stripBuilt:false
};

const $ = id => document.getElementById(id);
const el = {
  spread:$('spread'), viewport:$('viewport'), loader:$('loader'),
  pageTitle:$('pageTitle'), pageSub:$('pageSub'),
  pageInput:$('pageInput'), pageTotal:$('pageTotal'),
  drawer:$('drawer'), scrim:$('scrim'),
  surahList:$('surahList'), juzList:$('juzList'), marksList:$('marksList'), surahFilter:$('surahFilter'),
  strip:$('strip'), stripTrack:$('stripTrack'),
  searchSheet:$('searchSheet'), searchInput:$('searchInput'), searchResults:$('searchResults'),
  settingsSheet:$('settingsSheet'), btnBookmark:$('btnBookmark'),
  audioBar:$('audioBar'), audioTitle:$('audioTitle'), audioSub:$('audioSub')
};

/* -------------------------------------------------------------- utilities */
const clamp = (v,a,b)=>Math.max(a,Math.min(b,v));
function loadLS(k,f){ try{ const v=localStorage.getItem(k); return v?JSON.parse(v):f; }catch{ return f; } }
function saveLS(k,v){ try{ localStorage.setItem(k,JSON.stringify(v)); }catch{} }
function openSheet(n){ n.classList.add('is-open'); n.setAttribute('aria-hidden','false'); el.scrim.hidden=false; }
function closeSheet(n){ n.classList.remove('is-open'); n.setAttribute('aria-hidden','true');
  if(!document.querySelector('.drawer.is-open')) el.scrim.hidden=true; }
function closeDrawer(){ el.drawer.classList.remove('is-open'); el.drawer.setAttribute('aria-hidden','true'); el.scrim.hidden=true; }
const esc = t => String(t).replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

/* ================================================================== AUDIO */
const A = { el:null, cur:null, playing:false };
function initAudio(){
  A.el = new Audio();
  A.el.preload = 'none';
  A.el.addEventListener('ended', ()=> setPlayIcon(false));
  A.el.addEventListener('pause', ()=> setPlayIcon(false));
  A.el.addEventListener('play',  ()=> setPlayIcon(true));

  const sel = $('setReciter');
  sel.replaceChildren(...RECITERS.map(([id, name])=>{
    const o = document.createElement('option');
    o.value = id; o.textContent = name;
    return o;
  }));
  sel.value = S.cfg.reciter;
  sel.addEventListener('change', ()=>{
    S.cfg.reciter = sel.value; saveLS(LS.cfg, S.cfg);
    if (A.cur) playAyah(A.cur.s, A.cur.a, A.cur.offset);
  });

  $('btnPlayPause').addEventListener('click', ()=>{
    if (!A.el.src) return;
    if (A.el.paused) A.el.play().catch(()=>{}); else A.el.pause();
  });
  $('btnAudioClose').addEventListener('click', ()=>{ A.el.pause(); el.audioBar.hidden = true; });
}
function setPlayIcon(playing){
  A.playing = playing;
  $('btnPlayPause').classList.toggle('is-playing', playing);
}
function playAyah(s, a, offset){
  const n = (x, w) => String(x).padStart(w, '0');
  A.el.src = `https://everyayah.com/data/${S.cfg.reciter}/${n(s,3)}${n(a,3)}.mp3`;
  A.el.play().catch(()=>{});
  A.cur = { s, a, offset };
  const sa = S.data.fromGlobal(S.data.global(s, a));
  el.audioTitle.textContent = S.data.verse(s, a).replace(/[\u0610-\u061A\u064B-\u065F\u0670]/g,'');
  el.audioSub.textContent = `سورة ${S.data.surahName(s)} · الآية ${toArabicDigits(a)}`;
  el.audioBar.hidden = false;
  if (offset != null) flashAyah(S.data.locate(s, a).page, offset);
}
/** أقرب زخرفة لنقطة (نسبة من الصفحة) */
function nearestMedallion(pg, nx, ny){
  if (!pg?.meds?.length) return -1;
  let best = -1, bd = 1e9;
  for (let i = 0; i < pg.meds.length; i++){
    const dx = pg.meds[i][0] - nx, dy = pg.meds[i][1] - ny;
    const d = Math.hypot(dx, dy);
    if (d < bd){ bd = d; best = i; }
  }
  return bd < 0.09 ? best : -1;
}

/* ================================================================ BOOT */
async function boot(){
  S.cfg = { ...defaults, ...loadLS(LS.cfg, {}) };
  S.marks = loadLS(LS.marks, []);
  applyTheme(S.cfg.theme);

  el.loader.hidden = false;
  el.loader.innerHTML = '<div class="spinner"></div><p class="loadmsg">جارٍ تحضير المصحف…</p>';

  S.data = await new QuranData().load();
  S.pages = S.data.index.pages;
  S.src = new PageSource(S.cfg.mode);

  el.pageTotal.textContent = toArabicDigits(S.pages.length);
  $('aboutPages').textContent = toArabicDigits(S.pages.length);

  initAudio();
  buildSurahList(); buildJuzList(); buildMarks(); bindEvents(); syncSettingsUI();

  const saved = loadLS(LS.pos, null);
  const start = saved && saved.i > 0 && saved.i < S.pages.length ? saved.i : 0;
  await goTo(start, { replace:true });

  el.loader.hidden = true;
  registerSW();
}

function applyTheme(t){
  document.documentElement.dataset.theme = t;
  const m = document.querySelector('meta[name=theme-color]');
  if (m) m.content = t === 'dark' ? '#14100d' : '#f6efe2';
  saveLS(LS.cfg, S.cfg);
}

/* ============================================================ SPREAD / RENDER */
function spreadIndices(){
  if (S.cfg.layout !== 'spread') return [S.cur];
  const i = S.cur;
  if (i % 2 === 0) return i + 1 < S.pages.length ? [i, i+1] : [i];
  return [i-1, i];
}

function fitScale(){
  const idxs = spreadIndices();
  const vp = el.viewport.getBoundingClientRect();
  if (!vp.width || !vp.height) return 400;
  const w = idxs.length === 2 ? (2 + S.cfg.gap/488.976) : 1;
  return Math.max(80, Math.min((vp.width - 18)/w, (vp.height - 18)/PAGE_AR));
}

function makeHold(){
  const wrap = document.createElement('div');
  wrap.className = 'canvas-wrap is-loading';
  const host = document.createElement('div');
  host.className = 'page-host';
  wrap.appendChild(host);
  return { wrap, host, key:null };
}

async function layout(force){
  S.fit = fitScale();
  S.scale = S.fit * S.zoom;
  const idxs = spreadIndices();
  el.spread.style.setProperty('--gap', S.cfg.gap + 'px');

  for (const [i, h] of [...S.holds]){
    if (!idxs.includes(i)){ h.wrap.remove(); S.holds.delete(i); }
  }
  for (const i of idxs) if (!S.holds.has(i)) S.holds.set(i, makeHold());
  applyTransform();

  for (const i of idxs) await renderHold(i, force);
  // الترتيب الطبيعي: الصفحة الأولى تقع على اليمين في اتجاه RTL
  for (const i of idxs) el.spread.appendChild(S.holds.get(i).wrap);
  updateMeta();
}

async function renderHold(i, force){
  const hold = S.holds.get(i);
  if (!hold || S.pending.has(i)) return;
  const pg = S.pages[i];
  const key = S.cfg.mode + '|' + S.cfg.bright;
  if (!force && hold.key === key) return;
  S.pending.add(i);
  hold.wrap.classList.add('is-loading');
  hold.host.replaceChildren();
  try{
    hold.wrap.style.width = S.scale + 'px';
    hold.wrap.style.height = (S.scale * PAGE_AR) + 'px';
    await S.src.show(hold.host, pg, i);
    hold.host.style.filter = `brightness(${S.cfg.bright}%)`;
    hold.key = key;
  } catch(err){
    console.error('render', i, err);
    hold.host.innerHTML = '<div class="page-err">تعذّر عرض الصفحة</div>';
  } finally {
    hold.wrap.classList.remove('is-loading');
    S.pending.delete(i);
  }
}

function applyTransform(){ el.spread.style.transform = `translate(${S.tx}px, ${S.ty}px)`; }

let rafPending = false;
function scheduleRerender(){
  if (rafPending) return;
  rafPending = true;
  requestAnimationFrame(async ()=>{
    rafPending = false;
    S.scale = S.fit * S.zoom;
    for (const i of spreadIndices()) await renderHold(i, true);
  });
}

/* ============================================================ ZOOM / PAN */
const pointers = new Map();
let pinchStart = null, downPos = null;

el.viewport.addEventListener('pointerdown', e=>{
  try{ el.viewport.setPointerCapture(e.pointerId); }catch{}
  pointers.set(e.pointerId, { x:e.clientX, y:e.clientY });
  downPos = { x:e.clientX, y:e.clientY, t:Date.now() };
  if (pointers.size === 2){
    const [a,b] = [...pointers.values()];
    pinchStart = { d:Math.hypot(a.x-b.x, a.y-b.y), zoom:S.zoom };
  }
});
el.viewport.addEventListener('pointermove', e=>{
  if (!pointers.has(e.pointerId)) return;
  const prev = pointers.get(e.pointerId);
  pointers.set(e.pointerId, { x:e.clientX, y:e.clientY });
  if (pointers.size === 2 && pinchStart){
    const [a,b] = [...pointers.values()];
    const d = Math.hypot(a.x-b.x, a.y-b.y);
    if (pinchStart.d > 4) setZoom(pinchStart.zoom * (d/pinchStart.d));
    return;
  }
  if (pointers.size === 1 && S.zoom > 1.01){
    S.tx += e.clientX - prev.x; S.ty += e.clientY - prev.y;
    applyTransform();
  }
});
function endPointer(e){
  if (downPos && pointers.size === 1){
    const dx = e.clientX - downPos.x, dy = e.clientY - downPos.y;
    if (Date.now() - downPos.t < 400 && Math.hypot(dx,dy) < 6 && S.zoom <= 1.05){
      onPageTap(e);
    }
  }
  pointers.delete(e.pointerId);
  if (pointers.size < 2) pinchStart = null;
  if (!pointers.size) downPos = null;
}
el.viewport.addEventListener('pointerup', endPointer);
el.viewport.addEventListener('pointercancel', e=>{ pointers.delete(e.pointerId); downPos = null; });

/** نقرة على الصفحة: تشغيل أقرب آية إن كان الاستماع مفعّلًا */
function onPageTap(e){
  const target = e.target.closest?.('.canvas-wrap');
  if (!target) return;
  const hold = [...S.holds.values()].find(h => h.wrap === target);
  if (!hold) return;
  const r = target.getBoundingClientRect();
  const nx = (e.clientX - r.left) / r.width;
  const ny = (e.clientY - r.top) / r.height;
  const idx = spreadIndices().find(i => S.holds.get(i)?.wrap === target);
  if (idx == null) return;
  const pg = S.pages[idx];
  const k = nearestMedallion(pg, nx, ny);
  if (k < 0) return;
  const sa = S.data.fromGlobal(pg.g + k);
  playAyah(sa.s, sa.a, null);
}

el.viewport.addEventListener('wheel', e=>{
  e.preventDefault();
  if (e.ctrlKey || e.metaKey) setZoom(S.zoom * (e.deltaY < 0 ? 1.12 : 1/1.12), e.clientX, e.clientY);
  else { S.tx -= e.deltaX; S.ty -= e.deltaY; applyTransform(); }
}, { passive:false });

function setZoom(z, cx, cy){
  z = clamp(z, 1, 4);
  const vp = el.viewport.getBoundingClientRect();
  const px = cx ?? vp.width/2, py = cy ?? vp.height/2;
  const rect = el.spread.getBoundingClientRect();
  const ox = px - rect.left, oy = py - rect.top;
  const k = z / S.zoom;
  S.tx = (rect.left - vp.left) + ox*(1-k);
  S.ty = (rect.top - vp.top) + oy*(1-k);
  S.zoom = z;
  scheduleRerender();
}
el.viewport.addEventListener('dblclick', e=> setZoom(S.zoom > 1.3 ? 1 : 2.2, e.clientX, e.clientY));

let touchStart = null;
el.viewport.addEventListener('touchstart', e=>{
  if (e.touches.length === 1) touchStart = { x:e.touches[0].clientX, y:e.touches[0].clientY, t:Date.now() };
}, { passive:true });
el.viewport.addEventListener('touchend', e=>{
  if (!touchStart || S.zoom > 1.05){ touchStart = null; return; }
  const t = e.changedTouches[0];
  const dx = t.clientX - touchStart.x, dy = t.clientY - touchStart.y;
  if (Date.now() - touchStart.t < 700 && Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy)*1.6){
    const forward = S.cfg.dir === 'rtl' ? dx < 0 : dx > 0;
    forward ? goTo(S.cur+1) : goTo(S.cur-1);
  }
  touchStart = null;
}, { passive:true });

/* ================================================================ NAVIGATION */
async function goTo(i, opts = {}){
  i = clamp(i, 0, S.pages.length-1);
  S.cur = i;
  S.zoom = 1; S.tx = 0; S.ty = 0;
  await layout(!!opts.force);
  saveLS(LS.pos, { i, v:S.pages[i].v, p:S.pages[i].p, t:Date.now() });
  if (!opts.silent) el.strip.hidden = false;
}

function updateMeta(){
  const pg = S.pages[S.cur];
  if (!pg) return;
  el.pageTitle.textContent = S.data.juzName(S.data.juzOf(pg.s, pg.a));
  const last = S.data.fromGlobal(pg.g + pg.n - 1);
  const same = (last.s === pg.s);
  const range = (same && last.a === pg.a)
      ? `الآية ${toArabicDigits(pg.a)}`
      : `الآيات ${toArabicDigits(pg.a)} – ${toArabicDigits(last.a)}`;
  const tail = same ? '' : ` (حتى ${toArabicDigits(last.a)} من ${S.data.surahName(last.s)})`;
  el.pageSub.textContent = `سورة ${S.data.surahName(pg.s)} · ${range}${tail} · صفحة ${toArabicDigits(S.cur+1)}`;
  el.pageInput.value = String(S.cur+1);
  el.pageInput.max = String(S.pages.length);
  updateBookmarkBtn();
  highlightThumb();
}

/* ================================================================== STRIP */
function buildStrip(){
  if (S.stripBuilt) return;
  S.stripBuilt = true;
  const frag = document.createDocumentFragment();
  const a = Math.max(0, S.cur - 8), b = Math.min(S.pages.length, S.cur + 10);
  for (let i = a; i < b; i++){
    const d = document.createElement('div');
    d.className = 'thumb'; d.dataset.i = i;
    const im = document.createElement('img');
    im.loading = 'lazy'; im.alt = '';
    const tag = document.createElement('span');
    tag.className = 'tag'; tag.textContent = toArabicDigits(i+1);
    d.append(im, tag);
    d.addEventListener('click', ()=>goTo(i));
    S.src.loadImage(i, false).then(x=>{ im.src = x.src; }).catch(()=>{});
    frag.appendChild(d);
  }
  el.stripTrack.replaceChildren(frag);
}
function highlightThumb(){
  buildStrip();
  el.stripTrack.querySelector('.thumb.is-active')?.classList.remove('is-active');
  const cur = el.stripTrack.querySelector(`[data-i="${S.cur}"]`);
  if (cur){ cur.classList.add('is-active'); cur.scrollIntoView({ block:'nearest', inline:'center' }); }
}

/* ================================================================== INDEX UI */
function buildSurahList(){
  const frag = document.createDocumentFragment();
  for (let n = 1; n <= 114; n++){
    const s = S.data.surah(n);
    const li = document.createElement('li');
    li.dataset.key = `${n} ${s.name} ${s.englishName}`;
    li.innerHTML = `<button>
      <span class="num">${toArabicDigits(n)}</span>
      <span class="lbl"><span class="n">سورة ${esc(S.data.surahName(n))}</span>
      <span class="m">${esc(s.englishNameTranslation || s.englishName)} · ${toArabicDigits(s.numberOfAyahs)} آية</span></span></button>`;
    li.querySelector('button').addEventListener('click', ()=>{
      const i = S.data.surahStartPage(n);
      if (i !== null){ goTo(i); closeDrawer(); }
    });
    frag.appendChild(li);
  }
  el.surahList.replaceChildren(frag);
  el.surahFilter.addEventListener('input', e=>{
    const q = e.target.value.trim();
    for (const li of el.surahList.children) li.style.display = (!q || li.dataset.key.includes(q)) ? '' : 'none';
  });
}

function buildJuzList(){
  const frag = document.createDocumentFragment();
  for (const j of S.data.juz){
    const r = S.data.locate(j.s, j.a);
    const li = document.createElement('li');
    li.innerHTML = `<button>
      <span class="num">${toArabicDigits(j.j)}</span>
      <span class="lbl"><span class="n">${j.name}</span>
      <span class="m">سورة ${esc(S.data.surahName(j.s))} · الآية ${toArabicDigits(j.a)}</span></span></button>`;
    li.querySelector('button').addEventListener('click', ()=>{ if (r){ goTo(r.idx); closeDrawer(); } });
    frag.appendChild(li);
  }
  el.juzList.replaceChildren(frag);
}

function buildMarks(){
  if (!S.marks.length){
    const p = document.createElement('p'); p.className = 'empty';
    p.textContent = 'لا توجد علامات بعد.';
    el.marksList.replaceChildren(p); return;
  }
  const frag = document.createDocumentFragment();
  for (const m of S.marks.slice().reverse()){
    const pg = S.pages[m.i]; if (!pg) continue;
    const li = document.createElement('li');
    li.innerHTML = `<button>
      <span class="num">${toArabicDigits(m.i+1)}</span>
      <span class="lbl"><span class="n">سورة ${esc(S.data.surahName(pg.s))}</span>
      <span class="m">${S.data.juzName(S.data.juzOf(pg.s, pg.a))}</span></span></button>`;
    li.querySelector('button').addEventListener('click', ()=>{ goTo(m.i); closeDrawer(); });
    frag.appendChild(li);
  }
  el.marksList.replaceChildren(frag);
}

function updateBookmarkBtn(){
  el.btnBookmark.setAttribute('aria-pressed', S.marks.some(m=>m.i===S.cur) ? 'true':'false');
}
function toggleMark(){
  const i = S.marks.findIndex(m=>m.i===S.cur);
  if (i >= 0) S.marks.splice(i,1); else S.marks.push({ i:S.cur, t:Date.now() });
  saveLS(LS.marks, S.marks); updateBookmarkBtn(); buildMarks();
}

/* ================================================================== SEARCH */
function highlightText(text, q){
  let out = esc(text);
  if (!q) return out;
  const parts = q.split(/\s+/).filter(Boolean).map(esc).sort((a,b)=>b.length-a.length);
  for (const t of parts) out = out.replace(new RegExp('('+t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','g'), '$1');
  return out.replace(//g,'<mark>').replace(//g,'</mark>');
}
function renderResults(list, q){
  if (!list.length){ el.searchResults.innerHTML = '<p class="empty">لا توجد نتائج</p>'; return; }
  const frag = document.createDocumentFragment();
  for (const r of list){
    const b = document.createElement('button');
    b.className = 'res';
    b.innerHTML = `<span class="ref">سورة ${esc(S.data.surahName(r.s))} · الآية ${toArabicDigits(r.a)}</span>
                   <span class="txt">${highlightText(r.t, q)}</span>`;
    b.addEventListener('click', ()=>{
      const loc = S.data.locate(r.s, r.a);
      if (loc){ closeSheet(el.searchSheet); goTo(loc.idx).then(()=>flashAyah(loc.page, loc.offset)); }
    });
    frag.appendChild(b);
  }
  el.searchResults.replaceChildren(frag);
}

function flashAyah(pg, offset){
  const hold = S.holds.get(pg.i);
  if (!hold || !hold.key || !pg.meds?.length) return;
  const k = clamp(offset, 0, pg.meds.length - 1);
  const [nx, ny] = pg.meds[k];
  const W = hold.wrap.clientWidth, H = hold.wrap.clientHeight;
  const d = document.createElement('div');
  d.className = 'flash';
  d.style.left = (nx*W - W*0.045) + 'px';
  d.style.top  = (ny*H - H*0.028) + 'px';
  d.style.width = W*0.09 + 'px';
  d.style.height = H*0.055 + 'px';
  hold.wrap.appendChild(d);
  setTimeout(()=>d.remove(), 2600);
}

/* =================================================================== EVENTS */
function bindEvents(){
  $('btnMenu').addEventListener('click', ()=>{ el.drawer.classList.add('is-open'); el.drawer.setAttribute('aria-hidden','false'); el.scrim.hidden=false; });
  $('btnCloseDrawer').addEventListener('click', closeDrawer);
  el.scrim.addEventListener('click', ()=>{ closeDrawer(); closeSheet(el.searchSheet); closeSheet(el.settingsSheet); });

  for (const t of document.querySelectorAll('.tab')){
    t.addEventListener('click', ()=>{
      document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('is-active', x===t));
      document.querySelectorAll('.tabpanel').forEach(p=>p.classList.toggle('is-active', p.dataset.panel===t.dataset.tab));
    });
  }

  $('btnNext').addEventListener('click', ()=>goTo(S.cur+1));
  $('btnPrev').addEventListener('click', ()=>goTo(S.cur-1));
  $('btnPageJump').addEventListener('click', jumpToInput);
  el.pageInput.addEventListener('keydown', e=>{ if (e.key==='Enter') jumpToInput(); });

  $('btnTheme').addEventListener('click', ()=>{ S.cfg.theme = S.cfg.theme === 'dark' ? 'light' : 'dark'; applyTheme(S.cfg.theme); });
  el.btnBookmark.addEventListener('click', toggleMark);

  $('btnSearch').addEventListener('click', ()=>{ openSheet(el.searchSheet); setTimeout(()=>el.searchInput.focus(), 220); });
  $('btnCloseSearch').addEventListener('click', ()=>closeSheet(el.searchSheet));
  let sTimer;
  el.searchInput.addEventListener('input', e=>{
    clearTimeout(sTimer);
    const q = e.target.value;
    if (q.trim().length < 2){ el.searchResults.innerHTML = '<p class="empty">اكتب حرفين على الأقل…</p>'; return; }
    sTimer = setTimeout(()=>renderResults(S.data.search(q), q), 180);
  });

  $('btnSettings').addEventListener('click', ()=>{ openSheet(el.settingsSheet); syncSettingsUI(); });
  $('btnCloseSettings').addEventListener('click', ()=>closeSheet(el.settingsSheet));

  $('setLayout').addEventListener('change', e=>{ S.cfg.layout=e.target.value; saveLS(LS.cfg,S.cfg); layout(true); });
  $('setDir').addEventListener('change', e=>{ S.cfg.dir=e.target.value; saveLS(LS.cfg,S.cfg); layout(true); });
  $('setGap').addEventListener('input', e=>{ S.cfg.gap=+e.target.value; saveLS(LS.cfg,S.cfg); layout(true); });
  $('setBright').addEventListener('input', e=>{
    S.cfg.bright=+e.target.value; saveLS(LS.cfg,S.cfg);
    for (const [,h] of S.holds) h.host.style.filter = `brightness(${S.cfg.bright}%)`;
  });
  $('setMode').addEventListener('change', async e=>{
    S.cfg.mode = e.target.value; saveLS(LS.cfg,S.cfg);
    S.src = new PageSource(S.cfg.mode);
    S.stripBuilt = false;
    for (const [,h] of S.holds) h.key = null;
    await layout(true);
  });
  $('setKeys').addEventListener('change', e=>{ S.cfg.keys=e.target.checked; saveLS(LS.cfg,S.cfg); });
  $('btnReset').addEventListener('click', ()=>{
    localStorage.removeItem(LS.pos); localStorage.removeItem(LS.marks);
    S.marks = []; buildMarks(); updateBookmarkBtn();
  });

  document.addEventListener('keydown', e=>{
    if (!S.cfg.keys) return;
    if (['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return;
    const rtl = S.cfg.dir === 'rtl';
    if (e.key === 'ArrowRight') rtl ? goTo(S.cur-1) : goTo(S.cur+1);
    else if (e.key === 'ArrowLeft') rtl ? goTo(S.cur+1) : goTo(S.cur-1);
    else if (e.key === 'PageDown' || e.key === ' '){ e.preventDefault(); goTo(S.cur+1); }
    else if (e.key === 'PageUp'){ e.preventDefault(); goTo(S.cur-1); }
    else if (e.key === 'Home') goTo(0);
    else if (e.key === 'End') goTo(S.pages.length-1);
    else if (e.key === 'Escape'){ closeSheet(el.searchSheet); closeSheet(el.settingsSheet); closeDrawer(); }
  });

  let rz;
  window.addEventListener('resize', ()=>{ clearTimeout(rz); rz = setTimeout(()=>layout(true), 200); });
  window.addEventListener('beforeunload', ()=>saveLS(LS.pos, { i:S.cur, t:Date.now() }));

  window.addEventListener('beforeinstallprompt', e=>{ e.preventDefault(); window.__pi = e; $('btnInstall').hidden = false; });
  $('btnInstall').addEventListener('click', async ()=>{ if (window.__pi){ window.__pi.prompt(); window.__pi = null; $('btnInstall').hidden = true; } });
}

function jumpToInput(){
  const n = parseInt(el.pageInput.value, 10);
  if (Number.isFinite(n)) goTo(clamp(n-1, 0, S.pages.length-1));
}
function syncSettingsUI(){
  $('setLayout').value = S.cfg.layout;
  $('setDir').value = S.cfg.dir;
  $('setGap').value = S.cfg.gap;
  $('setBright').value = S.cfg.bright;
  $('setMode').value = S.cfg.mode;
  $('setKeys').checked = S.cfg.keys;
  $('setReciter').value = S.cfg.reciter;
}

/* ====================================================================== PWA */
function registerSW(){
  if ('serviceWorker' in navigator && location.protocol !== 'file:')
    navigator.serviceWorker.register('sw.js').catch(()=>{});
}

window.addEventListener('load', () => {
  boot().catch(err => {
    console.error(err);
    el.loader.hidden = false;
    el.loader.innerHTML = `<div style="padding:24px;text-align:center;color:#e0b8a6;font-size:13px;line-height:2">
      تعذّر تحميل المصحف.<br><span style="color:#b9a58c">${esc(String(err.message || err))}</span></div>`;
  });
});