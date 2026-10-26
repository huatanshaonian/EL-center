"""生成交互式焊接图（单个 HTML，浏览器打开即用，不联网）。

数据只来自各板"制板文件"目录：Gerber 压缩包（丝印、板框、飞针表里的焊盘坐标）、BOM_*_全部.csv、
JLC_SMT_CPL_*.csv（嘉立创已贴的位号，标灰）；每组料放在元件柜哪一格、库存多少从 Part-DB 查
（inventory/bom_locate.py，连不上 Part-DB 时不显示格子）。
用法：python make_solder_map.py            生成 BOARDS 里全部板子
      python make_solder_map.py NIXIE-DRV  只生成名字里含该字样的板子
输出：el_driver/焊接图/<板名>.html
"""
import csv
import html
import io
import json
import math
import os
import re
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
ED = os.path.join(ROOT, 'el_driver')
OUT = os.path.join(ED, '焊接图')
MIL = 0.0254
sys.path.insert(0, os.path.join(ROOT, 'inventory'))

# 板名, 目录, 文件标签, Gerber 文件名(不含路径), 不焊位号, 说明
BOARDS = [
    ('EL-IF D1.3', 'D1.3/制板文件', 'EL-IF_D1.3', 'Gerber_EL-IF_D1.3.zip', set(), ''),
    ('PWR-DIST D1.1', 'PWR-DIST_D1/制板文件', 'PWR-DIST_D1.1', 'Gerber_PWR-DIST_D1.1.zip', set(),
     '两个 NID100 插在排母上（每个 1×6 + 1×7，塑高 8.5），装好后用扎带穿长条孔捆住。'),
    ('KBD-ADAPT D1', 'KBD-ADAPT_D1/制板文件', 'KBD-ADAPT_D1', 'Gerber_KBD-ADAPT_D1.zip', set(), ''),
    ('SLANT D1.1', 'SLANT_D1/制板文件', 'SLANT_D1.1', 'Gerber_SLANT_D1.1.zip', set(),
     'Pico 插针装：先焊背面两条 1×20 排母（推子、编码器之前），排针焊在 Pico 上，Pico 芯片面朝外、1 脚对方焊盘。'),
    ('ESP-BASE D1', 'ESP-BASE_D1/制板文件', 'ESP-BASE_D1', 'Gerber_ESP-BASE_D1.zip', {'U1', 'J_EXP'},
     'U1（PCA9555）与 J_EXP 预留不焊；JP_BZ 插跳线帽。'),
    ('HV-UNI D1', 'HV-UNI_D1/制板文件', 'HV-UNI_D1', 'Gerber_HV-UNI_D1.zip', set(),
     '做 3 块。R21/R22 库存件确认不是迷你体；Q1 散热片带高压，套热缩。'),
    ('EYE-6E2 D1.1', 'EYE-6E2_D1/制板文件', 'EYE-6E2_D1.1', 'Gerber_EYE-6E2_D1.1.zip', {'R_HA', 'R_HB'},
     'R_HA/R_HB 灯丝均衡默认不焊（灯丝电压偏差大时才焊一只）；管座用自己的实物管座。'),
    ('GEIGER-MAIN D1', 'GEIGER_D1/制板文件_主板', 'GEIGER-MAIN_D1', 'Gerber_GEIGER-MAIN_D1.zip', set(),
     '首次通电前 VR1 拧到 10 Ω；Q6（S8050）焊前定脚。LS1/LS2 二选一。'),
    ('GEIGER-CLIP D1', 'GEIGER_D1/制板文件_夹子板', 'GEIGER-CLIP_D1', 'Gerber_GEIGER-CLIP_D1.zip', set(), ''),
    ('NIXIE-DRV D1.1', 'NIXIE-DRV_D1/制板文件_驱动板', 'NIXIE-DRV_D1.1', 'Gerber_NIXIE-DRV_D1.1.zip', set(),
     'K155ID1 插在 DIP-16 座上（缺口对丝印缺口）；HV-UNI 小板插 J_HP/J_HH。'),
    ('IN14-SOCK D1', 'NIXIE-DRV_D1/制板文件_IN14小板', 'IN14-SOCK_D1', 'Gerber_IN14-SOCK_D1.zip', {'R_PL'},
     '做 7 块（6 装机 + 1 备）。R_PR 0 Ω 自己焊（或电阻腿短接）；J1 2×7 排针焊在板子底面。'),
    ('IV18 D1', 'IV18_D1/制板文件', 'IV18_D1', 'Gerber_IV18_D1.zip', {'R17', 'R18', 'R19'},
     '贴片件钢网刷锡膏 + 加热台回流（2026-10-23 起不交嘉立创贴）；MAX6921（U1）1 脚对丝印圆点；R17–R19 不焊（тип 2 管）。直插件焊完把板底焊脚剪平到 ≤ 0.8 mm。'),
]

