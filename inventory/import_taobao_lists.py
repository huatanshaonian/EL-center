"""把淘宝自购清单（procurement/MIS-01_自购清单*.xlsx）里的电子件入 Part-DB，库位按 storage_plan.assign() 直接分到收纳格。

只收电子件；工具、五金、线材、外壳、耗材不入库（用户自己归类）。条目是从两张清单里人工挑出来的：
  第一批（make_buy_list.py，2026-10-20 已全部买齐）、第二批（make_buy_list_2.py，2026-10-23 买了 1–26、32–47）。
已有同名零件就只加批次；同一零件已有同样说明的批次就跳过，可重复运行。
用法：G:\\anaconda\\python.exe import_taobao_lists.py [--apply]（不带 --apply 只列出要做什么）
"""
import sys

from partdb_client import PartDB
from partdb_parts import fetch_parts
from storage_plan import assign

B1 = '淘宝第一批（自购清单）'
B2 = '淘宝第二批（2026-10-23 下单）'
HAVE = '手上原有（未进旧库存表）'

# (名称, 说明, 分类路径, [(数量, 批次说明), ...])
ITEMS = [
    # ---- 第一批 ----
    ('长方形带灯按钮 12V 自复位', '矩形头 24×18，开孔 Ø16（M16×1），LED 12 V，1NO+1NC；斜面④ 功能键', '开关/带灯按钮', [(6, B1)]),
    ('Ø16 指示灯 12V', '绿、红、黄各 1；灯头外径 19.5，开孔 Ø16；斜面③', 'LED/面板指示灯', [(3, B1)]),
    ('BH1750 光线模块 GY-302', 'I²C 0x23/0x5C，板载上拉；顶部边条光线感应', '模块/传感器模块', [(1, B1)]),
    ('85C1 指针表头 0–1 mA', '面框 64×56，背面凸台 Ø49；内阻实测约 160 Ω；1 用 1 备', '显示器件/指针表头', [(2, B1)]),
    ('NCH6100HV 辉光管升压模块', 'Omnixie；12–24 V 入，85–235 V 可调出；IN-14 阳极备用', '电源模块/DC/DC 电源模块', [(1, B1)]),
    ('UC3843 高压升压模块 45–390 V', '8–32 V 入；60×50×22，4×M3；6E2 阳极设 250 V', '电源模块/DC/DC 电源模块', [(1, B1)]),
    ('XL6009 可调升压模块', '3–32 V 入，5–35 V 出；43×21×14；IV-18 栅/阳极约 35 V，1 用 1 备', '电源模块/DC/DC 电源模块', [(2, B1)]),
    ('GZC9-F 9 脚陶瓷管座', 'noval 底盘安装；6E2 ×2 + 1 备', 'IC 插座/电子管座', [(3, B1)]),
    ('MAX6921AWI', 'VFD 驱动，SOIC-28 宽体；IV-18 板 1 用 1 备；焊前用 SOP28 测试座测真伪', '集成电路/IC', [(4, B1)]),  # 清单写 2，2026-10-27 用户清点实有 4
    ('USB2.0 一分四 Hub 模块', 'DC 5 V 外部供电款', '模块/USB Hub', [(1, B1)]),
    ('DS3231 RTC 模块 ZS-042', 'I²C 0x68（板上 AT24C32 0x57）；装 CR2032 前拆充电电阻/二极管', '模块/RTC', [(1, B1)]),
    ('2.4 GHz 胶棒天线 SMA', '2 dBi，50 Ω；ESP32-S3 外接天线', '射频/天线', [(1, B1)]),
    ('PAM8403 功放模块', '5 V，4 Ω 每声道 3 W，不带电位器版', '模块/功放', [(1, B1)]),
    ('Sunon MF40100V1-1000U-A99', '40×10 风扇 5 V，8.0 CFM；直吹 RK3399', '散热/风扇', [(1, B1)]),
    ('IEC C14 三合一电源座', '带保险丝座和船型开关，10 A 250 V，卡扣，开孔约 47×27', '连接器/电源插座', [(1, B1)]),
    ('5×20 保险丝 T3.15A 250V', '慢断；IEC 座内用（含备用）', '保险丝/熔断器', [(5, B1)]),
    # ---- 第二批 ----
    ('ATM 片式保险 7.5A', 'Mini(ATM) 棕色；PCB-3 两个 NID100 输入（F_N5、F_N12）+ 备用', '保险丝/熔断器', [(4, B2)]),
    ('2.54 mm 跳线帽', '盖革 JP1、ESP 底板 JP_BZ 等', '连接器/跳线帽', [(3, B2)]),
    ('XH2.54 胶壳 2P', '线端母壳，配 XH-2A', '连接器/XH 胶壳', [(25, B2)]),
    ('XH2.54 胶壳 3P', '线端母壳，配 XH-3A', '连接器/XH 胶壳', [(10, B2)]),
    ('XH2.54 胶壳 4P', '线端母壳，配 XH-4A', '连接器/XH 胶壳', [(18, B2)]),
    ('XH2.54 胶壳 5P', '线端母壳，配 XH-5A', '连接器/XH 胶壳', [(5, B2)]),
    ('XH2.54 胶壳 7P', '线端母壳，配 XH-7A', '连接器/XH 胶壳', [(3, B2)]),
    ('XH2.54 胶壳 8P', '线端母壳，配 XH-8A', '连接器/XH 胶壳', [(5, B2)]),
    ('XH2.54 胶壳 14P', '线端母壳，配 XH-14A', '连接器/XH 胶壳', [(4, B2)]),
    ('3070 腔体喇叭 4Ω 3W', '约 70×30×17，4 耳孔 Ø3.4 孔距 63×24；立体声 2 只 + 1 备', '声学器件/扬声器', [(3, B2)]),
    ('FFC 20P 0.5mm 30CM', 'FFC 软排线 0.5 mm 20P 长 30 cm 同向（A 型）厚 0.3；HDMI 软排线小板', '连接器/FFC 排线', [(1, B2)]),
    ('SOP28 宽体翻盖测试座', 'SOIC-28W 300 mil，脚距 1.27，免焊；测 MAX6921 真伪', 'IC 插座/测试座', [(1, B2)]),
    ('UC3843AN', '电流模式 PWM 控制器，DIP-8 直插；HV-UNI 每块 1 只（共 3 块）', '集成电路/IC',
     [(6, '淘宝自购（不在两张清单里）')]),  # 2026-10-27 用户清点 6 个
    ('К155ИД1 / K155ID1', '', '集成电路/IC', [(2, B2 + ' 备件')]),
    ('IN-14 辉光管', '', '电子管/辉光管', [(6, HAVE), (1, B2 + ' 备件')]),
    ('IV-18 荧光管', 'тип 2 优先；тип 1 也能用（R17–R19 改焊）', '电子管/荧光管', [(1, HAVE), (1, B2 + ' 备件')]),
    ('6E2 猫眼管（北京 = EM87）', '', '电子管/猫眼管', [(2, HAVE), (1, B2 + ' 备件')]),
    ('J305 盖革管', '总长约 103.5，管径 10', '电子管/盖革管', [(1, HAVE), (1, B2 + ' 备件')]),
]


def main(apply):
    db = PartDB(dry_run=not apply)
    parts = {p['name']: p for p in fetch_parts(db)}
    locs = {l['name']: l['@id'] for l in db.list_all('/api/storage_locations')}
    for name, desc, cat, lots in ITEMS:
        old = parts.get(name)
        p = old or {'name': name, 'desc': desc, 'cat': cat, 'lots': []}
        target = assign(p)
        if target not in locs:
            print(f'!! {name}：分不到格子（{target}），跳过')
            continue
        if old is None:
            piri = db.post('/api/parts', {'name': name, 'description': desc, 'tags': '淘宝',
                                          'category': db.ensure_path('/api/categories', cat.split('/'))})['@id']
            have = set()
        else:
            piri = old['iri']
            have = {d['description'] for d in db.get(piri).get('partLots') or []}
        for qty, lot_desc in lots:
            if lot_desc in have:
                continue
            db.post('/api/part_lots', {'part': piri, 'storage_location': locs[target],
                                       'amount': float(qty), 'description': lot_desc})
            print(f'{"新建" if old is None else "加批次"}  {name} ×{qty}  → {target}  （{lot_desc}）')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main('--apply' in sys.argv)
