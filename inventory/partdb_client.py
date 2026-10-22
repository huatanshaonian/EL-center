"""Part-DB REST 接口的最小客户端。

配置读 inventory/partdb_local.conf（不进 git）：
    PARTDB_URL=http://192.168.1.6:8088
    PARTDB_TOKEN=tcp_...
"""
import os

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONF = os.path.join(HERE, 'partdb_local.conf')
LD = 'application/ld+json'


def load_config(path=DEFAULT_CONF):
    cfg = {}
    with open(path, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                cfg[k.strip()] = v.strip()
    return cfg


class PartDBError(RuntimeError):
    pass


class PartDB:
    """封装增查改和“按名字找不到就建”，并缓存已查过的结构数据（分类、位置、厂家等）。"""

    def __init__(self, conf_path=DEFAULT_CONF, dry_run=False):
        cfg = load_config(conf_path)
        self.base = cfg['PARTDB_URL'].rstrip('/')
        self.dry_run = dry_run
        self.s = requests.Session()
        self.s.headers.update({'Authorization': 'Bearer ' + cfg['PARTDB_TOKEN'],
                               'Accept': LD})
        self._cache = {}       # endpoint -> list of items
        self._fake_id = 0

    # ---------- 底层请求 ----------
    def _req(self, method, path, **kw):
        url = path if path.startswith('http') else self.base + path
        r = self.s.request(method, url, timeout=90, **kw)
        if r.status_code >= 400:
            raise PartDBError(f'{method} {path} -> {r.status_code}: {r.text[:600]}')
        return r.json() if r.content else None

    def get(self, path, params=None):
        return self._req('GET', path, params=params)

    def post(self, path, data):
        if self.dry_run:
            self._fake_id += 1
            return {'@id': f'{path}/dry{self._fake_id}', **data}
        return self._req('POST', path, json=data, headers={'Content-Type': LD})

    def patch(self, iri, data):
        if self.dry_run:
            return data
        return self._req('PATCH', iri, json=data,
                         headers={'Content-Type': 'application/merge-patch+json'})

    def list_all(self, endpoint, params=None):
        """取某类资源的全部条目（自动翻页）。"""
        out, page = [], 1
        while True:
            p = dict(params or {}, page=page, itemsPerPage=100)
            d = self.get(endpoint, p)
            items = d.get('member', d.get('hydra:member', []))
            out.extend(items)
            total = d.get('totalItems', d.get('hydra:totalItems', len(out)))
            if not items or len(out) >= total:
                return out
            page += 1

    # ---------- 结构数据：按名字（和父节点）找，找不到就建 ----------
    def _items(self, endpoint):
        if endpoint not in self._cache:
            self._cache[endpoint] = self.list_all(endpoint)
        return self._cache[endpoint]

    @staticmethod
    def _parent_iri(item):
        p = item.get('parent')
        return p.get('@id') if isinstance(p, dict) else p

    def find(self, endpoint, name, parent=None):
        for it in self._items(endpoint):
            if it.get('name') == name and self._parent_iri(it) == parent:
                return it
        return None

    def ensure(self, endpoint, name, parent=None, **extra):
        """返回该名字条目的 IRI；不存在就新建（extra 只在新建时写入）。"""
        it = self.find(endpoint, name, parent)
        if it is None:
            data = {'name': name, **extra}
            if parent:
                data['parent'] = parent
            it = self.post(endpoint, data)
            it.setdefault('name', name)
            it.setdefault('parent', parent)
            self._items(endpoint).append(it)
        return it['@id']

    def ensure_path(self, endpoint, names, comments=None):
        """按层级建树，如 ['电阻', '固定电阻']，返回最末一级的 IRI。"""
        parent = None
        for i, n in enumerate(names):
            extra = {}
            if comments and comments.get(n):
                extra['comment'] = comments[n]
            parent = self.ensure(endpoint, n, parent, **extra)
        return parent

    # ---------- 立创数据源 ----------
    def provider_details(self, provider_id, provider_key='lcsc'):
        """调 Part-DB 的信息提供者，按 C 编号取型号、参数、规格书等。失败返回 None。"""
        try:
            return self._req('POST', '/api/info_providers/details',
                             json={'provider_key': provider_key, 'provider_id': provider_id},
                             headers={'Content-Type': 'application/json',
                                      'Accept': 'application/json'})
        except (PartDBError, requests.RequestException) as e:
            print(f'   ! 立创查询 {provider_id} 失败：{e}')
            return None
