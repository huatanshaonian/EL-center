"""
MIS-01 整机布局装配（布局 E11；Orange Pi 4、FPGA Dock 暂作未安装模块，不在总装内）
全局坐标：X 向右(宽)、Y 由前向后(深)、Z 向上；竖直前面板外表面 Y=-2，框架前沿 Y=0。
框架外形 320(W) x 220(D) x 420(H)，2020 型材；底部斜面与键盘座向前探出约 45（见 assembly_panel.py）。
公共尺寸/配色/零件表在 assembly_base.py。
"""
import cadquery as cq
import parts as P
import parts_modules as M
import parts_panel as F
import assembly_panel as AP
import vendor_parts as V
from assembly_base import W, D, H, Z_DECK, Z_SHELF, Z_SCREEN, PLATE_T, ITEMS, add, to_min

# ------------------------------------------------------------------ 框架
def frame():
    for i, (x, y) in enumerate(((0, 0), (W - 20, 0), (0, D - 20), (W - 20, D - 20))):
        add(f"2020_post_L{H}_{i+1}", P.profile_2020(H).translate((x, y, 0)), "alu", "frame")
    xr = P.profile_2020(W - 40)
    for tag, y, z in (("FB", 0, 0), ("FT", 0, H - 20), ("RB", D - 20, 0), ("RT", D - 20, H - 20)):
        add(f"2020_Xrail_L{W-40}_{tag}", to_min(xr.rotate((0, 0, 0), (0, 1, 0), 90), 20, y, z), "alu", "frame")
    yr = P.profile_2020(D - 40)
    for tag, z in (("bot", 0), ("deck", Z_DECK - 20), ("shelf", Z_SHELF - 20), ("top", H - 20)):
        for side, x in (("L", 0), ("R", W - 20)):
            add(f"2020_Yrail_L{D-40}_{tag}_{side}", to_min(yr.rotate((0, 0, 0), (1, 0, 0), -90), x, 20, z), "alu", "frame")
    # 甲板/电脑层型材端部角码（其余接头建议用端面攻丝 M5 或隐藏角码）
    br = P.corner_bracket_2020().mirror("XY")            # 水平腿朝上；17 宽在型材上居中，1 mm 定位凸台嵌入槽口
    for z in (Z_DECK - 20, Z_SHELF - 20):
        for x in (0, W - 20):
            add("corner_bracket", to_min(br, x + 1.5, 19, z - 20), "alu", "frame")
            add("corner_bracket", to_min(br.mirror("XZ"), x + 1.5, D - 40, z - 20), "alu", "frame")
    # 底板 / 甲板（前伸到 Y=2 托住管龛，前角避让立柱）/ 电脑层板 / 顶板
    add("base_plate_bakelite", P.plate(W, D, PLATE_T).translate((0, 0, -PLATE_T)), "bakelite", "plates")
    deck = P.plate(W - 4, D - 24, PLATE_T, notches=((0, 0, 18, 18), (W - 4 - 18, 0, 18, 18)))
    add("deck_plate_bakelite", deck.translate((2, 2, Z_DECK)), "bakelite", "plates")
    add("shelf_plate_bakelite", P.plate(W - 4, D - 52, PLATE_T).translate((2, 30, Z_SHELF)), "bakelite", "plates")
    vents = [(40 + i * 20, 60 + j * 20, 8) for i in range(13) for j in range(6)]
    add("top_plate_bakelite_vented", P.plate(W, D, PLATE_T, holes=vents).translate((0, 0, H)), "bakelite", "top")

# ------------------------------------------------------------------ EL 屏
def screen():
    sx0 = (W - 267) / 2
    add("Sharp_LJ64K052", P.lj64k052().translate((sx0, 3, Z_SCREEN)), "glass_el", "core")
    # 托架：贴屏背面，用屏的 Ø3.5 孔（257×208）锁 M3；托架上沿顶到前上横梁下面（Z=400）
    z0 = Z_SCREEN - 2
    brk = P.el_bracket(back_y=3 + 23.5, h=224.0, holes_z=(Z_SCREEN + 6 - z0, Z_SCREEN + 214 - z0), hole_x=sx0 + 5 - 20)
    add("EL_bracket_L", brk.translate((20, 0, z0)), "alu", "mech")
    add("EL_bracket_R", brk.mirror("YZ").translate((W - 20, 0, z0)), "alu", "mech")

