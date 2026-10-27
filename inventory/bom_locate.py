"""按 BOM 行去 Part-DB 找料，返回它放在哪几格、库存多少。给焊接图（make_solder_map.py）等用。

匹配顺序：
  1. 立创编号（BOM 的 Supplier Part = Part-DB 订单信息里的供应商料号）
  2. 型号（BOM 的 Manufacturer Part 与 Part-DB 零件名相同，或一方是另一方的前缀，如 MAX6921AWI+T / MAX6921AWI）
  3. 按数值：电阻、电容按“直插/贴片 + 封装 + 数值”找（旧库存表里的电阻电容没有立创编号）
  4. 同系列：型号去掉封装后缀后相同（ULN2803APG / ULN2803AN），也要人确认
第 3、4 种只是同规格/同系列的料，页面上要标出来让人自己确认。
立创下单时换过的料（procurement/build_lcsc_bom_order*.py 里的 SUBST）按换后的编号找。
"""
import ast
import glob
import os
import re

from partdb_client import PartDB
from partdb_parts import fetch_parts
from value_parse import _values

SMD_PKG = re.compile(r'^(R|C)(0402|0603|0805|1206|1210|2512)$')
PROC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'procurement')
# BOM 写法和库里名字对不上、又没有立创编号可查的
ALIAS = {'PH2.54,2*6P': 'PZ254V-12-12P-A40',               # EL-IF P1–P3 2×6 直针
         'GZC9-A': 'GZC9-F 9 脚陶瓷管座',                   # 6E2 板用自己买的 GZC9-F
         '204-10SDRD': '发光二极管 红色'}                   # HV-UNI 指示灯用库存红 LED
# 按数值找时排后面的格子（功率电阻、高压/薄膜电容），普通的找不到才用它们
SPECIAL = {'B04前', 'AL1前', 'AL1后'}


def _subst():
    """读各立创下单脚本里的换料表 {原编号: 新编号}（只解析字面量，不执行脚本）。"""
    out = {}
    for fn in glob.glob(os.path.join(PROC, 'build_lcsc_bom_order*.py')):
        tree = ast.parse(open(fn, encoding='utf-8').read())
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'SUBST' for t in node.targets):
                out.update(ast.literal_eval(node.value))
    return out


def _family(m):
    """型号去掉封装后缀：ULN2803APG → ULN2803A。太短的不算。"""
    f = re.match(r'[A-Z]+\d+[A-Z]?', m)
    return f.group(0) if f and len(f.group(0)) >= 7 else None


def _num(text, unit):
    v = [x for x, u in _values(text) if u == unit]
    return v[0] if v else None


def _same(a, b):
    return a is not None and b is not None and abs(a - b) <= 1e-9 * max(abs(a), abs(b), 1e-15)


