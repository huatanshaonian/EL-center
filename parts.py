"""
MIS-01 复古终端 —— 零件参数化模型 (CadQuery)
单位 mm。坐标约定（每个零件自己的局部坐标）：
  PCB / 模块类：板底面左前角为原点，X 长、Y 宽、Z 向上（元件面朝 +Z）
  管子类      ：玻壳底部中心为原点，Z 向上（引线向 -Z）
  面板/屏     ：X 宽、Y 深(前→后)、Z 高，前表面在 Y=0
每个函数开头的 SPEC 字典记录尺寸来源： C=已确认(原厂/可靠资料)  T=暂定(待实物测绘)
粗模型原版保存在 _backup_rough_v1/
"""
import math
import cadquery as cq
# 下列零件已换成厂家/开源库的真实 STEP（对齐与来源见 vendor_parts.py），其余仍为本文件的参数化模型
from vendor_parts import (tang20k_core, tang20k_dock, in14, iv18, dip16, lrs150_24, nid100_05, nid65_12,
                          corner_bracket_2020, tnut_m4_slot6, ec11, pushbutton_16, sma_bulkhead, fan)

def box(x, y, z, x0=0, y0=0, z0=0):
    return cq.Workplane("XY").box(x, y, z, centered=False).translate((x0, y0, z0))

def cyl(r, h, x=0, y=0, z=0, axis="Z"):
    w = {"Z": "XY", "Y": "XZ", "X": "YZ"}[axis]
    c = cq.Workplane(w).circle(r).extrude(h)
    if axis == "Y":
        c = c.mirror("XZ")  # XZ 平面法向为 -Y，翻转使其沿 +Y 生长
    return c.translate((x, y, z))

# ---------------------------------------------------------------- 1. 核心器件
def lj64k052():
    """Sharp LJ64K052 10.4" EL 模块（包络模型）。前表面 Y=0，X 宽、Z 高，原点=左下前角"""
    SPEC = dict(L=267, H=220, T=23.5,        # C 规格书 p.12：267±0.5 × 220 × 最大 23.5
                aa_w=211.2, aa_h=158.4,        # T 按 640x480 @0.33 mm 点距推算
                glass_t=3.0,                   # T
                holes=((3.5, 257, 208), (4.4, 238, 187)),   # C 规格书 p.12：两组安装孔（孔径, 横向孔距, 纵向孔距），对中心对称
                comp_half=63)                  # C 背部元件区以中心为界上下各 63
    L, H, T = SPEC["L"], SPEC["H"], SPEC["T"]
    glass = box(L, SPEC["glass_t"], H)                         # 前玻璃
    frame = box(L - 4, 3, H - 4, 2, SPEC["glass_t"], 2)       # 金属框
    pcb = box(L - 10, 1.6, H - 10, 5, SPEC["glass_t"] + 3, 5)  # 驱动板
    ch = SPEC["comp_half"]
    comps = box(L - 40, T - 7.6 - 1.6, 2 * ch, 20, SPEC["glass_t"] + 4.6, H / 2 - ch)   # 背部元件区（高压在此，须防误触）
    body = glass.union(frame).union(pcb).union(comps)
    # 有效显示区（0.2 mm 浅凹，仅作标识）
    aa = box(SPEC["aa_w"], 0.2, SPEC["aa_h"], (L - SPEC["aa_w"]) / 2, 0, (H - SPEC["aa_h"]) / 2)
    body = body.cut(aa)
    # CN5：背面竖直中心线上、中心以下约 59（C 位置；连接器外形 T）
    body = body.union(box(30, 4, 8, L / 2 - 15, T - 4, H / 2 - 59 - 4))
    # 两组安装孔（8 个通孔，原厂说明用其中 4 个）
    for d, px, pz in SPEC["holes"]:
        for sx in (-1, 1):
            for sz in (-1, 1):
                body = body.cut(cyl(d / 2, T + 2, L / 2 + sx * px / 2, -1, H / 2 + sz * pz / 2, "Y"))
    return body

def orangepi4():
    """Orange Pi 4（非 LTS）—— 91x56 已确认，孔位/接口位置暂定"""
    SPEC = dict(L=91, W=56, t=1.6, hole_d=2.75, holes=((3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)))
    L, W, t = SPEC["L"], SPEC["W"], SPEC["t"]
    b = box(L, W, t)
    for x, y in SPEC["holes"]:
        b = b.cut(cyl(SPEC["hole_d"] / 2, 3, x, y, -1))
    b = b.union(box(13, 13, 1.5, 30, 22, t))                     # RK3399
    b = b.union(box(14, 16, 16, L - 18, 2, t))                   # RJ45（伸出 2 mm）
    b = b.union(box(14, 13, 15, L - 13, 21, t))                  # USB3.0
    b = b.union(box(14, 13, 15, L - 13, 38, t))                  # 2xUSB2.0（叠层）
    b = b.union(box(15, 11.5, 6, 20, -1.5, t))                   # HDMI（下沿）
    b = b.union(box(9, 7.5, 3.3, 40, -1, t))                     # Type-C
    b = b.union(box(33, 5, 8.5, 12, W - 7, t))                   # 26pin 母座
    return b