# ------------------------------------------------------------------ 管龛（甲板上）：IN-14 一排，IV-18 横在其正下方
TUBE_X = [35, 57, 84, 106, 133, 155]          # 6 支 IN-14 管心，HH:MM:SS 分组（管龛窗 x 22..170）
Y_TUBE = 27                                    # IN-14 管轴距框架前沿（引线向下伸到 108.8，须在 IV-18 后面）
Y_IV18 = 12                                    # IV-18 管轴（玻壳前沿 y 2.5，让开面板背面 2 mm 亚克力）
Z_DRV = Z_DECK + PLATE_T + 10                  # 辉光驱动板底面：M3×10 铜柱立在甲板上
Z_IN14_PCB = Z_DRV + 1.6 + 11                  # IN-14 小板底面 116.6：2×7 排母 8.5 + 排针塑料座 2.5 插在驱动板上（IV-18 顶 114；管顶 174.7，EL 托架下沿 176）
DRV = (20, 40, 150, 80)                        # 辉光驱动板占位 x0, y0, 长, 宽（未画）
HVUNI_STEP = "el_driver/HV-UNI_D1/制板文件/HV-UNI_D1.step"   # 通用高压小板 80×40（mis-01-56），不进 git
HVUNI_STACK = 11                               # 排针插宿主板排母，叠高 11，四角 M3×11 铜柱
EYE_STANDOFF = 6                               # 6E2 板铜柱 M3×6：管座顶面 z 111.6，管顶 173.6（托架下沿 176）
IV18_X0 = 27                                   # IV-18 引线端玻壳中心 X（玻壳到 X=142）
Z_IV18_PCB = Z_DECK + PLATE_T + 1                        # IV-18 板底面，管心 Z=104.6
EYE_Y = 31                                     # 6E2 管轴 Y：管座前耳孔在 y≈18，6E2 板前沿 ≥ y 13，才能从 J305（y ≤ 11.6 @ 板高）上方让开（2026-10-20 由 27 后移）
EYE_ROT = 18                                   # 6E2 管座绕 Z 转角：荧光屏正对 7 脚、正对 -Y（前面板）时，缺口在 +X 往后偏 18°（北京 6E2，用户确认缺口在右）
SBM_Y, SBM_Z, SBM_X0 = 8, 103.5, 186           # 盖革管 J305 管轴 y、z 与左端 x（变量名沿用 SBM_）；管轴 z 由夹子小板 2 mm 垫 + 夹口高 5.9 决定
GM_L = 103.5                                   # J305 总长（用户实测）
GEIGER_BOARD = (180, 110, 60, 40)              # 盖革主板 x0, y0, 长, 宽：6E2 板后面，四孔落在甲板孔阵（185/235, 115/145），M3×6 铜柱（2026-10-20 由 y 50 后移给 6E2 板让位）
EYE_BOARD = (210, 15, 90, 90)                  # 6E2 板 x0, y0, 长, 宽：前沿 y 15 让开 J305 和右夹子小板，后沿 y 105 让开右后走线孔（y ≥ 120），右沿 x 300；M3×6 铜柱，四角孔都要自己钻
PCB3_STEP = "el_driver/PWR-DIST_D1/制板文件/PWR-DIST_D1.step"   # 约 59 MB，不进 git
PCB3_XY = (80, 160)                            # 倒挂后板的左边 x、后边 y（板占 x 80–230、y 60–160）
PCB3_STANDOFF = 10


def hv_uni(name, x, y, rot, z_host):
    """通用高压小板：板坐标原点（左下角）转 rot 度后放到 (x, y)，板底面 = 宿主板顶面 + 叠高；四角 M3 铜柱"""
    def place(shp):
        return shp.rotate((0, 0, 0), (0, 0, 1), rot).translate((x, y, z_host))
    add(name, place(V.load_abs(HVUNI_STEP).translate((0, 0, HVUNI_STACK))), "pcb_g", "tubes")
    for hx, hy in ((5, 5), (75, 5), (5, 35), (75, 35)):
        add(f"standoff_M3x{HVUNI_STACK}_HV", place(P.standoff_m3(HVUNI_STACK).translate((hx, hy, 0))), "brass", "tubes")