COPIES = {'HV-UNI D1': 3, 'IN14-SOCK D1': 7}  # 要做几块（库存够不够按总数算）
# BOM 里用占位封装代替的器件、或焊的时候换成库存料的：板名 -> {位号: (显示名, 去 Part-DB 查的名字)}
STAND_IN = {'IN14-SOCK D1': {'V1': ('IN-14 辉光管（BOM 里是 1×13 排针占位）', 'IN-14 辉光管')},
            'HV-UNI D1': {'R3': ('20Ω（BOM 写 22Ω；栅极串阻用库存 20Ω 代替，见设计记录）', '固定电阻 20 Ω')}}


# ---------------- Gerber → SVG path ----------------
def gerber_paths(txt):
    """返回 (strokes, flashes, regions)，单位 mm。strokes: [(w, [(x,y)...])]，flashes: [(shape, params, x, y)]"""
    m = re.search(r'%FSLAX(\d)(\d)Y', txt)
    dec = int(m.group(2)) if m else 6
    k = 25.4 if '%MOIN' in txt else 1.0
    sc = 10 ** dec
    aps = {}
    for m in re.finditer(r'%ADD(\d+)([A-Za-z0-9_]+),?([^*%]*)\*%', txt):
        aps[int(m.group(1))] = (m.group(2), [float(v) * k for v in m.group(3).split('X') if v])
    body = re.sub(r'%[^%]*%', '', txt)
    x = y = 0.0
    cur = None
    region = False
    poly = []
    interp = 1
    strokes, flashes, regions = [], [], []
    path = None
    for c in body.split('*'):
        c = c.strip()
        if not c:
            continue
        if c.startswith('G36'):
            region, poly = True, []
            continue
        if c.startswith('G37'):
            if len(poly) > 2:
                regions.append(poly)
            region = False
            continue
        g = re.match(r'G0?([123])', c)
        if g:
            interp = int(g.group(1))
        dm = re.match(r'^D(\d+)$', c) or re.match(r'^G54D(\d+)$', c)
        if dm and int(dm.group(1)) >= 10:
            cur = int(dm.group(1))
            path = None
            continue
        mx = re.search(r'X(-?\d+)', c)
        my = re.search(r'Y(-?\d+)', c)
        if not (mx or my or re.search(r'D0[123]', c)):
            continue
        nx = int(mx.group(1)) / sc * k if mx else x
        ny = int(my.group(1)) / sc * k if my else y
        d = re.search(r'D0?([123])$', c)
        op = int(d.group(1)) if d else 1
        if region:
            if op == 2:
                if len(poly) > 2:
                    regions.append(poly)
                poly = [(nx, ny)]
            else:
                poly.append((nx, ny))
        elif op == 1:
            w = aps.get(cur, ('C', [0.15]))[1]
            w = w[0] if w else 0.15
            if path is None or path[1][-1] != (x, y) or path[0] != w:
                path = (w, [(x, y)])
                strokes.append(path)
            path[1].append((nx, ny))
        elif op == 2:
            path = None
        elif op == 3:
            path = None
            if cur in aps:
                flashes.append((aps[cur][0], aps[cur][1], nx, ny))
        x, y = nx, ny
    return strokes, flashes, regions


def svg_layer(txt, cls):
    strokes, flashes, regions = gerber_paths(txt)
    out = []
    for w, pts in strokes:
        d = 'M' + ' L'.join(f'{a:.3f},{-b:.3f}' for a, b in pts)
        out.append(f'<path class="{cls}" d="{d}" stroke-width="{max(w, 0.08):.3f}"/>')
    for poly in regions:
        d = 'M' + ' L'.join(f'{a:.3f},{-b:.3f}' for a, b in poly) + 'Z'
        out.append(f'<path class="{cls}f" d="{d}"/>')
    for shape, p, fx, fy in flashes:
        if shape == 'C' and p:
            out.append(f'<circle class="{cls}f" cx="{fx:.3f}" cy="{-fy:.3f}" r="{p[0] / 2:.3f}"/>')
        elif shape in ('R', 'O') and len(p) >= 2:
            rx = min(p) / 2 if shape == 'O' else 0
            out.append(f'<rect class="{cls}f" x="{fx - p[0] / 2:.3f}" y="{-fy - p[1] / 2:.3f}" width="{p[0]:.3f}" height="{p[1]:.3f}" rx="{rx:.3f}"/>')
    return '\n'.join(out)


