"""生成元件柜的抽屉标签和收纳对照表（A4，HTML + PDF）。

  标签：每个抽屉一条（编号 + 前/后格内容），空着的抽屉只印编号；另附同尺寸空白标签手写用。
        小抽屉 35×10 mm，大抽屉 50×14 mm，沿灰线剪开贴在抽屉面上。
  对照表：每一格该放 Part-DB 里的哪些料（含数量、现在的库位），照着一格一格放。
规划本身在 storage_plan.py。用法：G:\\anaconda\\python.exe make_storage_labels.py
输出 inventory/收纳/；PDF 用 Edge 无头模式打印，打印时选“实际大小”（100%）。
"""
import collections
import html
import os
import re
import subprocess
import sys

from partdb_parts import fetch_parts
from storage_plan import BIG, DRAWERS, EXTRA, OUTSIDE, assign, cells
from value_parse import _values

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '收纳')
EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
BLANK_SMALL, BLANK_BIG = 37, 6  # 凑满整行，整页一张 A4

CSS_BASE = """
@page { size: A4; margin: 10mm; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Microsoft YaHei", "SimHei", sans-serif; color: #000; background: #fff; }
h1 { font-size: 10pt; margin: 0 0 2mm; }
.note { font-size: 7pt; color: #444; margin: 0 0 3mm; }
"""

CSS_LABEL = """
.grid { display: inline-grid; vertical-align: top; border-top: 0.2mm solid #999; border-left: 0.2mm solid #999; margin-bottom: 5mm; }
.s { grid-template-columns: repeat(5, 35mm); }
.b { grid-template-columns: repeat(3, 50mm); }
.lab { border-right: 0.2mm solid #999; border-bottom: 0.2mm solid #999; display: flex; align-items: center;
       overflow: hidden; white-space: nowrap; }
.s .lab { width: 35mm; height: 10mm; padding: 0 1mm; }
.b .lab { width: 50mm; height: 14mm; padding: 0 1.5mm; }
.code { font-weight: bold; }
.s .code { font-size: 8pt; width: 7mm; flex: none; }
.b .code { font-size: 10.5pt; width: 11mm; flex: none; }
.rows { display: flex; flex-direction: column; min-width: 0; }
.rows > div { overflow: hidden; }
.s .rows { font-size: 7.5pt; line-height: 4.4mm; }
.b .rows { font-size: 9.5pt; line-height: 6mm; }
.over { outline: 0.6mm solid red; }
.fb { color: #777; margin-right: 0.6mm; }
"""

CSS_GUIDE = """
table { border-collapse: collapse; width: 100%; font-size: 7.5pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 0.2mm solid #999; padding: 0.8mm 1.2mm; vertical-align: top; text-align: left; }
th { background: #eee; }
td.c { white-space: nowrap; font-weight: bold; }
.ex { color: #555; }
h2 { font-size: 9pt; margin: 4mm 0 1.5mm; }
"""


def esc(s):
    return html.escape(s or '')


def label(code, front, back):
    if not code:  # 整格空白，手写用
        return '<div class="lab"></div>'
    return (f'<div class="lab"><div class="code">{esc(code)}</div><div class="rows">'
            f'<div><span class="fb">前</span>{esc(front)}</div><div><span class="fb">后</span>{esc(back)}</div></div></div>')


def labels_html():
    small = [label(d, f, b) for d, (f, b) in DRAWERS.items() if d not in BIG]
    small += [label('', '', '')] * BLANK_SMALL
    big = [label(d, f, b) for d, (f, b) in DRAWERS.items() if d in BIG]
    big += [label('', '', '')] * BLANK_BIG
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>元件柜标签</title>
<style>{CSS_BASE}{CSS_LABEL}</style></head><body>
<h1>元件柜抽屉标签</h1>
<p class="note">打印选“实际大小 / 100%”；沿灰线剪开贴在抽屉面上，可再贴一层透明胶防磨。小抽屉 35×10 mm（A01–A18、B01–B30），
大抽屉 50×14 mm（AL1–AL6）。只印编号的是空着备用的抽屉，后面整格空白的留给手写。</p>
<div class="grid s">{''.join(small)}</div>
<div class="grid b">{''.join(big)}</div>
<script>/* 字超出格子的标签描红，check_overflow() 靠它检查 */
for (const d of document.querySelectorAll('.rows > div'))
  if (d.scrollWidth > d.clientWidth + 1) d.closest('.lab').classList.add('over');
