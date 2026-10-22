"""把旧库存表《电子元器件完整库存与收纳表_新增LRS200-24.xlsx》导入 Part-DB（一次性）。

- 「元器件总库存」每行 → 一个零件 + 一个库存批次；大类/子类 → 分类树；收纳位置 → 存放位置。
- 收纳位置为「待入库」的是 2026-10-20 立创订单的在途件：按「采购记录」页挂立创商城 C 编号、
  国内单价、商品链接，再通过 Part-DB 的立创数据源补参数、规格书（下载存到 NAS）和图片。
- 阻值、容值、耐压等从“型号／阻值”一栏解析成参数，网页上可以按参数筛选。
- 可重复运行：同分类下同名零件已存在就跳过，不会重复建。

用法（项目根目录）：
    G:\\anaconda\\python.exe inventory\\import_legacy_xlsx.py --dry-run     先看会建什么
    G:\\anaconda\\python.exe inventory\\import_legacy_xlsx.py --limit 3     先导 3 行试试
    G:\\anaconda\\python.exe inventory\\import_legacy_xlsx.py               全部导入
"""
import argparse
import os
import re
import sys

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from partdb_client import PartDB  # noqa: E402
from value_parse import params_from_row  # noqa: E402
import lcsc_enrich  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(ROOT, '电子元器件完整库存与收纳表_新增LRS200-24.xlsx')

BOX_PARENT = '元件收纳盒'
TRANSIT = '待入库（在途）'
# 型号本身就是零件名的大类；其余用“子类 + 值”命名，如“固定电阻 1 MΩ”
NAME_IS_MODEL = {'三极管', '集成电路', '继电器', '电源模块', '热敏电阻', '模块'}
TO92 = {'三极管'}


def read_sheet(wb, title):
    rows = list(wb[title].iter_rows(values_only=True))
    head = [str(c or '').strip() for c in rows[0]]
    out = []
    for r in rows[1:]:
        if any(c not in (None, '') for c in r):
            out.append({h: ('' if c is None else c) for h, c in zip(head, r)})
    return out


def box_comments(wb):
    """三极管收纳页：盒号 → “收纳分组；替代注意事项”。"""
    out = {}
    for r in read_sheet(wb, '三极管收纳'):
        box = str(r.get('盒号', '')).strip()
        if re.match(r'^[A-Z]+-\d+$', box):
            out[box] = f"{r.get('收纳分组', '')}：{r.get('型号与数量', '')}。{r.get('替代注意事项', '')}"
    return out


def part_name(row):
    major, minor, model = (str(row[k]).strip() for k in ('大类', '子类', '型号／阻值'))
    if major in NAME_IS_MODEL or row['_lcsc'] or minor in model:
        return model
    return f'{minor} {model}'


def split_lcsc_spec(spec):
    """在途行的“规格／特性”是“品牌；封装；规格”三段。"""
    seg = [s.strip() for s in str(spec).split('；')]
    seg += [''] * (3 - len(seg))
    return seg[0], seg[1], '；'.join(seg[2:]).strip('；')


def build_rows(wb):
    purchases = {str(p['立创编号']).strip(): p for p in read_sheet(wb, '采购记录')
                 if str(p.get('立创编号', '')).startswith('C')}
    rows = []
    for r in read_sheet(wb, '元器件总库存'):
        m = re.search(r'立创\s*(C\d+)', str(r.get('备注', '')))
        r['_lcsc'] = m.group(1) if m and str(r.get('收纳位置')).strip() == '待入库' else ''
        r['_buy'] = purchases.get(r['_lcsc'], {})
        rows.append(r)
    return rows


