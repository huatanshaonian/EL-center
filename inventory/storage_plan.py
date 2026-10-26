"""元件收纳柜规划：每个抽屉格子放什么，以及把 Part-DB 里每种料分到哪一格的规则。

柜子（2026-10-25 用户确认的布局，抽屉从左到右、从上到下编号）：
  A 柜：上 3 排 × 6 个小抽屉 A01–A18，下 2 排 × 3 个大抽屉 AL1–AL6
  B 柜：上 5 排 × 6 个小抽屉 B01–B30，下 3 排 × 3 个大抽屉（放工具，不在这里规划）
  小抽屉内宽约 4 cm、高 3 cm，大抽屉约 8 cm × 5 cm，深都是 14 cm；每个抽屉分前、后两格。
格子编号写成 “A05前”“A05后”，也是 Part-DB 里的库位名。
"""
import re

from value_parse import _values

# 抽屉 -> (前格, 后格)；空字符串 = 空着备用（标签只印编号，留给手写）
DRAWERS = {
    'A01': ('T-01 通用NPN', 'T-02 通用PNP'),
    'A02': ('T-03 大电流', 'T-04 高频NPN'),
    'A03': ('T-05 高压NPN', 'T-06 高压PNP'),
    'A04': ('直插MOS管', '贴片三极管/MOS'),
    'A05': ('玻封稳压管', '1N4148 开关管'),
    'A06': ('整流/TVS 直插', '贴片二极管'),
    'A07': ('LED', '光敏/热敏电阻'),
    'A08': ('DIP 数字IC', 'DIP 模拟IC'),
    'A09': ('贴片IC', '贴片IC（2）'),
    'A10': ('IC座 8/14P', 'IC座 16/20P'),
    'A11': ('微调电位器', '继电器/蜂鸣器'),
    'A12': ('保险丝/保险夹', '自恢复/ATM座'),
    'A13': ('色环电感', '功率/工字电感'),
    'A14': ('', ''), 'A15': ('', ''), 'A16': ('', ''), 'A17': ('', ''), 'A18': ('', ''),
    'AL1': ('大电解电容', '高压/薄膜电容'),
    'AL2': ('编码器/开关', '直滑推子'),
    'AL3': ('模块', '模块（2）'),
    'AL4': ('喇叭', 'DC头/USB座'),
    'AL5': ('HDMI/DF11/端子', '管座/IEC座'),
    'AL6': ('五金 M4螺丝', '五金 M4 T螺母'),
    'B01': ('电阻 1–91Ω', '电阻 100–910Ω'),
    'B02': ('电阻 1–9.1k', '电阻 10–91k'),
    'B03': ('电阻 100–910k', '电阻 ≥1M/高压'),
    'B04': ('功率电阻', '0Ω 直插'),
    'B05': ('0603 电阻', '0805/2512 电阻'),
    'B06': ('0603 电容', '0805+ 贴片电容'),
    'B07': ('瓷片 ≤1nF', '瓷片 10–100nF'),
    'B08': ('电解 ≤10µF', '电解 22–100µF'),
    'B09': ('电解 220–470µF', ''),
    'B10': ('单排排针', '双排排针'),
    'B11': ('短排母', '长排母'),
    'B12': ('XH座 2P', 'XH座 3P'),
    'B13': ('XH座 4/5P', 'XH座 7/8/14P'),
    'B14': ('XH胶壳 2P', 'XH胶壳 3P'),
    'B15': ('XH胶壳 4P', 'XH胶壳 5–14P'),
    'B16': ('XH端子', ''),
    'B17': ('五金 M3螺丝', '五金 M3螺母'),
    'B18': ('五金 沉头/尼龙', '五金 锤头螺母'),
    'B19': ('五金 M3铜柱', '五金 M2.5柱/钉'),
    'B20': ('五金 热熔/自攻', '五金 垫片'),
    **{f'B{i:02d}': ('', '') for i in range(21, 31)},
}
BIG = {k for k in DRAWERS if k.startswith('AL')}

# Part-DB 里没有、但要放进格子的东西（淘宝件、五金），对照表里提示
EXTRA = {
    'B16前': 'XH 散装端子（淘宝，压线钳用）',
    'B17前': 'M3 螺丝（各长度，内六角/十字）', 'B17后': 'M3 螺母',
    'B18前': 'M3 沉头螺丝（黑/本色）、M3 尼龙螺丝螺母套装', 'B18后': 'M3 锤头螺母（2020）',
    'B19前': 'M3 六角铜柱 6/10/11 mm', 'B19后': 'M2.5×25 铜柱 + M2.5×6 螺丝',
    'B20前': 'M3 热熔铜螺母、M2/M3 自攻螺丝', 'B20后': 'M3 尼龙平垫等垫片',
    'AL6前': 'M4×8 螺丝', 'AL6后': 'M4 弹片 T 螺母（2020）',
    'AL3后': 'ESP32 开发板等其他模块（装静电袋）', 'A09前': 'MAX6921 到货也放这里（静电袋）',
}

# 不进抽屉的
OUTSIDE = {
    '层架': '明纬电源（太大）',
    '文件袋': 'FFC 软排线（不能折，平放）',
    '大盒子': '辉光管、IV18、6E2、盖革管、指针表头（连包装一起放）',
}

# 旧盒子的三极管库位直接整格搬
LEGACY_T = {'T-01': 'A01前', 'T-02': 'A01后', 'T-03': 'A02前', 'T-04': 'A02后', 'T-05': 'A03前', 'T-06': 'A03后'}


def cells():
    """按顺序列出所有格子 (编号, 抽屉, 前/后, 标签文字)。"""
    for d, (f, b) in DRAWERS.items():
        yield d + '前', d, '前', f
        yield d + '后', d, '后', b


