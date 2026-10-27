"""焊接图网页模板（make_solder_map.py 填数据）。占位符：__TITLE__ __NOTE__ __VB__ __CX__ __OUTLINE__ __SILKTOP__ __SILKBOT__ __DATA__ __NOTES__"""

TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f6f5f1;--fg:#1d1d1b;--muted:#6b6a64;--card:#fff;--line:#dcdad3;--pcb:#0f4d2c;--silk:#f3f1e8;--pad:#c9a646;--hl:#e8483b;--done:#9a9890}
@media (prefers-color-scheme: dark){:root{--bg:#161614;--fg:#ecebe6;--muted:#9a9890;--card:#1f1f1c;--line:#34332f;--pcb:#0d3d24;--silk:#e9e6da;--pad:#b8963c;--hl:#ff6a5c;--done:#6b6a64}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,"Microsoft YaHei",sans-serif}
header{padding:10px 16px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center}
h1{font-size:17px;margin:0}.note{color:var(--muted);font-size:13px;flex-basis:100%}
.btn{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:4px 10px;border-radius:6px;cursor:pointer}
.btn.on{background:var(--fg);color:var(--bg)}
main{display:grid;grid-template-columns:minmax(0,3fr) minmax(300px,2fr);height:calc(100vh - 62px)}
@media (max-width:820px){main{grid-template-columns:1fr;height:auto}#view{height:60vh}}
#view{background:var(--pcb);position:relative;overflow:hidden}svg{width:100%;height:100%}
.ol{fill:none;stroke:#ffd84a;stroke-linecap:round}.olf{fill:none}
.st,.sb{fill:none;stroke:var(--silk);stroke-linecap:round;stroke-linejoin:round;opacity:.85}.stf,.sbf{fill:var(--silk);opacity:.85}
.pad{fill:var(--pad);opacity:.9}.pad.hole{stroke:#000;stroke-opacity:.35;stroke-width:.15}
.pad.p1{fill:#e2c25a}.pad.dim{opacity:.25}.pad.sel{fill:var(--hl);opacity:1}
.box{fill:none;stroke:var(--hl);stroke-width:.35;stroke-dasharray:1 .6}
#list{overflow:auto;border-left:1px solid var(--line)}
.grp{display:grid;grid-template-columns:22px 1fr auto;gap:2px 8px;padding:8px 12px;border-bottom:1px solid var(--line);cursor:pointer}
.grp:hover{background:var(--card)}.grp.act{background:var(--card);box-shadow:inset 3px 0 0 var(--hl)}
.grp .v{font-weight:600}.grp .d{grid-column:2;color:var(--muted);font-size:12.5px;word-break:break-all}
.grp .m{grid-column:2;color:var(--muted);font-size:12px}
.grp.done .v,.grp.done .d{color:var(--done);text-decoration:line-through}
.grp.skip{opacity:.55}.tag{font-size:11px;border:1px solid var(--line);border-radius:4px;padding:0 4px;margin-left:6px;color:var(--muted)}
.grp .loc{grid-column:2;font-size:12.5px}.cell{display:inline-block;font-weight:700;border:1px solid var(--fg);border-radius:4px;padding:0 5px;margin-right:4px}
.loc .warn{color:var(--hl)}.loc .q{color:var(--muted)}
.ov{padding:10px 12px;border-bottom:1px solid var(--line);font-size:13px;line-height:1.6}
.blk{padding:7px 12px;border-bottom:1px solid var(--line);cursor:pointer}.blk:hover{background:var(--card)}
.blk.act{background:var(--card);box-shadow:inset 3px 0 0 var(--hl)}.blk .bn{font-weight:600}.blk .bc{color:var(--muted);font-size:12px;margin-left:6px}
.blk .bt,.grp .ex{display:none;font-size:13px;line-height:1.6;margin-top:4px;white-space:pre-wrap}
.blk.act .bt{display:block}.grp.act .ex{display:block;grid-column:2}
.tips{display:block;margin-top:4px;color:var(--hl)}.ex .pd{display:block}.ex .pd b{font-weight:600}
.chip{display:inline-block;font-size:12px;border:1px solid var(--hl);color:var(--hl);border-radius:10px;padding:0 7px;margin:4px 4px 0 0;cursor:pointer}
.sec.tg{cursor:pointer}
.th{grid-column:3;grid-row:1/span 3;width:80px;height:80px;object-fit:contain;background:#fff;border:1px solid var(--line);border-radius:4px;cursor:zoom-in}
.idn{grid-column:2;font-size:12.5px;color:var(--muted)}.band{display:inline-block;width:14px;height:14px;border-radius:2px;border:1px solid #0006;vertical-align:-2px;margin-right:2px}
#pic{position:fixed;inset:0;background:#000b;display:none;align-items:center;justify-content:center;z-index:9;cursor:zoom-out}#pic img{max-width:90vw;max-height:90vh;background:#fff;border-radius:6px}
.sec{padding:6px 12px;font-size:12px;color:var(--muted);background:var(--bg);position:sticky;top:0;border-bottom:1px solid var(--line)}
#tip{position:absolute;left:8px;bottom:8px;background:rgba(0,0,0,.6);color:#fff;padding:3px 8px;border-radius:4px;font-size:12px}
</style></head><body>
<header><h1>__TITLE__</h1>
<button class="btn on" id="bTop">正面（顶层）</button><button class="btn" id="bBot">背面（底层，镜像）</button>
<button class="btn" id="bSort">按格子排</button><span id="prog" style="color:var(--muted)"></span>
<div class="note">点右侧一行：板上对应位置变红。勾选＝这一组焊完了（存在本机浏览器里）。方焊盘/偏亮的焊盘是 1 脚。方框里是元件柜格子（“按格子排”可以一格一格取料）。点开一行能看到每个元件的作用；最上面“电路说明”讲每一块电路的原理，点一块板上就高亮那一块；点板上的焊盘会跳到它那一行。__NOTE__</div></header>
<main><div id="view"><svg id="svg" viewBox="__VB__">
<g id="flip"><g id="silkB">__SILKBOT__</g><g id="silkT">__SILKTOP__</g><g>__OUTLINE__</g><g id="pads"></g><g id="boxes"></g></g>
</svg><div id="tip">滚轮缩放，拖动平移</div></div><div id="list"></div></main><div id="pic"><img alt=""></div>
<script>
const D = __DATA__, N = __NOTES__, NS = 'http://www.w3.org/2000/svg', KEY = 'solder:' + D.board;
// 电路分块：每块做成和料组一样的 {des, side} 对象，选中时板上高亮
const BLOCKS = N ? N.blocks.map(b => ({...b, des: b.refs, side: [...new Set(b.refs.map(r => (D.parts[r] || {}).side).filter(Boolean))]})) : [];
const blocksOf = des => BLOCKS.filter(b => b.refs.includes(des));
let done = {}; try { done = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
let side = 'T', active = null;
const padsG = document.getElementById('pads'), boxesG = document.getElementById('boxes');
const padEls = {};
for (const [des, p] of Object.entries(D.parts)) {
  padEls[des] = [];
  const minN = p.pads.reduce((m, q) => (/^\d+$/.test(q.n) && (m === null || +q.n < m)) ? +q.n : m, null);
  for (const q of p.pads) {
    const e = document.createElementNS(NS, q.s === 'C' || q.s === 'E' ? 'ellipse' : 'rect');
    if (e.tagName === 'ellipse') { e.setAttribute('cx', q.x); e.setAttribute('cy', q.y); e.setAttribute('rx', q.w / 2); e.setAttribute('ry', q.h / 2); }
    else { e.setAttribute('x', q.x - q.w / 2); e.setAttribute('y', q.y - q.h / 2); e.setAttribute('width', q.w); e.setAttribute('height', q.h); }
    if (q.a) e.setAttribute('transform', `rotate(${-q.a} ${q.x} ${q.y})`);
    e.setAttribute('class', 'pad' + (q.th ? ' hole' : '') + (+q.n === minN && p.pads.length > 1 ? ' p1' : ''));
    e.dataset.side = q.th ? 'B' : q.l; const t = document.createElementNS(NS, 'title'); t.textContent = des + '.' + q.n + (q.net ? ' ' + q.net : '') + (N && N.parts[des] ? ' — ' + N.parts[des] : ''); e.appendChild(t); e.dataset.des = des;
    padsG.appendChild(e); padEls[des].push(e);
  }
}
function render() {
  document.getElementById('flip').setAttribute('transform', side === 'B' ? 'translate(__CX__,0) scale(-1,1)' : '');
  document.getElementById('silkT').style.display = side === 'T' ? '' : 'none';
  document.getElementById('silkB').style.display = side === 'B' ? '' : 'none';
  bTop.classList.toggle('on', side === 'T'); bBot.classList.toggle('on', side === 'B');
  for (const [des, els] of Object.entries(padEls)) for (const e of els) e.style.display = (e.dataset.side === 'B' || e.dataset.side === side) ? '' : 'none';
  const sel = new Set(active ? active.des : []);
  boxesG.innerHTML = '';
  for (const [des, els] of Object.entries(padEls)) for (const e of els) { e.classList.toggle('sel', sel.has(des)); e.classList.toggle('dim', !!active && !sel.has(des)); }
  for (const des of sel) { const p = D.parts[des]; if (!p || !p.pads.length) continue;
    const xs = p.pads.map(q => q.x), ys = p.pads.map(q => q.y), m = 1.2;
    const r = document.createElementNS(NS, 'rect'); r.setAttribute('class', 'box');
    r.setAttribute('x', Math.min(...xs) - m); r.setAttribute('y', Math.min(...ys) - m);
    r.setAttribute('width', Math.max(...xs) - Math.min(...xs) + 2 * m); r.setAttribute('height', Math.max(...ys) - Math.min(...ys) + 2 * m); boxesG.appendChild(r); }
  const hand = D.groups.filter(g => !g.smt && !g.dnp), fin = hand.filter(g => done[g.des.join(',')]).length;
  document.getElementById('prog').textContent = `手焊 ${fin}/${hand.length} 组`;
}
bTop.onclick = () => { side = 'T'; render(); }; bBot.onclick = () => { side = 'B'; render(); };
const list = document.getElementById('list');
function sec(t) { const s = document.createElement('div'); s.className = 'sec'; s.textContent = t; list.appendChild(s); }
// 格子编号排序：A01前 < A01后 < … < AL6后 < B01前 …，库外的（层架、大盒子）和没找到的排最后
function cellKey(c) { const m = /^([AB])(L?)(\d+)(前|后)$/.exec(c || ''); return m ? [m[1], m[2], m[3].padStart(2, '0'), m[4] === '前' ? 0 : 1].join('') : 'zz' + (c || '~'); }
const firstCell = g => (g.loc && g.loc.cells.length) ? g.loc.cells.slice().sort((a, b) => cellKey(a) < cellKey(b) ? -1 : 1)[0] : '';
let byCell = false; try { byCell = localStorage.getItem('solder:byCell') === '1'; } catch (e) {}
function locLine(g) {
  const el = document.createElement('div'); el.className = 'loc';
  if (!g.loc) { el.innerHTML = '<span class="warn">库里没找到这个料</span>'; return el; }
  for (const c of g.loc.cells) { const b = document.createElement('span'); b.className = 'cell'; b.textContent = c; el.appendChild(b); }
  const need = g.des.length * D.copies, st = g.loc.stock;
  const q = document.createElement('span');
  q.className = st && st < need ? 'warn' : 'q';
  q.textContent = st ? ` 库存 ${st}${st < need ? `，不够（${D.copies > 1 ? `做 ${D.copies} 块` : '这块板'}要 ${need}）` : ''}` : ' 库存数量没记';
  el.appendChild(q);
  if (g.loc.how !== 'C' && g.loc.how !== '型号') {
    const w = document.createElement('span'); w.className = 'q';
    w.textContent = `（${g.loc.how === '数值' ? '按数值找的同规格料' : '同系列型号'}：${g.loc.names.join('、')}，焊前核对）`; el.appendChild(w);
  }
  return el;
}
let notesOpen = true; try { notesOpen = localStorage.getItem('solder:notes') !== '0'; } catch (e) {}
function select(obj, el) {
  active = active === obj ? null : obj;
  document.querySelectorAll('.grp.act,.blk.act').forEach(x => x.classList.remove('act'));
  if (active && el) el.classList.add('act');
  if (active) { const s = new Set(active.side); if (!s.has(side) && s.size === 1) side = [...s][0]; }
  render();
}
function buildNotes() {
  const h = document.createElement('div'); h.className = 'sec tg'; h.textContent = (notesOpen ? '▾ ' : '▸ ') + '电路说明（点一块看原理，板上高亮这一块）';
  h.onclick = () => { notesOpen = !notesOpen; try { localStorage.setItem('solder:notes', notesOpen ? '1' : '0'); } catch (e) {} buildList(); };
  list.appendChild(h);
  if (!notesOpen) return;
  const ov = document.createElement('div'); ov.className = 'ov'; ov.textContent = N.overview; list.appendChild(ov);
  for (const b of BLOCKS) {
    const el = document.createElement('div'); el.className = 'blk' + (active === b ? ' act' : ''); el.id = 'blk-' + BLOCKS.indexOf(b);
    const n = document.createElement('div'); n.innerHTML = '<span class="bn"></span><span class="bc"></span>';
    n.firstChild.textContent = b.name; n.lastChild.textContent = `${b.refs.length} 个元件`;
    const t = document.createElement('div'); t.className = 'bt'; t.textContent = b.text;
    if (b.tips) { const tp = document.createElement('span'); tp.className = 'tips'; tp.textContent = '焊接 / 上电注意：' + b.tips; t.appendChild(tp); }
    el.append(n, t); el.onclick = () => select(b, el); list.appendChild(el);
  }
}
function partNotes(g) {
  const ex = document.createElement('div'); ex.className = 'ex';
  const byText = new Map();
  for (const d of g.des) { const t = N.parts[d] || ''; if (!byText.has(t)) byText.set(t, []); byText.get(t).push(d); }
  for (const [t, ds] of byText) { if (!t) continue; const p = document.createElement('span'); p.className = 'pd'; p.innerHTML = '<b></b>：'; p.firstChild.textContent = ds.join(' '); p.append(t); ex.appendChild(p); }
  for (const b of new Set(g.des.flatMap(blocksOf))) {
    const c = document.createElement('span'); c.className = 'chip'; c.textContent = '属于：' + b.name;
    c.onclick = ev => { ev.stopPropagation(); if (!notesOpen) { notesOpen = true; buildList(); } const el = document.getElementById('blk-' + BLOCKS.indexOf(b)); select(b, el); el.scrollIntoView({block: 'nearest'}); };
    ex.appendChild(c);
  }
  return ex;
}
// 帮助认料：直插电阻画五色环（1% 金属膜），直插瓷片给出表面印的三位码，电解提示极性
const COLORS = [['黑', '#111'], ['棕', '#7a4a1e'], ['红', '#d22'], ['橙', '#f80'], ['黄', '#fd0'], ['绿', '#2a2'], ['蓝', '#24d'], ['紫', '#82c'], ['灰', '#888'], ['白', '#fff']];
const MULT = {'-1': ['金', '#c9a646'], '-2': ['银', '#c0c0c0']};
function parseVal(v, unit) {
  const m = new RegExp('([0-9.]+)\\s*([pnuµμmkKMG]?)' + unit).exec(v || ''); if (!m) return null;
  return +m[1] * ({p: 1e-12, n: 1e-9, u: 1e-6, 'µ': 1e-6, 'μ': 1e-6, m: 1e-3, k: 1e3, K: 1e3, M: 1e6, G: 1e9}[m[2]] || 1);
}
function identLine(g) {
  const el = document.createElement('div'); el.className = 'idn'; const fp = g.fp || '';
  if (/^RES-TH/.test(fp)) {
    const r = parseVal(g.val, 'Ω'); if (r === null || r <= 0) return null;
    let e = Math.floor(Math.log10(r)) - 2, n = Math.round(r / 10 ** e);
    if (n >= 1000) { n = Math.round(n / 10); e += 1; }
    const ds = String(n).split('').map(Number), mult = e >= 0 ? COLORS[e] : MULT[e]; if (!mult) return null;
    const bands = [...ds.map(d => COLORS[d]), mult, COLORS[1]];
    el.append('色环（五环 1%）：');
    for (const [name, c] of bands) { const b = document.createElement('span'); b.className = 'band'; b.style.background = c; b.title = name; el.appendChild(b); }
    el.append(' ' + bands.map(b => b[0]).join(' ') + '（棕色误差环和其他环隔得稍远，从另一头开始读）');
    return el;
  }
  if (/^CAP-TH_L/.test(fp)) {
    const c = parseVal(g.val, 'F'); if (c === null) return null;
    const pf = Math.round(c * 1e12);
    let code = pf < 100 ? String(pf) : (() => { const e = Math.floor(Math.log10(pf)) - 1; return String(Math.round(pf / 10 ** e)) + e; })();
    el.textContent = `瓷片/薄膜表面印“${code}”（前两位是数字，第三位是后面跟几个 0，单位 pF）`;
    return el;
  }
  if (/^CAP-TH_BD/.test(fp)) { el.textContent = '电解电容：外壳印着容量和耐压，白条（−）一侧是负极，长脚是正极'; return el; }
  return null;
}
const pic = document.getElementById('pic');
pic.onclick = () => { pic.style.display = 'none'; };
function buildList() {
list.innerHTML = '';
if (N) buildNotes();
let lastSec = null;
const order = D.groups.slice();
if (byCell) order.sort((a, b) => { const ka = (a.smt || a.dnp ? 'zzz' : '') + cellKey(firstCell(a)), kb = (b.smt || b.dnp ? 'zzz' : '') + cellKey(firstCell(b)); return ka < kb ? -1 : ka > kb ? 1 : 0; });
for (const g of order) {
  const kind = g.dnp ? '不焊' : g.smt ? '嘉立创已贴（不用焊）' : byCell ? (firstCell(g) ? '格子 ' + firstCell(g) : '库里没找到') : '自己焊';
  if (kind !== lastSec) { sec(kind); lastSec = kind; }
  const row = document.createElement('div'); row.className = 'grp' + (g.smt || g.dnp ? ' skip' : '');
  const k = g.des.join(','); const cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = !!done[k];
  cb.onclick = ev => { ev.stopPropagation(); done[k] = cb.checked; try { localStorage.setItem(KEY, JSON.stringify(done)); } catch (e) {} row.classList.toggle('done', cb.checked); render(); };
  if (g.smt || g.dnp) cb.disabled = true;
  row.classList.toggle('done', !!done[k]);
  const v = document.createElement('div'); v.className = 'v'; v.textContent = `${g.val || g.comment}  ×${g.des.length}`;
  if (g.side.includes('B') && !g.side.includes('T')) { const t = document.createElement('span'); t.className = 'tag'; t.textContent = '背面'; v.appendChild(t); }
  const d = document.createElement('div'); d.className = 'd'; d.textContent = g.des.join('  ');
  const m = document.createElement('div'); m.className = 'm'; m.textContent = [g.mpn, g.fp, g.sup].filter(Boolean).join(' · ');
  row.append(cb, v, d, m);
  if (g.loc && g.loc.img) {
    const im = document.createElement('img'); im.className = 'th'; im.loading = 'lazy'; im.alt = ''; im.title = "立创商品实拍（坐标纸格子 1 mm），点开看大图";
    im.src = g.loc.img.replace('/900x900/', '/224x224/');
    im.onerror = () => im.remove();
    im.onclick = ev => { ev.stopPropagation(); pic.firstChild.src = g.loc.img; pic.style.display = 'flex'; };
    row.appendChild(im);
  }
  if (D.hasLoc && !g.smt && !g.dnp) row.appendChild(locLine(g));
  if (!g.smt && !g.dnp) { const idn = identLine(g); if (idn) row.appendChild(idn); }
  if (N) row.appendChild(partNotes(g));
  row.id = 'grp-' + D.groups.indexOf(g);
  row.onclick = () => select(g, row);
  if (active === g) row.classList.add('act');
  list.appendChild(row);
}
bSort.classList.toggle('on', byCell);
}
bSort.style.display = D.hasLoc ? '' : 'none';
bSort.title = '格子数据来自 Part-DB，' + D.when + ' 生成';
bSort.onclick = () => { byCell = !byCell; try { localStorage.setItem('solder:byCell', byCell ? '1' : '0'); } catch (e) {} buildList(); };
buildList();
const svg = document.getElementById('svg'); let vb = svg.getAttribute('viewBox').split(' ').map(Number), drag = null;
svg.addEventListener('wheel', e => { e.preventDefault(); const r = svg.getBoundingClientRect(), f = e.deltaY > 0 ? 1.15 : 1 / 1.15;
  const px = vb[0] + (e.clientX - r.left) / r.width * vb[2], py = vb[1] + (e.clientY - r.top) / r.height * vb[3];
  vb = [px - (px - vb[0]) * f, py - (py - vb[1]) * f, vb[2] * f, vb[3] * f]; svg.setAttribute('viewBox', vb.join(' ')); }, {passive: false});
svg.addEventListener('pointerdown', e => { drag = [e.clientX, e.clientY, vb[0], vb[1]]; svg.setPointerCapture(e.pointerId); });
svg.addEventListener('pointermove', e => { if (!drag) return; const r = svg.getBoundingClientRect();
  vb[0] = drag[2] - (e.clientX - drag[0]) / r.width * vb[2]; vb[1] = drag[3] - (e.clientY - drag[1]) / r.height * vb[3]; svg.setAttribute('viewBox', vb.join(' ')); });
svg.addEventListener('pointerup', e => {
  const moved = drag && Math.hypot(e.clientX - drag[0], e.clientY - drag[1]) > 4; drag = null;
  if (moved) return;
  const hit = document.elementsFromPoint(e.clientX, e.clientY).find(x => x.dataset && x.dataset.des);  // 点焊盘：跳到它那一行
  const g = hit && D.groups.find(q => q.des.includes(hit.dataset.des));
  if (!g) return;
  const el = document.getElementById('grp-' + D.groups.indexOf(g));
  if (active !== g) select(g, el);
  el.scrollIntoView({block: 'nearest'});
});
render();
</script></body></html>'''
