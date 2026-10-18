"""
MIS-01 —— 磁吸键盘座：仿 ThinkPad X1 Tablet 底边，让原装键盘吸上来用。
用平板上拆下的 POGO 触点小板（装在槽底板背后，触点从开孔伸出）和底边磁铁条（装在两段磁铁开孔背后，上压 1 mm 铁皮，拧在自攻凸台上）。
屏幕面的两对磁铁从正面嵌入，用来让键盘翻起来吸住、垫出角度。

局部坐标（未倾斜，等同平板竖放）：X 沿长度、0 = 中心，左右对称；Y = 厚度方向，0 = 屏幕面，向后为正；Z = 0 为底面（槽口朝下），向上为正。
装到机身上时整体绕 X 轴后仰，使屏幕面和斜面同角度；背后与机架的连接件等总装时再做，这里背面敞开，方便装小板和磁铁。
尺寸来源：U = 用户实测；T = 暂定（3D 打印件，按实物试装再改）。"""
import cadquery as cq
from parts import box, cyl

SPEC = dict(
    L=300.0, D=8.9, H=15.0,                     # T 总长（与键盘同宽）、总厚、屏幕面高
    groove=(211.0, 3.8, 1.7), groove_y=2.5,      # U 槽长、宽、深；槽前边离屏幕面
    floor=0.8,                                   # U 槽底板厚
    wall=2.0, band=4.0,                          # T 屏幕面墙厚；只在屏幕面磁铁槽处局部加厚到 4，下沿 45° 斜面（免支撑、让开装在里面的零件）
    end_wall=2.0, rib_t=1.2,                     # T 两端封墙、横向加强筋厚
)

def _inner(gap, w):
    """“相距 gap”= 一对孔最近边的距离 → 右侧孔中心 X"""
    return gap / 2 + w / 2

def _stadium(length, width, x, y, z0, h):
    """圆头长孔（长沿 X），从 z0 向上 h"""
    return cq.Workplane("XY").slot2D(length, width).extrude(h).translate((x, y, z0))

def _rrect(lx, ly, r, x, y, z0, h):
    return cq.Workplane("XY").rect(lx, ly).extrude(h).edges("|Z").fillet(r).translate((x, y, z0))

def keyboard_dock():
    s = SPEC
    L, D, H = s["L"], s["D"], s["H"]
    gl, gw, gd = s["groove"]
    fl = s["floor"]
    z_fl = gd + fl                               # 槽底板上表面 Z=2.5
    gy = s["groove_y"] + gw / 2                  # 槽宽中线 Y=4.4

    # ---- 主体：底墙 + 屏幕面墙 + 两端封墙，背面敞开（屏幕面墙是主要受力结构）
    b = box(L, D, z_fl, -L / 2)
    b = b.union(box(L, s["wall"], H, -L / 2))
    for sx in (-1, 1):
        b = b.union(box(s["end_wall"], D, H, sx * (L / 2 - s["end_wall"] / 2) - s["end_wall"] / 2))
    # 横向加强筋（YZ 面）：只放在不装东西的区段 —— 第二对螺丝与第一对自攻孔之间、最外自攻孔以外
    for x in (40.2, 110.0, 120.0, 130.0, 140.0):
        for sx in (-1, 1):
            b = b.union(box(s["rib_t"], D - s["wall"], H - z_fl, sx * x - s["rib_t"] / 2, s["wall"], z_fl))

    # ---- 槽（U）：211×3.8 圆头，深 1.7
    b = b.cut(_stadium(gl, gw, 0, gy, -0.01, gd + 0.01))

    # ---- 自攻凸台（U：外径 1.55 的螺丝 ≈ M1.6，底孔取 1.3；凸台高出槽底板 1.55；Y 比槽中线往后偏 0.2）
    boss_y, boss_h, boss_d, pilot = gy + 0.2, 1.55, 3.0, 1.3
    boss_x = [_inner(93.2, 1.55), _inner(203.8, 1.55)]
    for x in boss_x:
        for sx in (-1, 1):
            b = b.union(cyl(boss_d / 2, boss_h, sx * x, boss_y, z_fl))

    # ---- 底边磁铁开孔（U：51×2.2，相距 98.5，位于槽宽中间），孔内两道 0.8 宽横筋，比底板再高 1.2
    #      横筋位置 U：两对筋相距 134.2、161（最近边距离），每边开孔被分成 17.85 / 12.6 / 18.95 三段
    mag_len, mag_w = 51.0, 2.2
    mag_cx = _inner(98.5, mag_len)
    for sx in (-1, 1):
        b = b.cut(box(mag_len, mag_w, fl + 0.02, sx * mag_cx - mag_len / 2, gy - mag_w / 2, gd - 0.01))
        for gap in (134.2, 161.0):
            b = b.union(box(0.8, mag_w, fl + 1.2, sx * _inner(gap, 0.8) - 0.4, gy - mag_w / 2, gd))

    # ---- 槽底板上的通孔（都在槽宽中线上）
    cut_h = (gd - 0.01, fl + 0.02)
    b = b.cut(_stadium(17.1, 2.0, 0, gy, *cut_h))                              # U 触点开孔 17.1×2（六个圆柱连成的长圆）
    for sx in (-1, 1):
        for gap in (45.0, 65.9):                                               # U 两对 Ø1.65 螺丝孔（65.9 为复测值）
            b = b.cut(cyl(1.65 / 2, fl + 0.02, sx * _inner(gap, 1.65), gy, gd - 0.01))
        loc_len = (63.2 - 51.8) / 2                                            # U 限位孔：内距 51.8、外距 63.2 → 长 5.7（口述长 6.1，以内外距为准）
        b = b.cut(_rrect(loc_len, 3.33, 1.0, sx * (51.8 / 2 + loc_len / 2), gy, *cut_h))   # 宽 3.33 U；圆角 R1 T
        for x in boss_x:                                                       # 自攻底孔：凸台顶一直通到槽面（U：贯穿）
            b = b.cut(cyl(pilot / 2, boss_h + fl + 0.02, sx * x, boss_y, gd - 0.01))

    # ---- 屏幕面磁铁槽（U：Z 12.35 往下 5.5、深 3；T：从正面嵌入）
    #      槽处墙局部加厚到 4（槽后留 1 mm），左右各多出 2；加厚块下沿 45° 斜到墙上，让开磁铁条铁皮上的螺丝头
    pz0, pd = 12.35 - 5.5, 3.0
    zc = pz0 - (s["band"] - s["wall"])                                       # 斜面起点 Z=4.85
    prof = [(s["wall"] - 0.1, zc), (s["band"], pz0), (s["band"], H), (s["wall"] - 0.1, H)]
    for gap, ln in ((182.7, 34.5), (31.0, 10.9)):
        cx = gap / 2 + ln / 2
        for sx in (-1, 1):
            pad = cq.Workplane("YZ").polyline(prof).close().extrude(ln + 4).translate((sx * cx - ln / 2 - 2, 0, 0))
            b = b.union(pad).cut(box(ln, pd, 5.5, sx * cx - ln / 2, -0.01, pz0))
    return b

if __name__ == "__main__":
    d = keyboard_dock()
    bb = d.val().BoundingBox()
    print(f"{bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}  solids={len(d.solids().vals())}  valid={d.val().isValid()}")
