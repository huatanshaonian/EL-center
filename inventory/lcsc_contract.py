"""解析立创商城《订货合同》PDF（订单中心下载的那份），取出订单号、下单日期和每行 C 编号 / 数量 / 含税单价。

合同表格里中文和小数点的提取顺序会乱（如“19.4334”读成“19 4334”），所以：
- 只信任 C 编号、数量、单价、金额四栏，型号、名称等以 Part-DB / 补单表为准；
- 单价用“数量 × 单价 ≈ 金额”校验，对不上的行会报出来。
需要 PyMuPDF（G:\\anaconda 自带）。
"""
import io
import re
import zipfile

import pymupdf


def _nums(cell):
    return re.findall(r'\d+', cell or '')


def _decimal(cell):
    """“19 4334元 /.个” → 19.4334；“20元/个” → 20。"""
    g = _nums(cell)
    if not g:
        return None
    if len(g) >= 2 and '.' in (cell or ''):
        return float(g[0] + '.' + g[1])
    return float(g[0])


def parse_pdf_bytes(data, source=''):
    doc = pymupdf.open(stream=data, filetype='pdf')
    text = '\n'.join(p.get_text() for p in doc)
    no = re.search(r'订单编号[：:]\s*(SO\d+)', text)
    date = re.search(r'下单日期[：:]\s*(\d{4}-\d{2}-\d{2})', text)
    total = re.search(r'订单总计金额（含税）[：:]\s*([\d.]+)', text)
    lines, problems = [], []
    for page in doc:
        for t in page.find_tables().tables:
            for r in t.extract():
                cells = [(c or '').replace('\n', '') for c in r]
                if len(cells) < 8 or not cells[0].strip().isdigit():
                    continue
                m = re.match(r'\s*(C\d+)', cells[1])
                if not m:
                    continue
                qty = int(_nums(cells[5])[-1])
                price, amount = _decimal(cells[6]), _decimal(cells[7])
                if price is None or amount is None or abs(qty * price - amount) > 0.02:
                    problems.append(f'第 {cells[0]} 行 {m.group(1)}：数量 {qty} × 单价 {price} ≠ 金额 {amount}')
                lines.append({'seq': int(cells[0]), 'cnum': m.group(1), 'qty': qty,
                              'price': price, 'amount': amount})
    return {'order_no': no.group(1) if no else '', 'date': date.group(1) if date else '',
            'total': float(total.group(1)) if total else None, 'lines': lines,
            'problems': problems, 'source': source}


def load_contracts(path):
    """传 PDF 或装着多份合同 PDF 的 zip，返回合同列表。"""
    if path.lower().endswith('.zip'):
        out = []
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.filename.lower().endswith('.pdf'):
                    out.append(parse_pdf_bytes(z.read(info), info.filename))
        return out
    with open(path, 'rb') as f:
        return [parse_pdf_bytes(f.read(), path)]


if __name__ == '__main__':
    import sys
    for c in load_contracts(sys.argv[1]):
        s = sum(l['qty'] * l['price'] for l in c['lines'])
        print(c['order_no'], c['date'], f"{len(c['lines'])} 行，商品含税 {s:.2f}，合同总计 {c['total']}（含运费）")
        for p in c['problems']:
            print('  !', p)
