"""生成“没有立创二维码的料”去哪一格的表（A4，HTML + PDF），收纳时照着放。

范围：Part-DB 里没有立创订单编号的零件——旧库存表里的料和淘宝自购件（立创的袋子扫码就能看格子，不在表里）。
按“原来在哪”分组：旧盒子按盒号（取自旧库存表的收纳位置），淘宝件一组；组内按新格子顺序排。
明纬电源（层架）不进柜，不列。
用法：G:\\anaconda\\python.exe make_nonlcsc_list.py   输出 inventory/收纳/非立创料位置表.html + .pdf
"""
import collections
import html
import os
import re
import sys

import openpyxl

from import_legacy_xlsx import XLSX, build_rows, part_name
from make_storage_labels import CSS_BASE, CSS_GUIDE, OUT, to_pdf
from partdb_client import PartDB
from partdb_parts import fetch_parts
from storage_plan import cells


def old_boxes():
    """旧库存表：零件名 -> 原盒号（L-01、R-K…）。"""
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    out = {}
    for r in build_rows(wb):
        box = str(r.get('收纳位置', '')).strip()
        if box and box != '待入库':
            out[part_name(r)] = box
    return out


def lcsc_parts(db):
    out = set()
    for od in db.list_all('/api/orderdetails'):
        if (od.get('supplierpartnr') or '').startswith('C'):
            out.add(od['part']['@id'] if isinstance(od.get('part'), dict) else od.get('part'))
    return out


def main():
    db = PartDB()
    lcsc = lcsc_parts(db)
    boxes = old_boxes()
    order = {c: i for i, (c, *_) in enumerate(cells())}
    groups = collections.defaultdict(list)
    for p in fetch_parts(db):
        if p['iri'] in lcsc:
            continue
        for (amount, cell), ld in zip(p['lots'], p['lot_desc']):
            if cell == '层架':
                continue
            new = ld.startswith(('淘宝', '手上原有'))  # import_taobao_lists.py 建的批次
            src = '淘宝 / 手上原有' if new or p['name'] not in boxes else boxes[p['name']]
            groups[src].append((order.get(cell, 999), cell, p, amount))
    rows = []
    for src in sorted(groups, key=lambda s: (s.startswith('淘宝'), s)):
        items = sorted(groups[src], key=lambda x: (x[0], x[2]['name']))
        rows.append(f'<tr><th colspan="3">原来在：{html.escape(src)}（{len(items)} 项）</th></tr>')
        for _, cell, p, amount in items:
            desc = p['desc'] if p['desc'] and not re.match(r'(五色环|数量|容差)', p['desc']) else ''
            t = html.escape(p['name']) + (f'<span class="ex"> — {html.escape(desc[:40])}</span>' if desc else '')
            rows.append(f'<tr><td class="c">{html.escape(cell)}</td><td>{t}</td><td>{amount or "若干"}</td></tr>')
    n = sum(len(v) for v in groups.values())
    page = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>非立创料位置表</title>
<style>{CSS_BASE}{CSS_GUIDE}
table {{ font-size: 8.5pt; }} th[colspan] {{ background: #ddd; font-size: 9pt; }} td.c {{ font-size: 10pt; width: 16mm; }}
td:last-child {{ width: 12mm; text-align: right; }}</style></head><body>
<h1>没有立创二维码的料：放哪一格（共 {n} 项）</h1>
<p class="note">立创的袋子用手机扫码看格子；这张表只列旧库存表里的料和淘宝件。按原来所在的盒子分组，组内按新格子顺序排，
一盒一盒倒出来照着放。数据来自 Part-DB（{html.escape(db.base)}）。</p>
<table><tr><th>格子</th><th>料</th><th>数量</th></tr>{''.join(rows)}</table>
</body></html>"""
    path = os.path.join(OUT, '非立创料位置表.html')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(page)
    print(path, '->', to_pdf(path), f'共 {n} 项')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
