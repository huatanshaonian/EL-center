"""立创件的补充信息：参数、规格书、立创商城订货信息（国内价）。

立创编号（C 编号）在 Part-DB 里存成供应商“立创商城”的订货号，
参数和规格书通过 Part-DB 自带的 LCSC 信息提供者取（lcsc.com 接口，英文参数）。
"""
SUPPLIER = '立创商城'
SUPPLIER_SITE = 'https://www.szlcsc.com'


def provider_parameters(dto):
    """信息提供者返回的参数 → Part-DB Parameter-Write 列表。"""
    out = []
    for p in (dto or {}).get('parameters') or []:
        if not p.get('name'):
            continue
        item = {'_type': 'Part', 'name': p['name'][:255],
                'value_text': (p.get('value_text') or '')[:255],
                'unit': (p.get('unit') or '')[:50],
                'symbol': (p.get('symbol') or '')[:50],
                'group': (p.get('group') or '')[:255]}
        for src, dst in (('value_typ', 'value_typical'), ('value_min', 'value_min'),
                         ('value_max', 'value_max')):
            if p.get(src) is not None:
                item[dst] = p[src]
        if not item['value_text'] and all(k not in item for k in
                                          ('value_typical', 'value_min', 'value_max')):
            continue
        out.append(item)
    return out


def datasheet_urls(dto):
    return [d['url'] for d in (dto or {}).get('datasheets') or [] if d.get('url')]


def image_urls(dto):
    urls = [i['url'] for i in (dto or {}).get('images') or [] if i.get('url')]
    if not urls and (dto or {}).get('preview_image_url'):
        urls = [dto['preview_image_url']]
    return urls


def add_attachments(db, part_iri, dto, types):
    """规格书让 Part-DB 下载存到 NAS；图片只存链接、做预览图。types = {'规格书': iri, '图片': iri}"""
    for url in datasheet_urls(dto)[:2]:
        try:
            db.post('/api/attachments', {
                'element': part_iri, '_type': 'Part', 'name': '规格书', 'url': url,
                'attachment_type': types['规格书'],
                'upload': {'downloadUrl': True, 'private': False,
                           'becomePreviewIfEmpty': False}})
        except Exception as e:  # 规格书下载失败不影响入库
            print(f'   ! 规格书附件失败 {url[:60]}…：{e}')
    for url in image_urls(dto)[:1]:
        try:
            db.post('/api/attachments', {
                'element': part_iri, '_type': 'Part', 'name': '图片', 'url': url,
                'attachment_type': types['图片'],
                'upload': {'downloadUrl': False, 'private': False,
                           'becomePreviewIfEmpty': True}})
        except Exception as e:
            print(f'   ! 图片附件失败：{e}')


def add_lcsc_order(db, part_iri, cnum, url, unit_price_cny):
    """在零件上挂“立创商城 C 编号”的订货信息和国内单价（人民币，基准货币不用写币种）。"""
    supplier = db.ensure('/api/suppliers', SUPPLIER, website=SUPPLIER_SITE)
    od = db.post('/api/orderdetails', {
        'part': part_iri, 'supplier': supplier, 'supplierpartnr': cnum,
        'supplier_product_url': url or ''})
    if unit_price_cny not in (None, ''):
        db.post('/api/pricedetails', {
            'orderdetail': od['@id'], 'price': str(unit_price_cny),
            'price_related_quantity': 1, 'min_discount_quantity': 1})
    return od['@id']