</script>
</body></html>"""


def part_line(p):
    t = p['name']
    if p['desc'] and p['desc'] not in t and not p['desc'].startswith(('五色环', '玻璃封装', '容差', 'TO-92', '数量')):
        t += ' — ' + p['desc'][:28]
    old = sorted({n for _, n in p['lots'] if n})
    old = '' if not old else ('（在途）' if old == ['待入库（在途）'] else f'（现在 {"、".join(old)}）')
    n = p['amount'] or '若干'
    return f'{esc(t)} ×{n}<span class="ex">{esc(old)}</span>'


def guide_html(parts):
    where = collections.defaultdict(list)
    for p in parts:
        where[assign(p) or '未分配'].append(p)
    for v in where.values():  # 同一格里按数值从小到大（电阻、电容、稳压值），认不出数值的排后面
        v.sort(key=lambda p: (min([x for x, _ in _values(p['desc']) or _values(p['name'])] or [float('inf')]), p['name']))
    rows = []
    for cell, d, fb, text in cells():
        items = [part_line(p) for p in where.get(cell, [])]
        if cell in EXTRA:
            items.append(f'<span class="ex">{esc(EXTRA[cell])}</span>')
        if not text and not items:
            continue
        rows.append(f'<tr><td class="c">{cell}</td><td>{esc(text)}</td><td>{"<br>".join(items)}</td></tr>')
    outside = ''.join(
        f'<tr><td class="c">{k}</td><td>{esc(v)}</td><td>{"<br>".join(part_line(p) for p in where.get(k, []))}</td></tr>'
        for k, v in OUTSIDE.items())
    bad = where.get('未分配', [])
    bad_html = f'<h2>没分到格子的（要补规则）</h2><p>{"<br>".join(part_line(p) for p in bad)}</p>' if bad else ''
    empty = [d for d, (f, b) in DRAWERS.items() if not f and not b]
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>收纳对照表</title>
<style>{CSS_BASE}{CSS_GUIDE}</style></head><body>
<h1>元件柜收纳对照表（数据来自 Part-DB，共 {len(parts)} 种）</h1>
<p class="note">一行一格，照“放什么”一栏放进去。旧盒子的三极管 T-01～T-06 整格搬，不用拆。
电阻每个阻值一袋，竖着从小到大排；旧色环电阻袋上没写阻值的先写上。“在途”的料到货后直接放进对应格。
完全空着的抽屉：{"、".join(empty)}。</p>
<table><tr><th>格子</th><th>标签</th><th>放什么</th></tr>{''.join(rows)}</table>
<h2>不进抽屉的</h2>
<table><tr><th>放哪</th><th>放什么</th><th>Part-DB 里的料</th></tr>{outside}</table>
{bad_html}
</body></html>"""


def check_overflow(html_path):
    """用 Edge 渲染一次，返回字超出格子的标签编号。"""
    dom = subprocess.run([EDGE, '--headless', '--disable-gpu', '--dump-dom', 'file:///' + html_path.replace('\\', '/')],
                         capture_output=True, timeout=120, encoding='utf-8', errors='replace').stdout
    return re.findall(r'class="lab over"><div class="code">([^<]*)<', dom)


def to_pdf(html_path):
    pdf = os.path.splitext(html_path)[0] + '.pdf'
    subprocess.run([EDGE, '--headless', '--disable-gpu', '--no-pdf-header-footer', '--print-to-pdf-no-header',
                    f'--print-to-pdf={pdf}', 'file:///' + html_path.replace('\\', '/')],
                   check=True, capture_output=True, timeout=120)
    return pdf


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(OUT, exist_ok=True)
    parts = fetch_parts()
    for name, text in (('收纳标签', labels_html()), ('收纳对照表', guide_html(parts))):
        path = os.path.join(OUT, name + '.html')
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print(path, '->', to_pdf(path))
        if name == '收纳标签':
            print('字超出格子的标签：', check_overflow(path) or '无')
    print('未分配：', [p['name'] for p in parts if not assign(p)] or '无')