def import_row(db, r, existing, types, use_provider):
    major, minor = str(r['大类']).strip(), str(r['子类']).strip()
    name = part_name(r)
    cat = db.ensure_path('/api/categories', [major, minor])
    key = (name, cat)
    if key in existing:
        return 'skip', name

    status = str(r.get('确认状态', '')).strip()
    remark = str(r.get('备注', '')).strip()
    loc_code = str(r.get('收纳位置', '')).strip()
    qty = r.get('数量（只／件）')
    part = {'name': name, 'category': cat, 'description': str(r.get('规格／特性', '')).strip(),
            'comment': '', 'tags': '', 'parameters': params_from_row(major, str(r['型号／阻值'])),
            'needs_review': ('待核实' in status) or ('疑似' in name)}
    notes = []
    if remark:
        notes.append(remark)
    if status and status not in ('已确认', '用户确认') and not status.startswith('在途'):
        notes.append(f'确认状态：{status}')
    if major in TO92:
        part['footprint'] = db.ensure('/api/footprints', 'TO-92')

    dto = None
    if r['_lcsc']:
        cnum, buy = r['_lcsc'], r['_buy']
        brand, pkg, spec = split_lcsc_spec(r.get('规格／特性', ''))
        dto = db.provider_details(cnum) if use_provider else None
        part['description'] = spec or str(buy.get('规格', ''))
        part['manufacturer_product_number'] = str(r['型号／阻值']).strip()
        part['manufacturer'] = db.ensure('/api/manufacturers', brand or str(buy.get('品牌', '')))
        fp = (dto or {}).get('footprint') or pkg or str(buy.get('封装', ''))
        if fp and fp != '-':
            part['footprint'] = db.ensure('/api/footprints', fp)
        part['tags'] = '立创'
        part['parameters'] = lcsc_enrich.provider_parameters(dto) or part['parameters']
        use = re.sub(r'；?立创\s*C\d+.*$', '', remark).strip('；')
        notes = [f'用途：{use}'] if use else []
        if dto and dto.get('description'):
            notes.append(f'立创描述：{dto["description"]}')
    part['comment'] = '\n\n'.join(notes)

    p = db.post('/api/parts', part)
    piri = p['@id']
    existing.add(key)

    # 库存批次
    if loc_code == '待入库':
        loc = db.ensure('/api/storage_locations', TRANSIT,
                        comment='已下单未到货。到货后把批次移到实际盒子里。')
        lot_desc = '在途：' + (f"立创订单 {r['_buy'].get('订单号', '')}（{r['_buy'].get('下单日期', '')} 下单）"
                              if r['_buy'] else status)
    else:
        loc = db.ensure_path('/api/storage_locations', [BOX_PARENT, loc_code],
                             comments=types['box_comments'])
        lot_desc = ''
    lot = {'part': piri, 'storage_location': loc, 'description': lot_desc,
           'instock_unknown': qty in (None, '')}
    lot['amount'] = 0 if qty in (None, '') else float(qty)
    db.post('/api/part_lots', lot)

    if r['_lcsc']:
        lcsc_enrich.add_lcsc_order(db, piri, r['_lcsc'], r['_buy'].get('链接', ''),
                                   r['_buy'].get('单价（元）'))
        if dto:
            lcsc_enrich.add_attachments(db, piri, dto, types)
    return 'new', name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='只打印，不写库')
    ap.add_argument('--limit', type=int, default=0, help='只导前 N 行（试跑用）')
    ap.add_argument('--no-provider', action='store_true', help='不查立创数据源')
    ap.add_argument('--rows', default='', help='只导这些行号（逗号分隔，按总库存页顺序从 1 数）')
    a = ap.parse_args()

    wb = openpyxl.load_workbook(XLSX, data_only=True)
    rows = build_rows(wb)
    if a.rows:
        pick = {int(x) for x in a.rows.split(',')}
        rows = [r for i, r in enumerate(rows, 1) if i in pick]
    if a.limit:
        rows = rows[:a.limit]
    db = PartDB(dry_run=a.dry_run)

    existing = set()
    if not a.dry_run:
        for p in db.list_all('/api/parts'):
            c = p.get('category')
            existing.add((p.get('name'), c.get('@id') if isinstance(c, dict) else c))
    types = {'规格书': db.ensure('/api/attachment_types', '规格书'),
             '图片': db.ensure('/api/attachment_types', '图片'),
             'box_comments': box_comments(wb)}

    stats = {'new': 0, 'skip': 0, 'fail': 0}
    for i, r in enumerate(rows, 1):
        try:
            res, name = import_row(db, r, existing, types, not a.no_provider)
        except Exception as e:
            res, name = 'fail', f"{r.get('型号／阻值')}：{e}"
        stats[res] += 1
        tag = {'new': '+', 'skip': '=', 'fail': '!'}[res]
        print(f"{i:3d} {tag} [{r['大类']}/{r['子类']}] {name}"
              + (f"  ({r['_lcsc']})" if r['_lcsc'] else ''))
    print(f"\n新建 {stats['new']}，已存在跳过 {stats['skip']}，失败 {stats['fail']}"
          + ('（试跑，没写库）' if a.dry_run else ''))


if __name__ == '__main__':
    main()
