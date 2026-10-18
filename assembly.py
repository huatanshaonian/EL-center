"""
MIS-01 整机布局装配（布局 E11）
全局坐标：X 向右(宽)、Y 由前向后(深)、Z 向上；竖直前面板外表面 Y=-2，框架前沿 Y=0。
框架外形 320(W) x 220(D) x 420(H)，2020 型材；底部斜面与键盘座向前探出约 45（见 assembly_panel.py）。
公共尺寸/配色/零件表在 assembly_base.py。
"""
import cadquery as cq
import parts as P
import parts_modules as M
import parts_panel as F
import assembly_panel as AP
from assembly_base import W, D, H, Z_DECK, Z_SHELF, Z_SCREEN, ITEMS, add, to_min

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
    add("base_plate_3mm", P.plate(W, D, 3).translate((0, 0, -3)), "dark", "plates")
    deck = P.plate(W - 4, D - 24, 2, notches=((0, 0, 18, 18), (W - 4 - 18, 0, 18, 18)))
    add("deck_plate_2mm", deck.translate((2, 2, Z_DECK)), "alu", "plates")
    add("shelf_plate_2mm", P.plate(W - 4, D - 52, 2).translate((2, 30, Z_SHELF)), "alu", "plates")
    vents = [(40 + i * 20, 60 + j * 20, 8) for i in range(13) for j in range(6)]
    add("top_plate_2mm_vented", P.plate(W, D, 2, holes=vents).translate((0, 0, H)), "panel", "top")

# ------------------------------------------------------------------ EL 屏
def screen():
    sx0 = (W - 267) / 2
    add("Sharp_LJ64K052", P.lj64k052().translate((sx0, 3, Z_SCREEN)), "glass_el", "core")
    brk = P.el_bracket()
    add("EL_bracket_L", brk.translate((20, 0, Z_SCREEN + 5)), "alu", "mech")
    add("EL_bracket_R", brk.mirror("YZ").translate((W - 20, 0, Z_SCREEN + 5)), "alu", "mech")

# ------------------------------------------------------------------ 管龛（甲板上）：IN-14 一排，IV-18 横在其正下方
TUBE_X = [35, 57, 84, 106, 133, 155]          # 6 支 IN-14 管心，HH:MM:SS 分组（管龛窗 x 22..170）
Y_TUBE = 27                                    # IN-14 管轴距框架前沿（引线向下伸到 108.8，须在 IV-18 后面）
Y_IV18 = 11                                    # IV-18 管轴（玻壳前沿离面板内表面 1.5）
Z_IN14_PCB = 116                               # IN-14 管座板底面（IV-18 顶在 114 以下）
IV18_X0 = 27                                   # IV-18 引线端玻壳中心 X（玻壳到 X=142）
Z_IV18_PCB = Z_DECK + 3                        # IV-18 板底面，管心 Z=104.6
EYE_Y = 27                                     # 6E2 管轴 Y（让开前面的 SBM-20）
SBM_Y, SBM_Z, SBM_X0 = 8, 103.5, 184           # SBM-20 管轴

def tubes():
    sock = P.in14_socket_pcb()
    for k, x in enumerate(TUBE_X):
        add(f"IN14_socket_PCB_{k+1}", sock.translate((x - 11, Y_TUBE - 12, Z_IN14_PCB)), "pcb_b", "tubes")
        for xx in (x - 6, x + 6):
            add("standoff_M3x24", P.standoff_m3(Z_IN14_PCB - Z_DECK - 2).translate((xx, Y_TUBE + 22, Z_DECK + 2)), "brass", "tubes")
        add(f"IN-14_{k+1}", P.in14().translate((x, Y_TUBE, Z_IN14_PCB + 1.6 + 4)), "nixie", "tubes")
    # IV-18：板直接用尼龙垫片坐在甲板上，支架托住管子
    add("IV18_PCB", P.iv18_pcb().translate((IV18_X0 - 5, Y_IV18 - 9, Z_IV18_PCB)), "pcb_b", "tubes")
    add("IV-18", P.iv18().translate((IV18_X0, Y_IV18, Z_IV18_PCB + 11.6)), "vfd", "tubes")
    # 驱动板 + 6xK155ID1 + NCH6100HV + 防护罩
    zb = Z_DECK + 2 + 8
    add("tube_driver_board", P.tube_driver_board().translate((20, 60, zb)), "pcb_g", "tubes")
    for k in range(6):
        add(f"K155ID1_{k+1}", P.dip16().translate((28 + k * 22, 70, zb + 1.6)), "chip", "tubes")
    add("NCH6100HV", P.nch6100hv().translate((145, 85, zb + 1.6 + 8.5)), "module", "tubes")
    add("HV_cover_acrylic_tubes", P.hv_cover(168, 78, 40).translate((16, 56, Z_DECK + 2)), "acrylic", "covers")
    add("IV18_PSU(envelope)", P.hv_module(40, 30, 15).translate((215, 90, Z_DECK + 2 + 6)), "module", "tubes")
    # 6E2 ×2：管座在甲板上，管子竖立在前面板竖窗后
    for k, x in enumerate(AP.EYE_X):
        add(f"Noval_socket_{k+1}", M.noval_socket().translate((x, EYE_Y, Z_DECK + 2 + 10)), "dark", "tubes")
        add(f"6E2_{k+1}", M.tube_6e2().translate((x, EYE_Y, Z_DECK + 2 + 10)), "eye", "tubes")