def tubes():
    sock = P.in14_socket_pcb()
    for k, x in enumerate(TUBE_X):
        add(f"IN14_socket_PCB_{k+1}", sock.translate((x - 10.5, Y_TUBE - 12, Z_IN14_PCB)), "pcb_b", "tubes")
        add(f"IN-14_{k+1}", P.in14().translate((x, Y_TUBE, Z_IN14_PCB + 1.6 + 4)), "nixie", "tubes")
    # 辉光驱动板（K155ID1×6 + 74HCT595×3 + 高压小板插座）：6 块 IN-14 小板用 2×7 排针插在它前沿，每块再用 1 颗 M3 锁住
    x0, y0, l, w = DRV
    add("Nixie_driver_PCB(placeholder)", P.box(l, w, 1.6, x0, y0, Z_DRV), "pcb_b", "tubes")
    for xx, yy in ((x0 + 5, y0 + w - 5), (x0 + l - 5, y0 + w - 5), (70.5, y0 + 5), (119.5, y0 + 5)):   # 后两角 + 前沿两个分组空隙
        add("standoff_M3x10", P.standoff_m3(10).translate((xx, yy, Z_DECK + PLATE_T)), "brass", "tubes")
    # 170 V 高压小板插在驱动板后右（避开前沿 IN-14 小板），板占 x 85–165、y 77–117
    hv_uni("HV-UNI_170V", 85, 77, 0, Z_DRV + 1.6)
    # IV-18：板直接用尼龙垫片坐在甲板上，支架托住管子
    add("IV18_PCB", P.iv18_pcb().translate((IV18_X0 - 5, Y_IV18 - 9, Z_IV18_PCB)), "pcb_b", "tubes")
    add("IV-18", P.iv18().translate((IV18_X0, Y_IV18, Z_IV18_PCB + 11.6)), "vfd", "tubes")
    add("IV18_PSU(envelope)", P.hv_module(40, 30, 15).translate((215, 166, Z_DECK + PLATE_T + 6)), "module", "tubes")
    # 6E2 ×2：管座在甲板上，管子竖立在前面板竖窗后
    for k, x in enumerate(AP.EYE_X):
        z = Z_DECK + PLATE_T + EYE_STANDOFF + 1.6 + 10                                   # 6E2 板还没画，只按铜柱 + 板厚抬高管座
        rz = lambda s: s.rotate((0, 0, 0), (0, 0, 1), EYE_ROT).translate((x, EYE_Y, z))
        add(f"Noval_socket_{k+1}", rz(M.noval_socket()), "dark", "tubes")
        add(f"6E2_{k+1}", rz(M.tube_6e2()), "eye", "tubes")
    # 6E2 板占位（mis-01-56 画）
    ex, ey, el, ew = EYE_BOARD
    ze = Z_DECK + PLATE_T + EYE_STANDOFF
    add("EYE-6E2_board(placeholder)", P.box(el, ew, 1.6, ex, ey, ze), "pcb_g", "tubes")
    for dx, dy in ((5, 5), (el - 5, 5), (5, ew - 5), (el - 5, ew - 5)):
        add("standoff_M3x6_EYE", P.standoff_m3(EYE_STANDOFF).translate((ex + dx, ey + dy, Z_DECK + PLATE_T)), "brass", "tubes")
    # 250 V 高压小板横放在 6E2 板上、两支管子后面（不转向，HV 输出在右端靠近管子），板占 x 215–295、y 50–90
    hv_uni("HV-UNI_250V", 215, 50, 0, ze + 1.6)

# ------------------------------------------------------------------ 盖革：J305 横在前面板盖革窗后；自制盖革板（参考 MightyOhm），位置待定
def geiger():
    add("J305", M.j305(GM_L).translate((SBM_X0, SBM_Y, SBM_Z)), "geiger", "geiger")
    # 两块夹子小板（20×12，2 mm 尼龙垫在甲板上，1 颗 M3 走长槽）：夹子中心对准两端电极，长槽朝外
    e = (GM_L - 94) / 2
    clip = M.geiger_clip_board()
    zc = Z_DECK + PLATE_T + 2
    add("Geiger_clip_board_L", clip.mirror("YZ").translate((SBM_X0 + e / 2 + 10, SBM_Y - 6, zc)), "pcb_g", "geiger")
    add("Geiger_clip_board_R", clip.translate((SBM_X0 + GM_L - e / 2 - 10, SBM_Y - 6, zc)), "pcb_g", "geiger")
    # 盖革主板（升压、蜂鸣器、J1 XH-2P 接 HV-C、J2 XH-4P 接 ESP32 底板）：占位，等 mis-01-56 画板
    gx, gy, gl, gw = GEIGER_BOARD
    add("Geiger_main_board(placeholder)", P.box(gl, gw, 1.6, gx, gy, Z_DECK + PLATE_T + 6), "pcb_g", "geiger")
    for dx, dy in ((5, 5), (gl - 5, 5), (5, gw - 5), (gl - 5, gw - 5)):
        add("standoff_M3x6", P.standoff_m3(6).translate((gx + dx, gy + dy, Z_DECK + PLATE_T)), "brass", "geiger")

