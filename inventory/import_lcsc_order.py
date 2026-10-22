"""立创商城订货合同 → Part-DB 在途库存（每次下单后跑一次，可重复运行）。

对合同里的每一行（C 编号）：
- 库里已有这个 C 编号的零件：把立创单价更新为本单含税单价；
- 没有：新建零件。型号、规格、品牌、分类取 procurement/ 下的立创补单表（*立创商城BOM*.xlsx），
  参数、封装、规格书、图片取 Part-DB 的立创数据源；
- 在“待入库（在途）”放一个批次，描述写“在途：立创订单 SO…（日期 下单）”。同一订单的批次已存在就只
  更新数量；已经移到盒子里的批次（说明到货了）不动。

用法（项目根目录）：
    G:\\anaconda\\python.exe inventory\\import_lcsc_order.py procurement\\立创商城订单合同.zip --dry-run
    G:\\anaconda\\python.exe inventory\\import_lcsc_order.py procurement\\立创商城订单合同.zip
旧导入里用报价单号 BOM261019002514 记的在途批次，用 --legacy-ref BOM261019002514=SO26101911224 认领。
"""
import argparse
import glob
import os
import sys
import warnings

import openpyxl

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from partdb_client import PartDB  # noqa: E402
from lcsc_contract import load_contracts  # noqa: E402
from lcsc_categories import category_path  # noqa: E402
import lcsc_enrich  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSIT = '待入库（在途）'


def load_bom_rows():
    """procurement/ 下所有立创补单表，按修改时间从旧到新读，新表覆盖旧表。C 编号 → 行。"""
    files = sorted(glob.glob(os.path.join(ROOT, 'procurement', '*立创商城BOM*.xlsx')),
                   key=os.path.getmtime)
    out = {}
    for f in files:
        ws = openpyxl.load_workbook(f, data_only=True).active
        rows = list(ws.iter_rows(values_only=True))
        head = [str(c or '').strip() for c in rows[0]]
        for r in rows[1:]:
            d = {h: ('' if c is None else str(c).strip()) for h, c in zip(head, r)}
            if d.get('商品编号', '').startswith('C'):
                out[d['商品编号']] = d
    return out


def index_existing(db):
    """C 编号 → (零件 IRI, 订货信息)；零件 IRI → 批次列表。"""
    by_c = {}
    for od in db.list_all('/api/orderdetails'):
        part = od.get('part')
        by_c[od.get('supplierpartnr')] = ((part or {}).get('@id') if isinstance(part, dict) else part, od)
    lots = {}
    for lot in db.list_all('/api/part_lots'):
        p = lot.get('part')
        lots.setdefault(p.get('@id') if isinstance(p, dict) else p, []).append(lot)
    return by_c, lots


def create_part(db, cnum, bom, price, types):
    dto = db.provider_details(cnum)
    model = bom.get('型号') or (dto or {}).get('mpn') or cnum
    desc = bom.get('参数/规格') or (dto or {}).get('description', '')
    cat = db.ensure_path('/api/categories', category_path(
        bom.get('分类'), model, desc, (dto or {}).get('category', '')))
    part = {'name': model, 'category': cat, 'description': desc,
            'manufacturer_product_number': model, 'tags': '立创',
            'parameters': lcsc_enrich.provider_parameters(dto),
            'comment': f"立创描述：{dto['description']}" if dto and dto.get('description') else ''}
    brand = bom.get('品牌') or (dto or {}).get('manufacturer')
    if brand:
        part['manufacturer'] = db.ensure('/api/manufacturers', brand)
    fp = (dto or {}).get('footprint') or bom.get('封装')
    if fp and fp != '-':
        part['footprint'] = db.ensure('/api/footprints', fp)
    piri = db.post('/api/parts', part)['@id']
    url = f'https://so.szlcsc.com/global.html?k={cnum}'
    odiri = lcsc_enrich.add_lcsc_order(db, piri, cnum, url, price)
    if dto:
        lcsc_enrich.add_attachments(db, piri, dto, types)
    return piri, odiri, model