def read_csv(path):
    b = open(path, 'rb').read()
    t = b.decode('utf-16') if b[:2] in (b'\xff\xfe', b'\xfe\xff') else b.decode('utf-8-sig')
    d = '\t' if '\t' in t.split('\n')[0] else ','
    rows = list(csv.reader(io.StringIO(t), delimiter=d))
    h = [x.strip('"') for x in rows[0]]
    return [dict(zip(h, [x.strip('"') for x in r])) for r in rows[1:] if len(r) >= 3]


def build(name, sub, tag, gzip, dnp, note, locator=None):
    base = os.path.join(ED, sub)
    z = zipfile.ZipFile(os.path.join(base, gzip))
    names = z.namelist()
    get = lambda suf: z.read([n for n in names if n.endswith(suf)][0]).decode('latin1')
    probe = json.loads(z.read([n for n in names if 'Flying' in n][0]))
    comps = {r[1]: r for r in probe['components']['rows']}
    pf = probe['pins']['fields']
    pads = {}
    seen = set()
    for r in probe['pins']['rows']:
        p = dict(zip(pf, r))
        des, num = p['PIN_NAME'].rsplit('_', 1) if '_' in p['PIN_NAME'] else (p['PIN_NAME'], '')
        key = (p['PIN_NAME'], round(p['PIN_X'], 2), round(p['PIN_Y'], 2))
        if key in seen:
            continue
        seen.add(key)
        pads.setdefault(des, []).append({
            'n': num, 'x': round(p['PIN_X'] * MIL, 3), 'y': round(-p['PIN_Y'] * MIL, 3),
            'w': round(p['PAD_SIZEX'] * MIL, 3), 'h': round(p['PAD_SIZEY'] * MIL, 3),
            'a': p['PAD_ANGLE'] or 0, 's': p['PAD_SHAPE'], 'th': bool(p['HOLE_SIZE']), 'l': p['LAYER'],
            'net': p['NET_NAME']})
    bom = read_csv(os.path.join(base, f'BOM_{tag}_全部.csv'))
    smt = set()
    cplp = os.path.join(base, f'JLC_SMT_CPL_{tag}.csv')
    if os.path.exists(cplp):
        smt = {r['Designator'] for r in read_csv(cplp)}
    groups = []
    for b in bom:
        ds = [d.strip() for d in b.get('Designator', '').split(',') if d.strip()]
        if not ds:
            continue
        val = b.get('Value') or b.get('Comment') or ''
        si = STAND_IN.get(name, {})
        if len(ds) == 1 and ds[0] in si:
            val, real = si[ds[0]]
            b = {'Manufacturer Part': real, 'Comment': val}
        # 同一型号里有的嘉立创贴、有的不焊、有的自己焊时，拆成几行
        for kind in ('hand', 'smt', 'dnp'):
            sub = [d for d in ds if (d in dnp and kind == 'dnp') or (d not in dnp and d in smt and kind == 'smt')
                   or (d not in dnp and d not in smt and kind == 'hand')]
            if not sub:
                continue
            groups.append({
                'val': val, 'comment': b.get('Comment', ''), 'fp': b.get('Footprint', ''),
                'mpn': b.get('Manufacturer Part', ''), 'sup': b.get('Supplier Part', ''),
                'des': sub, 'smt': kind == 'smt', 'dnp': kind == 'dnp',
                'side': sorted({comps[d][2] for d in sub if d in comps}),
                'loc': locator.locate(b) if (locator and kind == 'hand') else None})
    # 手焊在前（按数量多→少），嘉立创已贴、不焊在后
    groups.sort(key=lambda g: (2 if g['dnp'] else 1 if g['smt'] else 0, -len(g['des']), g['val']))
    parts = {d: {'x': round(r[3] * MIL, 3), 'y': round(-r[4] * MIL, 3), 'side': r[2], 'pads': pads.get(d, [])}
             for d, r in comps.items()}
    gko = gerber_paths(get('.GKO'))
    xs = [p[0] for w, pts in gko[0] for p in pts] + [p[0] for poly in gko[2] for p in poly]
    ys = [-p[1] for w, pts in gko[0] for p in pts] + [-p[1] for poly in gko[2] for p in poly]
    vb = (min(xs) - 2, min(ys) - 2, max(xs) - min(xs) + 4, max(ys) - min(ys) + 4)
    layers = {
        'outline': svg_layer(get('.GKO'), 'ol'),
        'top': svg_layer(get('.GTO'), 'st'),
        'bot': svg_layer(get('.GBO'), 'sb'),
    }
    page = TEMPLATE.replace('__TITLE__', html.escape(f'{name} 焊接图')).replace('__NOTE__', html.escape(note)) \
        .replace('__VB__', ' '.join(f'{v:.2f}' for v in vb)).replace('__CX__', f'{vb[0] * 2 + vb[2]:.2f}') \
        .replace('__OUTLINE__', layers['outline']).replace('__SILKTOP__', layers['top']).replace('__SILKBOT__', layers['bot']) \
        .replace('__DATA__', json.dumps({'board': name, 'groups': groups, 'parts': parts, 'hasLoc': bool(locator), 'copies': COPIES.get(name, 1),
                                         'when': time.strftime('%Y-%m-%d %H:%M')}, ensure_ascii=False))
    os.makedirs(OUT, exist_ok=True)
    fn = os.path.join(OUT, f'{tag}.html')
    open(fn, 'w', encoding='utf-8').write(page)
    hand = sum(len(g['des']) for g in groups if not g['smt'] and not g['dnp'])
    print(f'{name}: {fn}  手焊 {hand} 个位号，{len(groups)} 组')


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
.grp{display:grid;grid-template-columns:22px 1fr;gap:2px 8px;padding:8px 12px;border-bottom:1px solid var(--line);cursor:pointer}
.grp:hover{background:var(--card)}.grp.act{background:var(--card);box-shadow:inset 3px 0 0 var(--hl)}
.grp .v{font-weight:600}.grp .d{grid-column:2;color:var(--muted);font-size:12.5px;word-break:break-all}
.grp .m{grid-column:2;color:var(--muted);font-size:12px}
.grp.done .v,.grp.done .d{color:var(--done);text-decoration:line-through}
.grp.skip{opacity:.55}.tag{font-size:11px;border:1px solid var(--line);border-radius:4px;padding:0 4px;margin-left:6px;color:var(--muted)}
.grp .loc{grid-column:2;font-size:12.5px}.cell{display:inline-block;font-weight:700;border:1px solid var(--fg);border-radius:4px;padding:0 5px;margin-right:4px}
.loc .warn{color:var(--hl)}.loc .q{color:var(--muted)}
.sec{padding:6px 12px;font-size:12px;color:var(--muted);background:var(--bg);position:sticky;top:0;border-bottom:1px solid var(--line)}
#tip{position:absolute;left:8px;bottom:8px;background:rgba(0,0,0,.6);color:#fff;padding:3px 8px;border-radius:4px;font-size:12px}
</style></head><body>
<header><h1>__TITLE__</h1>
<button class="btn on" id="bTop">正面（顶层）</button><button class="btn" id="bBot">背面（底层，镜像）</button>
<button class="btn" id="bSort">按格子排</button><span id="prog" style="color:var(--muted)"></span>
<div class="note">点右侧一行：板上对应位置变红。勾选＝这一组焊完了（存在本机浏览器里）。方焊盘/偏亮的焊盘是 1 脚。方框里是元件柜格子（“按格子排”可以一格一格取料）。__NOTE__</div></header>
<main><div id="view"><svg id="svg" viewBox="__VB__">
<g id="flip"><g id="silkB">__SILKBOT__</g><g id="silkT">__SILKTOP__</g><g>__OUTLINE__</g><g id="pads"></g><g id="boxes"></g></g>
</svg><div id="tip">滚轮缩放，拖动平移</div></div><div id="list"></div></main>
<script>
const D = __DATA__, NS = 'http://www.w3.org/2000/svg', KEY = 'solder:' + D.board;
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
    e.dataset.side = q.th ? 'B' : q.l; const t = document.createElementNS(NS, 'title'); t.textContent = des + '.' + q.n + (q.net ? ' ' + q.net : ''); e.appendChild(t);
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
function buildList() {
list.innerHTML = '';
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
  if (D.hasLoc && !g.smt && !g.dnp) row.appendChild(locLine(g));
  row.onclick = () => { active = active === g ? null : g; document.querySelectorAll('.grp.act').forEach(x => x.classList.remove('act')); if (active) row.classList.add('act');
    if (active) { const s = new Set(active.side); if (!s.has(side) && s.size === 1) side = [...s][0]; } render(); };
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
svg.addEventListener('pointerup', () => drag = null);
render();
</script></body></html>'''

if __name__ == '__main__':
    want = sys.argv[1] if len(sys.argv) > 1 else ''
    try:
        from bom_locate import Locator
        loc = Locator()
    except Exception as e:  # 不在家里网络、或没有 token 时照样出图，只是没有格子
        print('Part-DB 连不上，焊接图里不显示格子：', e)
        loc = None
    for b in BOARDS:
        if want in b[0] or want in b[2]:
            build(*b, locator=loc)