def _val(p, unit):
    v = _values(p['desc']) or _values(p['name'])
    v = [x for x, u in v if u == unit]
    return v[0] if v else None


def _resistor(p):
    if p['cat'] == '电阻/贴片电阻':
        return 'B05前' if '0603' in p['name'] else 'B05后'
    if '跳线' in p['desc'] or _val(p, 'Ω') == 0:
        return 'B04后'
    if p['cat'].startswith('电阻/功率') or re.search(r'(?<![/\d])[123]W|1/2W', p['desc']):
        return 'B04前'
    r = _val(p, 'Ω')
    if r is None:
        return None
    for lim, c in ((100, 'B01前'), (1e3, 'B01后'), (1e4, 'B02前'), (1e5, 'B02后'), (1e6, 'B03前')):
        if r < lim:
            return c
    return 'B03后'


def _capacitor(p):
    cat, t = p['cat'], p['desc'] + ' ' + p['name']
    if cat == '电容/贴片电容':
        return 'B06前' if ('0603' in p['name'] or p['name'].startswith('CL10')) else 'B06后'
    if cat == '电容/薄膜电容' or re.search(r'1\s*kV|1KV', t):
        return 'AL1后'
    if cat == '电容/固态电解电容':
        return 'B08后'
    c = _val(p, 'F')
    if cat == '电容/瓷片电容':
        return 'B07前' if c is not None and c <= 1.0e-9 else 'B07后'
    if cat == '电容/铝电解电容':
        v = _val(p, 'V') or 0
        if c is None:
            return None
        if (c >= 470e-6 and v >= 25) or v >= 100:
            return 'AL1前'
        if c >= 220e-6:
            return 'B09前'
        return 'B08后' if c >= 22e-6 else 'B08前'
    return None


SMD_IC = ('DBVR', 'RPWR', 'SM/TR', 'AP2112K', 'M96', 'MAX6921')
ANALOG_IC = ('NE555', 'TLC555', 'LM393', 'TL431', 'UC3843')


def assign(p):
    """返回这种料该放的格子编号；不进抽屉的返回 OUTSIDE 的键；认不出返回 None。"""
    cat, name, desc = p['cat'], p['name'], p['desc']
    major = cat.split('/')[0]
    locs = [l for _, l in p['lots']]
    if major == '三极管':
        for l in locs:
            if l in LEGACY_T:
                return LEGACY_T[l]
            if l in LEGACY_T.values():  # 已经挪到新格子了（apply_storage_locations.py 跑过之后）
                return l
        if name.startswith('MMBT'):
            return 'A04后'
        return 'A03前' if ('高压' in desc and cat.endswith('NPN')) else None
    if major == '场效应管':
        return 'A04前' if name.startswith('IRF') else 'A04后'
    if major == '二极管':
        if name.startswith(('BAT', 'SMBJ', 'BZT')):
            return 'A06后'
        if cat.endswith('稳压二极管'):
            return 'A05前'
        if '开关二极管' in cat:
            return 'A05后'
        return 'A06前'
    if major == 'LED':
        return 'A07前'
    if major in ('光敏电阻', '热敏电阻'):
        return 'A07后'
    if major == '集成电路':
        if any(k in name for k in SMD_IC):
            return 'A09前'
        return 'A08后' if name.startswith(ANALOG_IC) else 'A08前'
    if major in ('显示器件', '电子管'):  # 表头、各种管子：大件，连包装放大盒子
        return '大盒子'
    if cat == 'IC 插座/电子管座' or cat == '连接器/电源插座':
        return 'AL5后'
    if major in ('射频', '散热'):  # 天线、风扇
        return 'AL4后'
    if major == 'IC 插座':
        return 'A10前' if re.search(r'DIP-(8|14)\b', desc) else 'A10后'
    if major == '电位器':
        return 'AL2后' if cat.endswith('直滑推子') else 'A11前'
    if major == '继电器' or cat == '声学器件/蜂鸣器':
        return 'A11后'
    if cat == '声学器件/扬声器':
        return 'AL4前'
    if major == '保险丝':
        return 'A12后' if (cat.endswith('自恢复保险丝') or name.startswith('3557') or 'ATM' in name) else 'A12前'
    if major == '电感':
        return 'A13前' if cat.endswith('色环轴向电感') else 'A13后'
    if major in ('开关', '输入器件'):
        return 'AL2前'
    if major == '模块':
        return 'AL3前'
    if major == '电源模块':  # 明纬 AC/DC 太大放层架，DC/DC 升压模块进抽屉
        return '层架' if (name.startswith('明纬') or cat.endswith('AC/DC 开关电源')) else 'AL3后'
    if major == '电阻':
        return _resistor(p)
    if major == '电容':
        return _capacitor(p)
    if major == '连接器':
        sub = cat.split('/')[1]
        if sub in ('DC 插头', 'USB-A 母座'):
            return 'AL4后'
        if sub == '跳线帽':
            return 'B10前'
        if sub == 'XH 胶壳':
            n = int(re.search(r'(\d+)P', name).group(1))
            return {2: 'B14前', 3: 'B14后', 4: 'B15前'}.get(n, 'B15后')
        if sub == 'FFC 排线':
            return '文件袋'
        if sub == 'XH 插座':
            n = int(re.search(r'XH-(\d+)', name).group(1))
            return {2: 'B12前', 3: 'B12后'}.get(n, 'B13前' if n <= 5 else 'B13后')
        if sub == '排针':
            return 'B10后' if '-12-' in name else 'B10前'
        if sub == '排母':
            return 'B11后' if re.search(r'1×2[02]P', desc) else 'B11前'
        return 'AL5前'
    return None