def si3bg():
    """SI-3BG 盖革管：Ø10 x 55，两端金属端帽（端帽长度暂定）"""
    SPEC = dict(D=10, L=55, cap_L=6, cap_D=10.4)  # D,L: C(pocketmagic)；cap: T
    b = cyl(SPEC["D"] / 2, SPEC["L"], axis="X")
    for x in (0, SPEC["L"] - SPEC["cap_L"]):
        b = b.union(cyl(SPEC["cap_D"] / 2, SPEC["cap_L"], x, 0, 0, "X"))
    return b

def sbm21():
    """SBM-21 盖革管：管身 Ø6 x 16，总长 21，触点 5x2"""
    SPEC = dict(D=6, L_body=16, L_total=21, pin_L=2.5, pin_D=2)  # C(pocketmagic)
    b = cyl(SPEC["D"] / 2, SPEC["L_body"], SPEC["pin_L"], 0, 0, "X")
    b = b.union(cyl(SPEC["pin_D"] / 2, SPEC["pin_L"], 0, 0, 0, "X"))
    b = b.union(cyl(SPEC["pin_D"] / 2, SPEC["pin_L"], SPEC["pin_L"] + SPEC["L_body"], 0, 0, "X"))
    return b

# ---------------------------------------------------------------- 2. 电源
def nch6100hv():
    """NCH6100HV 辉光管升压模块：外形 45x37、2xØ2.2 孔取自第三方 LibrePCB 封装（T，官方无尺寸图）；高度 T"""
    SPEC = dict(L=45.0, W=37.0, t=1.6, H=14.0, holes=((2.0, 23.0), (43.0, 23.0)),
                pads=((10.0, 32.75), (10.0, 30.21), (10.0, 27.67), (34.5, 29.66), (34.5, 32.2)))
    s = SPEC
    b = box(s["L"], s["W"], s["t"])
    for x, y in s["holes"]:
        b = b.cut(cyl(1.1, 3, x, y, -1))
    b = b.union(cyl(6, 8, 14, 12, s["t"]))                                                 # 电感
    b = b.union(cyl(5, s["H"] - s["t"], 32, 12, s["t"]))                                   # 高压电解
    for x, y in s["pads"]:                                                                 # 输入 3 针 / 输出 2 针
        b = b.union(box(0.64, 0.64, 8.5, x - 0.32, y - 0.32, -8.5))
    return b

def hv_module(L, W, H):
    """通用高压模块包络（IV-18 电源、盖革高压），暂定"""
    b = box(L, W, 1.6)
    b = b.union(box(L - 6, W - 6, H - 1.6, 3, 3, 1.6))
    return b

def power_board():
    """24 V 配电 + NID 载板（自设计，暂定 130x80）：输入端子、2 路保险、NID100/NID65 插座、输出端子"""
    L, W = 130, 80
    b = box(L, W, 1.6)
    for x, y in ((4, 4), (L - 4, 4), (4, W - 4), (L - 4, W - 4)):
        b = b.cut(cyl(1.6, 3, x, y, -1))
    for k in range(3):                                      # 5.08 端子
        b = b.union(box(10.2, 8, 10, 5 + k * 12, 6, 1.6))
    for k in range(3):                                      # 5x20 保险座
        b = b.union(box(22, 8, 8, 45, 5 + k * 11, 1.6))
    for k in range(4):                                      # 输出端子
        b = b.union(box(10.2, 8, 10, 80 + k * 12, 6, 1.6))
    return b

# ---------------------------------------------------------------- 3. 机械
def profile_2020(length):
    """2020 欧标 6 槽型材（截面简化：槽口 6.2、槽腔 9x3.3、中心孔 Ø4.2），沿 +Z 拉伸"""
    s = cq.Workplane("XY").rect(20, 20, centered=False).extrude(length)
    for ang in (0, 90, 180, 270):
        slot = (box(6.2, 2.0, length, 6.9, 0, 0).union(box(9, 3.3, length, 5.5, 2.0, 0)))
        slot = slot.rotate((10, 10, 0), (10, 10, 1), ang)
        s = s.cut(slot)
    s = s.cut(cyl(2.1, length, 10, 10, 0))
    return s

def standoff_m3(h):
    """M3 六角铜柱（对边 5），母-母"""
    s = cq.Workplane("XY").polygon(6, 5 / math.cos(math.pi / 6)).extrude(h)
    return s.cut(cyl(1.25, h + 2, 0, 0, -1))

