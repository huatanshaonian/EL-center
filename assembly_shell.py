"""
MIS-01 外壳钣金件（2 mm 5052 铝，嘉立创钣金）：前壳（前面板 + 斜面）、下巴托（底板 + 两侧板）。
按嘉立创钣金规则建成真实折弯：2 mm 板外 R 3.7、内 R 1.7（嘉立创 Sheet Metal Fabrication Guidelines 2.4 表）；
翻边比所在边短的地方开 1 mm 折弯让位口。嘉立创要折好弯的 3D STEP（自己展开），不收展开图，见 export_enclosure.py。
坐标、开孔都来自 assembly_panel（FEATURES 由 front_panel()、slant() 先填好）。
"""
import math
import cadquery as cq
import parts as P
import parts_dock as PD
import assembly_panel as AP
from assembly_base import W, H, add

T, RI = 2.0, 1.7                     # 板厚、内折弯半径
RO = RI + T                          # 外折弯半径 3.7
RELIEF = 1.0                         # 折弯让位口宽
D_TAN = RI * math.tan(math.radians(AP.SLANT_ANG / 2))   # 前面板 / 斜面折弯：切点离虚拟尖角 0.50


def sector(plane, c, r0, r1, a0, a1, length):
    """圆环扇形（折弯圆角）：在 plane（'YZ' / 'XY' / 'XZ'）里以 c 为圆心、r0..r1、角度 a0..a1（度，局部第一轴起逆时针），沿法向拉伸 length"""
    def p(r, a):
        return (c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))
    am = (a0 + a1) / 2
    return (cq.Workplane(plane).moveTo(*p(r1, a0)).threePointArc(p(r1, am), p(r1, a1))
            .lineTo(*p(r0, a1)).threePointArc(p(r0, am), p(r0, a0)).close().extrude(length))


# ---------------------------------------------------------------- 前壳
def _front_flat():
    """竖直前面板：x −2..322、y −2..0，从折弯切点 z 88.5 到顶；两侧各 2 mm 的耳朵（盖住下巴托侧板）从 z 90 开始（让位）"""
    cut, holes = AP.FEATURES["front"]
    z0 = AP.Z_CHIN + D_TAN
    x0 = AP.SHELL_X0
    pan = P.panel(AP.SHELL_W, H - z0, T, [(x - x0, z - z0, w, h) for x, z, w, h in cut],
                  [(x - x0, z - z0, d) for x, z, d in holes]).translate((x0, -T, z0))
    ear = AP.SIDE_TOP + 0.5
    for xa in (x0, W):
        pan = pan.cut(P.box(T, T + 2, ear - z0 + 1, xa, -T - 1, z0 - 1))
    return pan


def _front_bend():
    """前面板 → 斜面的 33° 折弯：外表面在内侧（凹），圆心在面板前面"""
    c = (-T - RI, AP.Z_CHIN + D_TAN)
    return sector("YZ", c, RI, RO, -AP.SLANT_ANG, 0, W)


def _flange_left():
    """斜面左侧翻边（斜面局部坐标 x, t, u）：90° 折弯 + 翻边平板 + 2 个 M3 压铆螺母孔 Ø4.2"""
    u0, u1 = AP.FLANGE_U
    bend = sector("XY", (RO, RO), RI, RO, 180, 270, u1 - u0).translate((0, 0, u0))
    flat = P.box(T, AP.FLANGE_T - RO, u1 - u0, 0, RO, u0)
    for u in AP.FLANGE_SCREW_U:
        flat = flat.cut(P.cyl(2.1, T + 2, -1, AP.FLANGE_SCREW_T, u, "X"))
    return bend.union(flat)


def _slant():
    """斜面平板（局部坐标）：u U_EDGE..83−0.5（上端接折弯），两侧翻边处去掉 x 0..3.7 并开 1 mm 让位口"""
    cut, holes = AP.FEATURES["slant"]
    e = AP.U_EDGE
    s = P.panel(W, AP.SLANT_L - D_TAN, T, [(x, u - e, *rest) for x, u, *rest in cut],
                [(x, u - e, d) for x, u, d in holes]).translate((0, 0, e))
    r = PD.CSK_D / 2 + 0.5                                                   # 键盘座 3 颗 M3 沉头：90° 锥从外表面（局部 Y 0）往里
    for x in PD.SPEC["tongue_x"]:
        s = s.cut(cq.Workplane().add(cq.Solid.makeCone(r, 0, r, cq.Vector(W / 2 + x, -0.5, e + PD.SCREW_U), cq.Vector(0, 1, 0))))
    u0, u1 = AP.FLANGE_U
    fl = _flange_left()
    for mirror in (False, True):
        rm = P.box(RO, T + 2, u1 - u0 + 2 * RELIEF, 0, -1, u0 - RELIEF)
        rm = rm.union(P.box(RO + RELIEF, T + 2, RELIEF, 0, -1, u0 - RELIEF)).union(P.box(RO + RELIEF, T + 2, RELIEF, 0, -1, u1))
        f = fl
        if mirror:
            rm, f = rm.mirror("YZ").translate((W, 0, 0)), fl.mirror("YZ").translate((W, 0, 0))
        s = s.cut(rm).union(f)
    return AP.on_slant_local(s)