def update_price(db, od, price):
    pds = od.get('pricedetails') or []
    if pds:
        cur = float(pds[0].get('price') or 0)
        if abs(cur - price) > 1e-6:
            db.patch(pds[0]['@id'], {'price': str(price)})
            pds[0]['price'] = str(price)   # 同步缓存，否则同一 C 编号在后一张合同里会拿旧价比较
    else:
        db.post('/api/pricedetails', {'orderdetail': od['@id'], 'price': str(price),
                                      'price_related_quantity': 1, 'min_discount_quantity': 1})


def put_lot(db, piri, lots, order_no, refs, qty, desc):
    """同一订单的批次：在途就更新数量和描述，已到货（不在在途位置）就不动。"""
    for lot in lots.get(piri, []):
        if any(r in (lot.get('description') or '') for r in refs):
            loc = lot.get('storage_location') or {}
            if TRANSIT not in str(loc.get('name', '')):
                return 'arrived'
            if float(lot.get('amount') or 0) != qty or lot.get('description') != desc:
                db.patch(lot['@id'], {'amount': float(qty), 'description': desc})
                return 'updated'
            return 'same'
    loc = db.ensure('/api/storage_locations', TRANSIT,
                    comment='已下单未到货。到货后把批次移到实际盒子里。')
    db.post('/api/part_lots', {'part': piri, 'storage_location': loc, 'amount': float(qty),
                               'description': desc})
    return 'new_lot'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('contracts', nargs='+', help='合同 PDF 或 zip')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--legacy-ref', action='append', default=[],
                    help='旧单号=合同单号，如 BOM261019002514=SO26101911224')
    a = ap.parse_args()

    legacy = dict(x.split('=', 1) for x in a.legacy_ref)
    bom = load_bom_rows()
    db = PartDB(dry_run=a.dry_run)
    by_c, lots = index_existing(db)
    types = {'规格书': db.ensure('/api/attachment_types', '规格书'),
             '图片': db.ensure('/api/attachment_types', '图片')}

    contracts = [c for path in a.contracts for c in load_contracts(path)]
    contracts.sort(key=lambda c: c['date'])   # 先旧后新，单价以最新一单为准
    for c in contracts:
        no, date = c['order_no'], c['date']
        refs = [no] + [old for old, new in legacy.items() if new == no]
        desc = f'在途：立创订单 {no}（{date} 下单）'
        print(f'== {no}（{date}），{len(c["lines"])} 行，合同总计 {c["total"]} 元')
        for p in c['problems']:
            print('  ! 合同解析：', p)
        stat = {}
        for ln in c['lines']:
            cnum = ln['cnum']
            if cnum in by_c:
                piri, od = by_c[cnum]
                update_price(db, od, ln['price'])
                kind, name = '已有', (od.get('part') or {}).get('name', cnum)
            else:
                piri, odiri, name = create_part(db, cnum, bom.get(cnum, {}), ln['price'], types)
                by_c[cnum] = (piri, {'@id': odiri, 'pricedetails': [{'@id': '', 'price': ln['price']}]})
                kind = '新建'
            res = put_lot(db, piri, lots, no, refs, ln['qty'], desc)
            lots.setdefault(piri, []).append({'description': desc, 'amount': ln['qty'],
                                              'storage_location': {'name': TRANSIT}, '@id': ''})
            stat[(kind, res)] = stat.get((kind, res), 0) + 1
            print(f"  {ln['seq']:3d} {cnum:<10} ×{ln['qty']:<4} ¥{ln['price']:<8} {kind} {res:8} {name}")
        print('  小结：', '，'.join(f'{k[0]}/{k[1]} {v}' for k, v in sorted(stat.items())))
    if a.dry_run:
        print('（试跑，没写库）')


if __name__ == '__main__':
    main()
