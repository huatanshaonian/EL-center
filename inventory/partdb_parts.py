"""从 Part-DB 取全部零件，整理成简单的字典列表（名称、描述、分类路径、库存、各批次库位），给收纳规划等脚本用。"""
from partdb_client import PartDB


def _iri(x):
    return x if isinstance(x, str) or x is None else x.get('@id')


def fetch_parts(db=None):
    db = db or PartDB()
    cats = {c['@id']: c for c in db.list_all('/api/categories')}
    locs = {l['@id']: l['name'] for l in db.list_all('/api/storage_locations')}

    def cpath(iri):
        names = []
        while iri in cats:
            names.append(cats[iri]['name'])
            iri = _iri(cats[iri].get('parent'))
        return '/'.join(reversed(names))

    out = []
    for p in db.list_all('/api/parts'):
        lots = []
        for l in p.get('partLots') or []:
            sl = l.get('storage_location')
            lots.append((l.get('amount'), sl.get('name') if isinstance(sl, dict) else locs.get(sl), l.get('@id')))
        out.append({'id': p['id'], 'iri': p['@id'], 'name': p.get('name') or '',
                    'desc': p.get('description') or '', 'cat': cpath(_iri(p.get('category'))),
                    'amount': sum(a or 0 for a, _, _ in lots), 'lots': [(a, n) for a, n, _ in lots],
                    'lot_iris': [i for _, _, i in lots]})
    return out
