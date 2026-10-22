"""把库存表里“1 MΩ”“470 μF / 16 V”“102 / 1 nF”这类写法解析成 Part-DB 参数。

数值一律换成基本单位（Ω、F、H、V、A），Part-DB 显示时会自动加 k/M/µ 前缀，
这样就能在网页上按参数筛选（例如所有 10 kΩ 电阻、耐压 ≥ 50 V 的电解）。
"""
import re

PREFIX = {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'μ': 1e-6, 'm': 1e-3,
          '': 1.0, 'k': 1e3, 'K': 1e3, 'M': 1e6, 'G': 1e9}
NUM_UNIT = re.compile(r'(\d+(?:\.\d+)?)\s*([pnuµμmkKMG]?)\s*(Ω|F|H|V|A)')


def _values(text):
    """找出文本里所有“数值 + 单位”，返回 [(基本单位数值, 单位)]。"""
    out = []
    for num, pre, unit in NUM_UNIT.findall(text or ''):
        out.append((round(float(num) * PREFIX[pre], 15), unit))
    return out


def param(name, value, unit, symbol=''):
    return {'_type': 'Part', 'name': name, 'value_typical': value, 'unit': unit, 'symbol': symbol,
            'value_text': ''}


# 单位 → 该类零件里这个量叫什么
NAMES = {
    '电阻': {'Ω': ('阻值', 'R')},
    '电位器': {'Ω': ('阻值', 'R')},
    '电感': {'H': ('电感量', 'L')},
    '电容': {'F': ('容值', 'C'), 'V': ('耐压', 'U')},
    '二极管': {'V': ('稳压值', 'Uz')},
    '保险丝': {'A': ('额定电流', 'I'), 'V': ('额定电压', 'U')},
}


def params_from_row(major, value_text):
    """按大类把“型号／阻值”一栏解析成参数列表；认不出就返回空表。"""
    table = NAMES.get(major)
    if not table:
        return []
    out, seen = [], set()
    for v, unit in _values(value_text):
        if unit in table and unit not in seen:
            name, sym = table[unit]
            out.append(param(name, v, unit, sym))
            seen.add(unit)
    return out
