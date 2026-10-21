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
import vendor_parts as V
from assembly_base import W, H, Z_DECK, Z_SCREEN, PLATE_T, add, place, to_min

# ---------------------------------------------------------------- 斜面几何
SLANT_L, SLANT_ANG = 83.0, 33.0                  # 斜面展开长、与竖直面夹角
Z_CHIN = 88.0                                    # 竖直前面板下沿 = 斜面上沿（外表面 Y=-2）
SA, CA = math.sin(math.radians(SLANT_ANG)), math.cos(math.radians(SLANT_ANG))
Y_BASE = -2 - SLANT_L * SA                       # 斜面下沿 / 底座条外表面，约 -47.2（前探 45.2）
Z_BASE = Z_CHIN - SLANT_L * CA                   # 斜面下沿高度，约 18.4（底座条高）

# 斜面器件位置 (x, u)。四组等距 14、右边距放宽到 22：右列长方形键的键体（深约 30）要让开右前立柱（x≥300）
SEL = (37.0, 40)
USB = ((30.0, 10), (67.0, 10))                  # 左 USB3（直连 Pi）、右 USB2（来自 Hub）；带耳延长线母头，中心距 ≥37（耳宽 35，T）
PCB_D, PCB_T = 6.5, 1.6                           # 斜面电路板元件面到斜面内表面 6.5（推子贴死面板）
PCB_X, PCB_U = (17.0, 166.0), (0.0, 78.0)         # SLANT D1 外形 x 17–166、u 0–78（下沿两个 USB 缺口，左上 x 17–21 只到 u 64）
SLANT_STEP = "el_driver/SLANT_D1/制板文件/SLANT_D1.step"   # 约 26 MB，不进 git；板原点 = 斜面 (17, 0)，板 +y = u，顶层（元件面）朝面板
ENC = ((98.5, 63), (123.5, 63), (148.5, 63))   # 3 个编码器一排，中心距 25（Ø15 旋钮间隙 10）；2026-10-20 由 2 个改 3 个
FADER_X, FADER_U = 123.5, (40, 24)                # 两根推子间距 16（原 40/18）
TOG_X, TOG_U, LAMP_U = (180.5, 201.5, 222.5), 26, 63
KEY_X, KEY_U = (256.0, 286.0), (63, 40, 18)

# 竖直前面板上的仪表（全局 x, z）
METER = (214, 146)
EYE_X = (261, 285)                               # 6E2 管心 x
EYE_WIN = (248, 118, 50, 56)                     # 6E2 开口 x, z, w, h：上下边与表头面框齐平（z 118–174），表头底边向右延伸成横条，把 6E2 和下面的盖革窗隔开
ACRYLIC_T = 2                                    # 三个开口背后都贴透明亚克力（管龛 170 V、6E2 250 V、盖革管 400 V，手指够不着）
NICHE = (24, 92, 146, 84)                        # 管龛窗 x, z, w, h（左边让出 2 mm 给亚克力贴边，亚克力不能压到左 EL 托架 x 20–22）
SBM_WIN = (180, 94, 118, 19)                     # 盖革窗，右边与 6E2 开口齐平（x 298）
SENSOR = (304, 404)

# 前壳（前面板 + 斜面，一块 2 mm 铝钣金）与下巴托（底板 + 两侧板，一块 2 mm 铝钣金），2026-10-22 用户确认（png/23 方案 + 两件拆法）
SHELL_X0, SHELL_W = -2.0, W + 4.0                # 前面板加宽到 324，左右各盖住下巴托侧板的 2 mm
SIDE_X = (-2.0, W)                               # 两侧板在机架外侧（x −2..0 / 320..322），M4 锁立柱和 Y 梁外侧 T 槽
SIDE_BACK = 75.0                                 # 侧板往后盖到 y 75；左侧板盖住喇叭（y 30–70），开喇叭网孔
SIDE_M4 = ((10, 30), (10, 60), (35, 10), (35, 80), (65, 10), (65, 80))   # 侧板 M4 孔 (y, z)：前立柱 ×2、下层 / 甲板层 Y 梁各 ×2
GRILLE = (50.0, 45.0, 17.0, 3.0, 5.0)            # 左侧板喇叭网：中心 (y, z)、半径、孔径、孔距（六角排）
TRAY_Y0 = -48.0                                  # 下巴托底板前沿（键盘座背面下角 y −47.9 后面）
FLANGE_T, FLANGE_U = 10.0, (8.0, 64.0)           # 斜面两侧翻边：往里 10，沿斜面 u 8–64（再往上翻边后角就伸进前立柱 y > 0）；各 2 个 M3 压铆螺母（u 20 / 56）锁侧板
FLANGE_SCREW_U, FLANGE_SCREW_T = (20.0, 56.0), 6.0
FEET_H = 3.0                                     # 底板下橡胶脚垫

