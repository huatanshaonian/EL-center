"""生成交互式焊接图（单个 HTML，浏览器打开即用，不联网）。

数据只来自各板"制板文件"目录：Gerber 压缩包（丝印、板框、飞针表里的焊盘坐标）、BOM_*_全部.csv、
JLC_SMT_CPL_*.csv（嘉立创已贴的位号，标灰）；每组料放在元件柜哪一格、库存多少从 Part-DB 查
（inventory/bom_locate.py，连不上 Part-DB 时不显示格子）；元件作用和电路分块原理来自
el_driver/焊接图/说明/<板名>.json（没有就不显示）。
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

from solder_map_template import TEMPLATE

ROOT = os.path.dirname(os.path.abspath(__file__))
ED = os.path.join(ROOT, 'el_driver')
OUT = os.path.join(ED, '焊接图')
NOTES = os.path.join(OUT, '说明')
MIL = 0.0254
sys.path.insert(0, os.path.join(ROOT, 'inventory'))

# 板名, 目录, 文件标签, Gerber 文件名(不含路径), 不焊位号, 说明
BOARDS = [
    ('EL-IF D1.3', 'D1.3/制板文件', 'EL-IF_D1.3', 'Gerber_EL-IF_D1.3.zip', set(),
     'U1/U2（SN74AHCT245N）插在 DIP-20 座上（座子不在 BOM 里，A10后；先焊座子，缺口对丝印缺口）。'),
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


def load_notes(tag):
    """读这块板的元件/电路说明，没有返回 None。"""
    fn = os.path.join(NOTES, f'{tag}.json')
    if not os.path.exists(fn):
        return None
    with open(fn, encoding='utf-8') as f:
        return json.load(f)


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
    if '__NOTES__' not in page:
        raise RuntimeError('模板缺 __NOTES__')
    page = page.replace('__NOTES__', json.dumps(load_notes(tag), ensure_ascii=False))
    open(fn, 'w', encoding='utf-8').write(page)
    hand = sum(len(g['des']) for g in groups if not g['smt'] and not g['dnp'])
    print(f'{name}: {fn}  手焊 {hand} 个位号，{len(groups)} 组')




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
