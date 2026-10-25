"""按 storage_plan.py 的分格规则，把 Part-DB 里每个批次的库位改成它该放的格子（如 “B02后”）。

库位结构：A柜 / B柜 下面是各格（A01前 … B30后），另有 层架、文件袋、大盒子 三个顶层库位。
已经在目标格的批次不动，可重复运行；没有批次的零件补一个“数量未知”的批次，扫码也能看到格子。
用法：
    G:\\anaconda\\python.exe apply_storage_locations.py          # 只列出要改什么
    G:\\anaconda\\python.exe apply_storage_locations.py --apply  # 真改
"""
import collections
import sys

from partdb_client import PartDB
from partdb_parts import fetch_parts
from storage_plan import OUTSIDE, assign, cells

ROOTS = {'A': 'A柜', 'B': 'B柜'}


def ensure_locations(db):
    """建全部格子库位，返回 名字 -> IRI。"""
    iri = {}
    parents = {k: db.ensure('/api/storage_locations', v) for k, v in ROOTS.items()}
    for cell, *_ in cells():
        iri[cell] = db.ensure('/api/storage_locations', cell, parents[cell[0]])
    for name in OUTSIDE:
        iri[name] = db.ensure('/api/storage_locations', name)
    return iri


def main(apply):
    db = PartDB(dry_run=not apply)
    parts = fetch_parts(db)
    loc = ensure_locations(db)
    moves, adds, skip = collections.Counter(), [], []
    for p in parts:
        target = assign(p)
        if target is None:
            skip.append(p['name'])
            continue
        if not p['lot_iris']:
            adds.append((p['name'], target))
            db.post('/api/part_lots', {'part': p['iri'], 'storage_location': loc[target],
                                       'instock_unknown': True, 'amount': 0})
            continue
        for (amount, old), lot in zip(p['lots'], p['lot_iris']):
            if old == target:
                continue
            moves[(old, target)] += 1
            db.patch(lot, {'storage_location': loc[target]})
    print(('已改' if apply else '将改') + f'：{sum(moves.values())} 个批次')
    for (old, new), n in sorted(moves.items(), key=lambda x: (x[0][1], x[0][0] or '')):
        print(f'  {old} -> {new}  ×{n}')
    if adds:
        print(f'补建批次（零件原来没有批次）{len(adds)} 个：', '、'.join(f'{n}→{t}' for n, t in adds))
    if skip:
        print('没分到格子、没动：', '、'.join(skip))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main('--apply' in sys.argv)