# ------------------------------------------------------------------ 盖革：SBM-20 横在前面板开窗后，盖革板在甲板上
def geiger():
    add("SBM-20", M.sbm20().translate((SBM_X0, SBM_Y, SBM_Z)), "geiger", "geiger")
    for x in (SBM_X0 + 1, SBM_X0 + 108 - 5):                  # 端帽夹（T）
        add("SBM20_clip", P.box(4, 10, SBM_Z - 5.5 - Z_DECK - 2, x, SBM_Y - 5, Z_DECK + 2), "alu", "geiger")
    for x, y in ((189.5, 41.5), (242.5, 41.5), (189.5, 74.5), (242.5, 74.5)):
        add("standoff_M3x5", P.standoff_m3(5).translate((x, y, Z_DECK + 2)), "brass", "geiger")
    add("Geiger_board", M.geiger_board().translate((186, 38, Z_DECK + 2 + 5)), "pcb_b", "geiger")

# ------------------------------------------------------------------ 下舱：电源、配电、喇叭
def lower():
    add("MeanWell_LRS-150-24", P.lrs150_24().translate((25, 100, 0)), "psu", "power")
    # 市电端子防护罩（亚克力 3 mm 罩帽，跨在 PSU 端子端，用 PSU 侧面 M3 孔经角片固定）
    t = 3
    hood = (P.box(46, 104, t, 160, 96, 40 - t)            # 顶
            .union(P.box(t, 104, 40, 203, 96, 0))            # 外侧壁
            .union(P.box(19, t, 40, 184, 96, 0)).union(P.box(19, t, 40, 184, 197, 0))
            .union(P.box(24, t, 10 - t, 160, 96, 30)).union(P.box(24, t, 10 - t, 160, 197, 30)))
    add("Mains_hood_acrylic", hood, "acrylic", "covers")
    pb = to_min(P.power_board().rotate((0, 0, 0), (0, 0, 1), 90), 212, 66, 10)
    add("24V_power_board", pb, "pcb_g", "power")
    for x, y in ((288, 70), (288, 192), (216, 70), (216, 192)):
        add("standoff_M3x10", P.standoff_m3(10).translate((x, y, 0)), "brass", "power")
    add("NID100-05", to_min(P.nid100_05().rotate((0, 0, 0), (0, 0, 1), 90), 220, 120, 11.6 - 4.5), "module", "power")
    add("NID65-12", to_min(P.nid65_12().rotate((0, 0, 0), (0, 0, 1), 90), 238, 120, 11.6 - 4.5), "module", "power")
    # 喇叭暗装：贴在左侧下层型材之间，朝开放的左侧面发声
    add("Speaker_40mm", F.speaker_40().rotate((0, 0, 0), (0, 0, 1), -90).translate((22, 50, 45)), "dark", "power")

# ------------------------------------------------------------------ 电脑层
def computers():
    zs = Z_SHELF + 2
    opi = to_min(P.orangepi4().rotate((0, 0, 0), (0, 0, 1), 90), 32, 106, zs + 10)
    for x, y in ((84.5, 109.5), (84.5, 167.5), (35.5, 109.5), (35.5, 167.5)):
        add("standoff_M3x10", P.standoff_m3(10).translate((x, y, zs)), "brass", "compute")
    add("OrangePi_4", opi, "opi", "compute")
    dock = P.tang20k_dock().translate((150, 112, zs + 10))        # 官方 Dock 模型已含插好的核心板
    add("Tang_Primer_20K_Dock+Core", dock, "pcb_b", "compute")
    for x, y in ((154, 116), (241, 116), (154, 181), (241, 181)):   # 板 95x73，孔距 87x65（孔为 M2.5，铜柱待换 M2.5）
        add("standoff_M3x10", P.standoff_m3(10).translate((x, y, zs)), "brass", "compute")

# ------------------------------------------------------------------ 后面板 + 风扇
def rear():
    cut = [(30, Z_SHELF + 12, 80, 22), (146, Z_SHELF + 10, 102, 24),   # 电脑接口窗（Dock 接口占 X 147..245）
           (265, 30, 28, 48)]                                         # IEC C14 带开关插座（预留）
    holes = [(cx + sx * 25, 340 + sz * 25, 4.4) for cx in (100, 220) for sx in (-1, 1) for sz in (-1, 1)]
    holes += [(cx, 340, 56) for cx in (100, 220)]
    holes += [(10, z, 4.5) for z in (10, 210, 410)] + [(W - 10, z, 4.5) for z in (10, 210, 410)]
    holes += [(x, 40, 6.5) for x in (225, 247)]                        # 后 SMA ×2 预留
    add("rear_panel_2mm", P.panel(W, H, 2, cut, holes).translate((0, D, 0)), "panel", "rear")
    for cx in (100, 220):
        add("fan_60x15", P.fan(60, 15).translate((cx, D - 15, 340)), "dark", "rear")

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