class Locator:
    def __init__(self, db=None):
        db = db or PartDB()
        self.parts = {p['iri']: p for p in fetch_parts(db)}
        self.subst = _subst()
        try:  # 旧库存表里的料（零件名 -> 原盒号），用户有的没收进柜子，焊接图要标出来
            from import_legacy_xlsx import legacy_boxes
            self.legacy = legacy_boxes()
        except Exception as e:  # 旧表不在（换电脑）时只是不标
            print('读不到旧库存表，焊接图不标“旧库存”：', e)
            self.legacy = {}
        self.pic = {}  # 零件 IRI -> 商品图地址（立创导入时存的外链）
        for a in db.list_all('/api/attachments'):
            el = a.get('element') or {}
            if a.get('picture') and el.get('@type') == 'Part' and a.get('media_url'):
                self.pic.setdefault(el['@id'], a['media_url'])
        self.by_c = {}
        for od in db.list_all('/api/orderdetails'):
            pi = od['part']['@id'] if isinstance(od.get('part'), dict) else od.get('part')
            if od.get('supplierpartnr') and pi in self.parts:
                self.by_c.setdefault(od['supplierpartnr'], []).append(self.parts[pi])

    def _by_mpn(self, mpn):
        m = mpn.upper().replace(' ', '')
        if len(m) < 4:
            return []
        out = []
        for p in self.parts.values():
            n = p['name'].upper().replace(' ', '')
            if n == m or (len(n) >= 5 and (m.startswith(n) or n.startswith(m))):
                out.append(p)
            elif len(m) >= 6 and re.search(r'(?<![A-Z0-9])' + re.escape(m) + r'(?![A-Z0-9])', n):
                out.append(p)  # 库里名字带前后缀：明纬 NID100-5（5 V 输出）
            elif len(n) >= 6 and re.search(r'(?<![A-Z0-9])' + re.escape(n) + r'(?![A-Z0-9])', m):
                out.append(p)  # BOM 写成一句话：单针排母：从 PM254-1-20-Z-8.5 剪 1 针
        return out

    def _by_family(self, mpn):
        f = _family(mpn.upper())
        if not f:
            return []
        return [p for p in self.parts.values() if _family(p['name'].upper()) == f]

    def _by_value(self, val, fp):
        """电阻、电容按数值 + 直插/贴片（贴片再加封装）找同规格的料。"""
        smd = SMD_PKG.match(fp)
        if fp.startswith('RES-TH') or (smd and smd.group(1) == 'R'):
            unit, major = 'Ω', '电阻'
        elif fp.startswith('CAP-TH') or (smd and smd.group(1) == 'C'):
            unit, major = 'F', '电容'
        else:
            return []
        want = _num(val, unit)
        if want is None:
            return []
        out = []
        for p in self.parts.values():
            if not p['cat'].startswith(major):
                continue
            is_smd = p['cat'].endswith('贴片电阻') or p['cat'].endswith('贴片电容')
            if bool(smd) != is_smd:
                continue
            if smd:  # 贴片：封装要对；名字和说明里都没写封装的（如 WR25W4704FTL）也收下
                text = p['name'] + p['desc']
                pk = {k for k in ('0402', '0603', '0805', '1206', '1210', '2512') if k in text}
                if p['name'].startswith('CL10'):
                    pk.add('0603')
                if p['name'].startswith('CL21'):
                    pk.add('0805')
                if pk and smd.group(2) not in pk:
                    continue
            if not smd and major == '电容':  # 直插电容：BD 是电解，L×W 是瓷片/薄膜
                electro = '电解' in p['cat']
                if electro != ('_BD' in fp):
                    continue
            if _same(_num(p['desc'], unit) or _num(p['name'], unit), want):
                out.append(p)
        plain = [p for p in out if not {l for _, l in p['lots']} <= SPECIAL]
        return plain or out

    def locate(self, row):
        """row 是 BOM 一行（dict）。返回 {'how': 'C'|'型号'|'数值'|'同系列', 'cells': [...], 'stock': n,
        'names': [...], 'img': 商品图地址或 None, 'old': [[旧库存零件名, 原盒号], ...], 'allOld': 是否全是旧库存} 或 None。"""
        c = (row.get('Supplier Part') or '').strip()
        mpn = (row.get('Manufacturer Part') or '').strip() or (row.get('Comment') or '').split(' ')[0]
        for k, v in ALIAS.items():
            if mpn.startswith(k):
                mpn = v
        tries = (('C', lambda: self.by_c.get(self.subst.get(c, c), []) or self.by_c.get(c, [])),
                 ('型号', lambda: self._by_mpn(mpn) if mpn else []),
                 ('数值', lambda: self._by_value(row.get('Value') or row.get('Comment') or '', row.get('Footprint') or '')),
                 ('同系列', lambda: self._by_family(mpn) if mpn else []))
        for how, get in tries:
            found = get()
            if found:
                cells = []
                for p in found:
                    for _, loc in p['lots']:
                        if loc and loc not in cells:
                            cells.append(loc)
                img = next((self.pic[p['iri']] for p in found if p['iri'] in self.pic), None)
                old = sorted({(p['name'], self.legacy[p['name']]) for p in found if p['name'] in self.legacy})
                return {'how': how, 'cells': cells, 'stock': sum(p['amount'] for p in found),
                        'names': sorted({p['name'] for p in found}), 'img': img,
                        'old': [list(o) for o in old], 'allOld': len(old) == len({p['name'] for p in found})}
        return None
