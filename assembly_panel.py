"""
MIS-01 装配 —— 前面板（布局 E11）：竖直前面板、底部斜面及其操作件、底座条、磁吸键盘座与键盘
坐标、数值对应 面板方案.md 第 1、2 节；斜面局部坐标 x=全局 X，u=沿斜面自下沿向上的长度。
"""
import math
import cadquery as cq
import parts as P
import parts_modules as M
import parts_panel as F
import parts_dock as PD
from assembly_base import W, H, Z_DECK, Z_SCREEN, add, place

# ---------------------------------------------------------------- 斜面几何
SLANT_L, SLANT_ANG = 83.0, 33.0                  # 斜面展开长、与竖直面夹角
Z_CHIN = 88.0                                    # 竖直前面板下沿 = 斜面上沿（外表面 Y=-2）
SA, CA = math.sin(math.radians(SLANT_ANG)), math.cos(math.radians(SLANT_ANG))
Y_BASE = -2 - SLANT_L * SA                       # 斜面下沿 / 底座条外表面，约 -47.2（前探 45.2）
Z_BASE = Z_CHIN - SLANT_L * CA                   # 斜面下沿高度，约 18.4（底座条高）

# 斜面器件位置 (x, u)。四组等距 14、右边距放宽到 22：右列长方形键的键体（深约 30）要让开右前立柱（x≥300）
SEL = (37.0, 40)
USB = ((28.0, 10), (46.0, 10))
ENC = ((110.5, 63), (136.5, 63))
FADER_X, FADER_U = 123.5, (40, 18)
TOG_X, TOG_U, LAMP_U = (180.5, 201.5, 222.5), 26, 63
KEY_X, KEY_U = (256.0, 286.0), (63, 40, 18)

# 竖直前面板上的仪表（全局 x, z）
METER = (214, 146)
EYE_X, EYE_WIN = (261, 285), (122, 48)           # 6E2 竖窗中心 x、窗底 z 与窗高
NICHE = (22, 92, 148, 84)                        # 管龛窗 x, z, w, h
SBM_WIN = (180, 94, 116, 19)
SENSOR = (304, 404)

def on_slant(shape, x, u, back=False):
    """面板件（原点=前表面开孔中心，-Y 朝外，+Z 向上）放到斜面 (x,u)；back=True 表示原点在面板背面（如 EC11）"""
    if back:
        shape = shape.translate((0, 2, 0))
    return place(shape, x, Y_BASE + u * SA, Z_BASE + u * CA, rot=(("X", -SLANT_ANG),))

def front_panel():
    sx0 = (W - 267) / 2
    aa_w, aa_h = 211.2, 158.4
    z0 = Z_CHIN
    cut = [(sx0 + (267 - aa_w) / 2 - 2, Z_SCREEN + (220 - aa_h) / 2 - 2, aa_w + 4, aa_h + 4),   # EL 视窗
           NICHE, SBM_WIN]
    cut += [(x - 6, EYE_WIN[0], 12, EYE_WIN[1]) for x in EYE_X]                                # 6E2 竖窗
    holes = [(METER[0], METER[1], 51)] + [(METER[0] + sx * 24, METER[1] + sz * 21, 3.2) for sx in (-1, 1) for sz in (-1, 1)]
    holes += [(SENSOR[0], SENSOR[1], 6)]
    holes += [(x, z, 4.5) for x in (10, W - 10) for z in (140, 280, 410)] + [(x, H - 10, 4.5) for x in (110, 210)]
    cut = [(x, z - z0, w, h) for x, z, w, h in cut]
    holes = [(x, z - z0, d) for x, z, d in holes]
    add("front_panel_2mm", P.panel(W, H - z0, 2, cut, holes).translate((0, -2, z0)), "panel", "front")
    add("Panel_meter_85C1", F.panel_meter().translate((METER[0], -2, METER[1])), "meter", "ui")

def slant():
    cut = [(x - 6.7, u - 3, 13.4, 6) for x, u in USB]
    cut += [(FADER_X - 31, u - 1, 62, 2) for u in FADER_U]
    cut += [(x - 11, u - 8, 22, 16) for x in KEY_X for u in KEY_U]
    holes = [(SEL[0], SEL[1], 10)] + [(x, u, 7.2) for x, u in ENC]
    holes += [(x, TOG_U, 6.2) for x in TOG_X] + [(x, LAMP_U, 8.2) for x in TOG_X]
    sp = P.panel(W - 4, SLANT_L, 2, [(x - 2, u, w, h) for x, u, w, h in cut], [(x - 2, u, d) for x, u, d in holes])
    add("slant_panel_2mm", place(sp, 2, Y_BASE, Z_BASE, rot=(("X", -SLANT_ANG),)), "chin", "front")      # 夹在两侧封板之间
    # 两侧三角封板、底座条、斜面下底板
    pts = [(0, 0), (0, Z_CHIN), (-2, Z_CHIN), (Y_BASE, Z_BASE), (Y_BASE, 0)]
    cheek = cq.Workplane("YZ").polyline(pts).close().extrude(2)
    add("chin_cheek_L", cheek, "chin", "front")
    add("chin_cheek_R", cheek.translate((W - 2, 0, 0)), "chin", "front")
    add("base_strip_2mm", P.panel(W - 4, Z_BASE - 2 * SA, 2).translate((2, Y_BASE, 0)), "panel", "front")   # 顶边让开斜面板内角
    add("chin_bottom_3mm", P.plate(W, -Y_BASE, 3).translate((0, Y_BASE, -3)), "dark", "front")
    # 操作件
    add("Rotary_selector_5pos", on_slant(F.rotary_selector(), *SEL), "knob", "ui")
    for k, (x, u) in enumerate(USB):
        add(f"USB-A_panel_{k+1}", on_slant(F.usb_a_panel(), x, u), "alu", "ui")
    for k, (x, u) in enumerate(ENC):
        add(f"EC11_encoder_{k+1}", on_slant(P.ec11(), x, u, back=True), "knob", "ui")
    for k, (u, pos) in enumerate(zip(FADER_U, (0.7, 0.35))):
        add(f"Fader_60mm_{k+1}", on_slant(F.fader_60(pos), FADER_X, u), "alu", "ui")
    for k, x in enumerate(TOG_X):
        add(f"Toggle_guarded_{k+1}", on_slant(F.toggle_guarded(), x, TOG_U), "guard", "ui")
        add(f"Indicator_lamp_{k+1}", on_slant(F.indicator_lamp(), x, LAMP_U), "alu", "ui")
    key = F.rect_lamp_button()
    for i, u in enumerate(KEY_U):
        for j, x in enumerate(KEY_X):
            add(f"Rect_lamp_button_{i * 2 + j + 1}", on_slant(key, x, u), "lamp", "ui")

def keyboard():
    """底座条前装键盘座，X1 键盘平放在桌面上，连接带贴住舌条"""
    dock = PD.keyboard_dock()                                                  # 暂时竖直放；是否随斜面后仰、背后怎么接机架待定
    y_dock = Y_BASE - PD.SPEC["D"]
    add("Keyboard_dock", dock.translate((W / 2, y_dock, 0)), "dark", "keyboard")
    kb = M.x1_tablet_keyboard()
    add("X1_Tablet_keyboard", kb.translate(((W - 300) / 2, y_dock - 226, 0)), "kbd", "keyboard")

def build():
    front_panel(); slant(); keyboard()