SHELL = []                                       # 前壳的两段（前面板、斜面），build() 里合成一个零件


def on_slant_local(shape):
    """斜面局部坐标（x = 全局 x，Y = 从斜面外表面往里 t，Z = 沿斜面 u）→ 全局"""
    return place(shape, 0, Y_BASE, Z_BASE, rot=(("X", -SLANT_ANG),))


def slant_pt(u, t):
    """斜面局部 (u, t) → 全局 (y, z)"""
    return (Y_BASE + u * SA + t * CA, Z_BASE + u * CA - t * SA)


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
    cut += [EYE_WIN]                                                                         # 6E2 大开口
    holes = [(METER[0], METER[1], 50)] + [(METER[0] + sx * 26, METER[1] - 13, 3.2) for sx in (-1, 1)]   # 85C1：Ø50 + 2×M3（孔距 52）
    holes += [(SENSOR[0], SENSOR[1], 6)]
    holes += [(x, z, 4.5) for x in (10, W - 10) for z in (140, 280, 410)] + [(x, H - 10, 4.5) for x in (110, 210)]
    cut = [(x - SHELL_X0, z - z0, w, h) for x, z, w, h in cut]
    holes = [(x - SHELL_X0, z - z0, d) for x, z, d in holes]
    SHELL.append(P.panel(SHELL_W, H - z0, 2, cut, holes).translate((SHELL_X0, -2, z0)))
    add("Panel_meter_85C1", F.panel_meter().translate((METER[0], -2, METER[1])), "meter", "ui")
    # 透明亚克力（贴在面板背面，VHB 双面胶或 UV 胶）
    # 右：L 形一片盖 6E2 + 盖革两个窗，让开表头螺柱（x 241.5）和右侧 EL 托架（x ≥ 298、z ≥ 176）
    acr = P.box(299 - 178, ACRYLIC_T, 116 - 91, 178, 0, 91).union(P.box(299 - 244, ACRYLIC_T, 175.5 - 91, 244, 0, 91))
    add("Window_acrylic_clear_R", acr, "acrylic", "front")
    # 左：管龛一片，让开左 EL 托架（x 20–22）
    add("Window_acrylic_clear_L", P.box(173 - 22.5, ACRYLIC_T, 179 - 89, 22.5, 0, 89), "acrylic", "front")