# ---------------------------------------------------------------- 4. 自设计件（初版，按布局尺寸）
def el_bracket(back_y=26.5, h=224.0, holes_z=(8.0, 216.0), hole_x=11.5):
    """EL 屏 Z 形托架，2 mm 铝板：一腿贴立柱内侧面（M4 → 锤头螺母），一腿贴屏背面。
    屏用规格书 Ø3.5 那组孔（257×208）：M3 螺丝从屏正面穿过屏和托架，背后螺母锁紧；螺丝头落在屏与前面板之间 3 mm 的空隙里。
    原点 = 贴立柱那条腿的左前下角；back_y = 屏背面离框架前沿的距离；holes_z / hole_x 为屏孔在托架上的位置（左托架，右托架镜像）"""
    t = 2.0
    leg_a = box(t, back_y, h, 0, 0, 0)          # 贴立柱内侧（X 法向）
    leg_b = box(28, t, h, 0, back_y, 0)         # 贴屏背面
    b = leg_a.union(leg_b)
    for z in (20, h / 2, h - 20):
        b = b.cut(cyl(2.2, t + 2, -1, 10, z, "X"))          # M4 → 立柱槽里的锤头螺母
    for z in holes_z:
        b = b.cut(cyl(1.7, t + 2, hole_x, back_y - 1, z, "Y"))   # M3 → 屏 Ø3.5 孔
    return b

def in14_socket_pcb():
    """单管 IN-14 管座小板 21x40x1.6（管距最小 22，留 1 mm 缝方便换板）：管心距前沿 12，13 针 PCD12 插孔；
    底面 2×7 排针（插驱动板排母），后部 1 个 M3 孔锁到驱动板（占位，等 mis-01-56 画板）"""
    p = box(21, 40, 1.6)
    for k in range(13):
        a = 2 * math.pi * k / 13
        p = p.cut(cyl(0.6, 3, 10.5 + 6 * math.cos(a), 12 + 6 * math.sin(a), -1))
    p = p.cut(cyl(1.6, 3, 10.5, 36, -1))
    p = p.union(box(17.8, 5.1, 2.5, 1.6, 27, -2.5))  # 底面 2×7 排针塑料座（针另算）
    return p

def iv18_pcb():
    """IV-18 安装 PCB 130x28：管水平卡在两个支撑上（暂定）"""
    p = box(130, 28, 1.6)
    for x in (4, 126):
        p = p.cut(cyl(1.6, 3, x, 22, -1))
    for x in (20, 100):
        p = p.union(box(4, 14, 10, x, 2, 1.6).cut(cyl(9.6, 6, x - 1, 9, 11.6, "X").translate((0, 0, 0))))
    return p

def tube_driver_board():
    """辉光管驱动板 160x70：6×K155ID1 + 移位寄存器 + 高压模块位"""
    p = box(160, 70, 1.6)
    for x, y in ((4, 4), (156, 4), (4, 66), (156, 66)):
        p = p.cut(cyl(1.6, 3, x, y, -1))
    return p

def geiger_pcb():
    """盖革管 PCB 90x24：SI-3BG + SBM-21 夹具位（保险丝夹式），暂定"""
    p = box(90, 24, 1.6)
    for x in (4, 86):
        p = p.cut(cyl(1.6, 3, x, 20, -1))
    # 管夹（两片簧片夹住管体/端帽）：SI-3BG 占 x4..59（r5.2），SBM-21 占 x64..85（端针 r1）
    for x, r in ((8, 5.4), (52, 5.4), (64.5, 1.2), (82.5, 1.2)):
        for y in (12 - r - 0.8, 12 + r):
            p = p.union(box(2, 0.8, 9, x, y, 1.6))
    return p

def panel(w, h, t=2.0, cutouts=(), holes=()):
    """平板（XZ 平面，厚度沿 +Y）。cutouts: (x,z,w,h) 矩形开窗；holes: (x,z,d)"""
    p = box(w, t, h)
    for x, z, cw, ch in cutouts:
        p = p.cut(box(cw, t + 2, ch, x, -1, z).edges("|Y").fillet(min(cw, ch, 6) / 2 - 0.01) if min(cw, ch) > 6 else box(cw, t + 2, ch, x, -1, z))
    for x, z, d in holes:
        p = p.cut(cyl(d / 2, t + 2, x, -1, z, "Y"))
    return p

def plate(lx, ly, t=2.0, notches=(), holes=()):
    """水平板（XY 平面）"""
    p = box(lx, ly, t)
    for x, y, nw, nh in notches:
        p = p.cut(box(nw, nh, t + 2, x, y, -1))
    for x, y, d in holes:
        p = p.cut(cyl(d / 2, t + 2, x, y, -1))
    return p

def hv_cover(lx, ly, h, t=3.0):
    """亚克力高压防护罩（倒扣盒，带安装耳）"""
    outer = box(lx, ly, h)
    inner = box(lx - 2 * t, ly - 2 * t, h - t, t, t, 0)
    c = outer.cut(inner)
    for x in (-8, lx):
        c = c.union(box(8, 16, t, x, ly / 2 - 8, 0).cut(cyl(1.7, t + 2, x + 4, ly / 2, -1)))
    return c