# ------------------------------------------------------------------ 下舱：电源、配电、喇叭
def lower():
    # LRS-200-24 靠后放，端子在右端（靠近 IEC 插座）；机内可用空间见 free_space.py
    px, py, pl, pw = 22, 83, 215, 115
    add("MeanWell_LRS-200-24", M.lrs200_24().translate((px, py, 0)), "psu", "power")
    # PCB-3 电源板（PWR-DIST D1，150×100，mis-01-56 导出的 STEP）：元件朝下倒挂在甲板下，M3×10 铜柱，四孔落在甲板孔阵上；
    # 绕 X 转 180°，+x 的 J_24V 仍朝 LRS 输出端；元件最低 z 51，离 LRS 顶 21（2026-10-20 用户确认）
    z = Z_DECK - PCB3_STANDOFF
    add("PCB-3_PWR-DIST", V.load_abs(PCB3_STEP).rotate((0, 0, 0), (1, 0, 0), 180).translate((PCB3_XY[0], PCB3_XY[1], z)), "pcb_g", "power")
    for dx, dy in ((5, 5), (145, 5), (5, 95), (145, 95)):
        add("standoff_M3x10_PCB3", P.standoff_m3(PCB3_STANDOFF).translate((PCB3_XY[0] + dx, PCB3_XY[1] - dy, z)), "brass", "power")
    # 市电端子防护罩（亚克力 3 mm 罩帽，罩住电源右端端子，用电源侧面 M3 孔经角片固定）
    t, hx, hy, hl, hw, hh = 3, px + pl - 24, py - 2, 46, pw + 4, 40
    hood = (P.box(hl, hw, t, hx, hy, hh - t)                                   # 顶
            .union(P.box(t, hw, hh, hx + hl - t, hy, 0))                        # 外侧壁
            .union(P.box(hl - 24, t, hh, hx + 24, hy, 0)).union(P.box(hl - 24, t, hh, hx + 24, hy + hw - t, 0))
            .union(P.box(24, t, 10 - t, hx, hy, 30)).union(P.box(24, t, 10 - t, hx, hy + hw - t, 30)))
    add("Mains_hood_acrylic", hood, "acrylic", "covers")
    # 喇叭暗装：贴在左侧下层型材之间，朝开放的左侧面发声
    add("Speaker_40mm", F.speaker_40().rotate((0, 0, 0), (0, 0, 1), -90).translate((22, 50, 45)), "dark", "power")

# ------------------------------------------------------------------ 电脑层
# Orange Pi 4 和 Tang Primer 20K Dock 暂不定位置，作为未安装模块处理（单件 STEP 见 P04 / P03）。
# 等第一版自制 PCB 出来后，与各板一起重新布置；后面板接口窗也随之再开。
def computers():
    pass

# ------------------------------------------------------------------ 后面板
def rear():
    IEC = (276.0, 54.0)                                               # AC-14-F12 开孔中心；耳孔 x 256 / 296，螺母让开右后立柱（x ≥ 300）
    cut = [(IEC[0] - 14, IEC[1] - 30, 28, 60)]                        # IEC C14 三合一开孔 28x60；电脑接口窗待板子定位后再开
    holes = [(cx, 340, 56) for cx in (100, 220)]                       # 原 60 风扇位，2026-10-20 不装风扇，留作通风孔
    holes += [(IEC[0] + sx * 20, IEC[1], 3.5) for sx in (-1, 1)]     # 电源座耳孔 M3
    holes += [(10, z, 4.5) for z in (10, 210, 410)] + [(W - 10, z, 4.5) for z in (10, 210, 410)]
    holes += [(x, 40, 6.5) for x in (225, 247)]                        # 后 SMA ×2 预留
    add("rear_panel_2mm", P.panel(W, H, 2, cut, holes).translate((0, D, 0)), "panel", "rear")
    add("IEC_C14_AC-14-F12", F.iec_c14_inlet().rotate((0, 0, 0), (0, 0, 1), 180).translate((IEC[0], D + 2, IEC[1])), "dark", "rear")

def build():
    ITEMS.clear()
    frame(); screen(); AP.build(); tubes(); geiger(); lower(); computers(); rear()
    return ITEMS

if __name__ == "__main__":
    import os, collections
    items = build()
    assy = cq.Assembly(name="MIS-01")
    names = collections.Counter()
    for name, shp, col, grp in items:
        names[name] += 1
        nm = name if names[name] == 1 else f"{name}_{names[name]}"
        assy.add(shp, name=nm, color=cq.Color(*col))
    os.makedirs("step", exist_ok=True)
    assy.export("step/MIS-01_layout_assembly.step")
    print("parts:", len(items))