def slant():
    cw, ch = F.USB_EXT["cut"]
    cut = [(x - cw / 2, u - ch / 2, cw, ch) for x, u in USB]
    cut += [(FADER_X - 31, u - 1, 62, 2) for u in FADER_U]
    holes = [(SEL[0], SEL[1], 10.1)] + [(SEL[0] + sx * 11, SEL[1], 4.2) for sx in (-1, 1)]       # MFR01：Ø10 + 2 个 Ø4.1 防转孔（距 22）
    holes += [(x + sx * F.USB_EXT["hole_dx"] / 2, u, 3.2) for x, u in USB for sx in (-1, 1)]     # 延长线耳孔
    holes += [(x, u, 16.2) for x in KEY_X for u in KEY_U]                                     # LA16 按钮 Ø16
    holes += [(x, u, 7.2) for x, u in ENC]
    holes += [(x, TOG_U, 6.2) for x in TOG_X] + [(x, LAMP_U, 16.2) for x in TOG_X]
    holes += [(W / 2 + x, PD.SCREW_U, 3.4) for x in PD.SPEC["tongue_x"]]                     # 键盘座舌片 M3 沉头
    sp = P.panel(W, SLANT_L, 2, cut, holes)                                                  # 斜面局部坐标：x = 全局 x，Y = t，Z = u
    for x0 in (0.0, W - 2):                                                                  # 两侧翻边（往里折 90°）
        fl = P.box(2, FLANGE_T, FLANGE_U[1] - FLANGE_U[0], x0, 2, FLANGE_U[0])
        for u in FLANGE_SCREW_U:
            fl = fl.cut(P.cyl(1.7, 4, x0 - 1, 2 + FLANGE_SCREW_T, u, "X"))
        sp = sp.union(fl)
    SHELL.append(on_slant_local(sp))
    # 操作件
    add("Rotary_selector_5pos", on_slant(F.rotary_selector(), *SEL), "knob", "ui")
    for k, (x, u) in enumerate(USB):
        add(("USB3_panel_ext", "USB2_panel_ext")[k], on_slant(F.usb_panel_ext(), x, u), "dark", "ui")
    for k, (x, u) in enumerate(ENC):
        add(f"EC11_encoder_{k+1}", on_slant(P.ec11().translate((0, PCB_D - 4.5, 0)), x, u, back=True), "knob", "ui")   # 本体高 4.5 坐在电路板上
    for k, (u, pos) in enumerate(zip(FADER_U, (0.7, 0.35))):
        add(f"Fader_60mm_{k+1}", on_slant(F.fader_60(pos), FADER_X, u), "alu", "ui")
    for k, x in enumerate(TOG_X):
        add(f"Toggle_guarded_{k+1}", on_slant(F.toggle_guarded(), x, TOG_U), "guard", "ui")
        add(f"Indicator_lamp_{k+1}", on_slant(F.indicator_lamp(), x, LAMP_U), "alu", "ui")
    key = F.rect_lamp_button()
    for i, u in enumerate(KEY_U):
        for j, x in enumerate(KEY_X):
            add(f"Rect_lamp_button_{i * 2 + j + 1}", on_slant(key, x, u), "lamp", "ui")

def _slant_drop(b):
    """SLANT D1 STEP 里不装的实体：模式开关孔里多出来的 Ø34 圆片；EC11 本体和轴（用 P.ec11 自己的模型，带旋钮）"""
    hole_disc = b.xmin > 2 and b.xmax < 38 and b.ymin > 22 and b.ymax < 58 and b.zmin > -0.1 and b.zmax < 1.7
    ec11_top = 74 < b.xmin and b.xmax < 139 and 54 < b.ymin and b.ymax < 72 and b.zmax > 3.8                # 背面阻容最高 3.5
    return hole_disc or ec11_top

def slant_pcb():
    """斜面电路板 SLANT D1（mis-01-56 导出的整板 STEP；Pico、ULN2803、键插座在背面，EC11、推子焊在顶层）：
    元件面到斜面内表面 PCB_D。STEP 绕 X 转 +90°：板 z（顶层朝上）→ 局部 -Y（朝面板），板 y → 局部 Z（= u）"""
    b = V.load_abs_drop(SLANT_STEP, _slant_drop).rotate((0, 0, 0), (1, 0, 0), 90)
    b = b.translate((PCB_X[0], 2 + PCB_D + PCB_T, PCB_U[0]))
    add("SLANT_board", place(b, 0, Y_BASE, Z_BASE, rot=(("X", -SLANT_ANG),)), "pcb_g", "ui")
    # 贴板背面、长边沿 u，中心斜面 (72.5, 45.5)（SLANT D1 U1；STEP 里没有 Pico 模型）；底面贴板、元件面和 USB 座朝里（2026-10-22 改正，原来装反）
    # 待改：USB 口离 USB2 延长线本体只有 5.6 mm 插不进线（png/24、25），mis-01-56 改成转 180°、板边齐斜面电路板上沿，配 90° 弯头线
    pico = M.rpi_pico().rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 1, 0), 90).rotate((0, 0, 0), (0, 0, 1), 180)
    pico = to_min(pico, 62, 2 + PCB_D + PCB_T, 20)                                              # 让开模式开关孔、USB 缺口、编码器和推子焊脚
    add("RPi_Pico(on_slant_PCB)", place(pico, 0, Y_BASE, Z_BASE, rot=(("X", -SLANT_ANG),)), "pcb_g", "ui")