def front_shell():
    return _front_flat().union(_front_bend()).union(_slant())


# ---------------------------------------------------------------- 下巴托
def side_outline():
    """侧板外形 (y, z)：下沿 = 底板折弯切点 TRAY_Z + 1.7；前沿沿斜面外表面线、键盘座底面；上沿 z SIDE_TOP，往后到 y SIDE_BACK"""
    dh, dd = PD.SPEC["H"], PD.SPEC["D"]
    fb, bb = AP.slant_pt(AP.U_EDGE - dh, 0), AP.slant_pt(AP.U_EDGE - dh, dd)   # 键盘座底面前角、后角
    zl = AP.TRAY_Z + RI
    return [(AP.TRAY_Y0, zl), (AP.SIDE_BACK, zl), (AP.SIDE_BACK, AP.SIDE_TOP), (-T, AP.SIDE_TOP), (-T, AP.Z_CHIN),
            fb, bb, (bb[0], zl)]


def _side_plate(grille_y):
    """一块侧板（x 0..2 局部，外表面 x = 0），孔：M4 锁型材、M3 锁斜面翻边压铆螺母、M3 锁键盘座两端、喇叭网"""
    s = cq.Workplane("YZ").polyline(side_outline()).close().extrude(T)
    for y, z in AP.SIDE_M4:
        s = s.cut(P.cyl(2.25, T + 2, -1, y, z, "X"))
    for u in AP.FLANGE_SCREW_U:
        y, z = AP.slant_pt(u, AP.FLANGE_SCREW_T)
        s = s.cut(P.cyl(1.7, T + 2, -1, y, z, "X"))
    dh = PD.SPEC["H"]
    for z in PD.SPEC["end_holes_z"]:
        y, zz = AP.slant_pt(AP.U_EDGE + z - dh, PD.SPEC["end_hole_y"])
        s = s.cut(P.cyl(1.7, T + 2, -1, y, zz, "X"))
    gz0, gz1, gd, gp = AP.GRILLE[1]
    gy0, gy1 = grille_y
    j, z = 0, gz0 + gd / 2
    while z <= gz1 - gd / 2 + 0.01:
        y = gy0 + gd / 2 + (gp / 2 if j % 2 else 0)
        while y <= gy1 - gd / 2 + 0.01:
            s = s.cut(P.cyl(gd / 2, T + 2, -1, y, z, "X"))
            y += gp
        z += gp * 0.866; j += 1
    return s


def chin_tray():
    """底板（z TRAY_Z−2..TRAY_Z，y TRAY_Y0..0）+ 两侧板（机架外侧 x −2..0 / 320..322，往上折 90°）+ 后翻边（贴前下横梁，往上折 90°，M4 ×3）；
    底板上 4 个 Ø2.4 孔装键盘转接小板 KBD-ADAPT 的 M2 铜柱"""
    y0, zt = AP.TRAY_Y0, AP.TRAY_Z
    yb = -RO - RELIEF                                                     # 侧边折弯后端（离后折弯留让位口）
    bottom = P.box(W + 2 * T - 2 * RO, -RO - y0, T, -T + RO, y0, zt - T)
    kx, ky = AP.KBD_XY
    for hx, hy in AP.KBD_HOLES:
        bottom = bottom.cut(P.cyl(1.2, T + 2, kx + hx, ky + hy, zt - T - 1))
    back_bend = sector("YZ", (-RO, zt + RI), RI, RO, 270, 360, W + 2 * T - 2 * RO - 2 * RELIEF).translate((-T + RO + RELIEF, 0, 0))
    back = P.box(W + 2 * T - 2 * RO - 2 * RELIEF, T, AP.BACK_FLANGE_TOP - (zt + RI), -T + RO + RELIEF, -T, zt + RI)
    nx, nz = AP.BACK_FLANGE_NOTCH
    back = back.cut(P.box(W + T - nx, T + 2, AP.BACK_FLANGE_TOP, nx, -T - 1, nz).edges("|Y and <X and <Z").fillet(2))
    for x in AP.BACK_FLANGE_HOLES_X:
        back = back.cut(P.cyl(2.25, T + 2, x, -T - 1, 10, "Y"))
    tray = bottom.union(back_bend).union(back)
    for k, xs in enumerate((-T, W)):
        side = _side_plate(AP.GRILLE[0][k])
        bend = sector("XZ", (RO, zt + RI), RI, RO, 180, 270, yb - y0)   # XZ 平面法向 −Y：从 yb 往前拉到 y0
        bend = bend.translate((0, yb, 0))
        if k == 0:
            tray = tray.union(side.translate((-T, 0, 0))).union(bend.translate((-T, 0, 0)))
        else:
            tray = tray.union(side.mirror("YZ").translate((W + T, 0, 0))).union(bend.mirror("YZ").translate((W + T, 0, 0)))
    return tray


def build():
    add("front_shell_alu", front_shell(), "panel", "front")
    add("chin_tray_alu", chin_tray(), "chin", "front")