def chin_tray():
    """下巴托：底板（x −2..322、y TRAY_Y0..0、z −2..0）+ 两侧板（底板两边往上折）+ 底板后边往上折 18 锁前下横梁（M4 ×3）。
    侧板外形：沿斜面外表面线往下到键盘座底面前角，再沿键盘座底面到背面下角；往后盖到 y SIDE_BACK、往上到 z Z_CHIN"""
    dh, dd = PD.SPEC["H"], PD.SPEC["D"]
    pts = [(TRAY_Y0, -2), (SIDE_BACK, -2), (SIDE_BACK, Z_CHIN), (-2, Z_CHIN), slant_pt(-dh, 0), slant_pt(-dh, dd)]
    side = cq.Workplane("YZ").polyline(pts).close().extrude(2)
    for y, z in SIDE_M4:
        side = side.cut(P.cyl(2.25, 4, -1, y, z, "X"))
    for u in FLANGE_SCREW_U:                                                        # 斜面翻边 M3
        y, z = slant_pt(u, 2 + FLANGE_SCREW_T)
        side = side.cut(P.cyl(1.7, 4, -1, y, z, "X"))
    for z in PD.SPEC["end_holes_z"]:                                                # 键盘座两端 M3
        y, zz = slant_pt(z - dh, PD.SPEC["end_hole_y"])
        side = side.cut(P.cyl(1.7, 4, -1, y, zz, "X"))
    gy, gz, gr, gd, gp = GRILLE
    left = side
    for i in range(-5, 6):
        for j in range(-5, 6):
            y, z = gy + gp * (i + 0.5 * (j % 2)), gz + gp * 0.866 * j
            if (y - gy) ** 2 + (z - gz) ** 2 <= gr ** 2:
                left = left.cut(P.cyl(gd / 2, 4, -1, y, z, "X"))
    tray = P.box(SHELL_W, -TRAY_Y0, 2, SHELL_X0, TRAY_Y0, -2)
    back = P.box(W, 2, 18, 0, -2, 0)
    for x in (60, W / 2, W - 60):
        back = back.cut(P.cyl(2.25, 4, x, -3, 10, "Y"))
    tray = tray.union(back).union(left.translate((SIDE_X[0], 0, 0))).union(side.translate((SIDE_X[1], 0, 0)))
    add("chin_tray_alu", tray, "chin", "front")


def keyboard():
    """键盘座随斜面后仰：屏幕面与斜面外表面共面、顶面顶住斜面下沿；X1 键盘连接条（5 mm，用户实测）吸在座子底面，键盘平放在桌面"""
    dh = PD.SPEC["H"]
    to_slant = lambda shp: on_slant_local(shp.translate((W / 2, 0, -dh)))
    add("Keyboard_dock", to_slant(PD.keyboard_dock()), "dark", "front")
    add("Keyboard_dock_cover", to_slant(PD.keyboard_dock_cover()), "dark", "front")
    spine_t, spine_l = 5.0, 280.0
    spine = P.box(spine_l, PD.SPEC["D"], spine_t, W / 2 - spine_l / 2, 0, -dh - spine_t)
    add("X1_keyboard_spine", on_slant_local(spine), "kbd", "keyboard")
    desk = -PLATE_T - FEET_H
    y_back = slant_pt(-dh - spine_t, 0)[0] - 2                                      # 键盘后沿在连接条前下角前面
    add("X1_Tablet_keyboard", M.x1_tablet_keyboard().translate(((W - 300) / 2, y_back - 226, desk)), "kbd", "keyboard")
    for x in (15, W - 15):                                                          # 橡胶脚垫 Ø15
        for y in (15, 205):
            add("rubber_foot", P.cyl(7.5, FEET_H, x, y, desk), "dark", "plates")

def build():
    SHELL.clear()
    front_panel(); slant(); slant_pcb(); chin_tray(); keyboard()
    add("front_shell_alu", SHELL[0].union(SHELL[1]), "panel", "front")      # 前面板 + 斜面：一块铝板折 33°
