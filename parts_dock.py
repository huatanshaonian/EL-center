"""
MIS-01 —— 磁吸键盘座：仿 ThinkPad X1 Tablet 底边，让原装键盘吸上来用。
用平板上拆下的 POGO 触点小板（装在槽底板背后，触点从开孔伸出）和底边磁铁条（装在两段磁铁开孔背后，上压 1 mm 铁皮，拧在自攻凸台上）。
屏幕面的两对磁铁从正面嵌入，用来让键盘翻起来吸住、垫出角度。

局部坐标（未倾斜，等同平板竖放）：X 沿长度、0 = 中心，左右对称；Y = 厚度方向，0 = 屏幕面，向后为正；Z = 0 为底面（槽口朝下），向上为正。
装到机身上时整体绕 X 轴后仰，屏幕面与斜面外表面共面，顶面顶住斜面下沿（2026-10-22 用户确认方案 png/23）：
- 长 320，正好夹在下巴托两块侧板之间；两端各一段实心块，每端 2 个 M3 孔（压 M3×4 热熔铜螺母），侧板外面打沉头螺丝；
- 顶面加顶板，顶板上 3 个舌片伸到斜面板背后，斜面下沿从正面打 3 颗 M3 沉头拧进舌片；
- 背面敞开装 POGO 小板和磁铁，装好后另盖一块背板（keyboard_dock_cover）：全长 320，两端各 2 颗 M2 自攻锁进两端实心块；
  背板下沿中间开出线口（01AY247 排线宽 20、扭着走占约 45），排线往后下接下巴托底板上的键盘转接小板 KBD-ADAPT。
尺寸来源：U = 用户实测；T = 暂定（3D 打印件，按实物试装再改）。
加工：2026-10-23 定为嘉立创 3D 打印尼龙 MJF（PA12 天然灰，不染色，2026-10-27），不用 CNC（薄壁、多面装夹，CNC 难做且贵）；
螺丝孔全部 Ø4.0，压 M3×4 滚花热熔铜螺母（外径约 4.2）。"""
import cadquery as cq
from parts import box, cyl

SPEC = dict(
    L=320.0, D=8.9, H=15.0,                     # 总长 = 下巴托两侧板之间（2026-10-22 由 300 改）、总厚、屏幕面高（T）
    groove=(211.0, 3.8, 1.7), groove_y=2.5,      # U 槽长、宽、深；槽前边离屏幕面
    floor=0.8,                                   # U 槽底板厚
    wall=2.0, band=4.0,                          # T 屏幕面墙厚；只在屏幕面磁铁槽处局部加厚到 4，下沿 45° 斜面（免支撑、让开装在里面的零件）
    end_wall=12.0, rib_t=1.5,                    # 两端实心块长（放 M3 螺丝孔 + 背盖 M2 孔；2026-10-26 由 8 加长）、横向加强筋厚（1.2 → 1.5）
    top_t=2.5,                                   # 顶板厚
    tongue=(16.0, 10.0, 4.0), tongue_x=(-35.0, 45.0, 120.0),  # 舌片 宽×高（沿斜面）×厚、中心 X（全局 x = 160 + X；让开 x<90 的 USB 延长线耳板和 x 90/159 的电路板铜柱）；
                                                              # 高 6.5 → 10（2026-10-27：斜面孔要离板边 ≥ 1.5T）
    end_holes_z=(5.5, 11.0), end_hole_y=5.0,     # 两端 M3 孔（沿 X）的 Z、Y
    cover_t=2.0,                                 # 背盖厚（1.2 → 1.5 → 2.0：嘉立创 MJF 对 100 mm 以上零件建议壁厚 ≥ 2.0，2026-10-27）
    cover_screw_x=150.5, cover_screw_z=(4.5, 10.5),   # 背盖 M2 自攻孔：|X|、Z（离两端 M3 孔 ≥ 1.7）；块上底孔 Ø1.7 深 6，背盖过孔 Ø2.4
    cable_slot=(46.0, 8.0),                      # 背盖下沿出线口 宽 × 高（从背盖下沿 Z 1.5 往上到 Z 8；POGO 小板顶 Z 6.2）
)
SCREW_U = 5.0                                    # 斜面下沿 M3 沉头孔中心离下沿（沿斜面）：孔边离板边 3.3 ≥ 1.5T（原 3.3 只剩 1.6，2026-10-27）
CSK_D = 6.5                                      # 斜面上这 3 个孔的 90° 沉头外径（M3 沉头螺钉头 Ø6.0–6.7），STEP 里画出来
INSERT_R = 2.0                                   # M3 热熔铜螺母孔 Ø4.0（尼龙打印件）

def _inner(gap, w):
    """“相距 gap”= 一对孔最近边的距离 → 右侧孔中心 X"""
    return gap / 2 + w / 2

def _stadium(length, width, x, y, z0, h):
    """圆头长孔（长沿 X），从 z0 向上 h"""
    return cq.Workplane("XY").slot2D(length, width).extrude(h).translate((x, y, z0))

def _rrect(lx, ly, r, x, y, z0, h):
    return cq.Workplane("XY").rect(lx, ly).extrude(h).edges("|Z").fillet(r).translate((x, y, z0))

def keyboard_dock(hole_r=INSERT_R):
    """hole_r：7 个 M3 孔半径。打印件 INSERT_R（Ø4 压热熔铜螺母）；CNC 询价图用 1.25（Ø2.5 攻 M3）"""
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
    # 顶板 + 舌片（舌片在屏幕面墙后面、Y 2 起，伸出顶面 tongue 高）
    b = b.union(box(L, D, s["top_t"], -L / 2, 0, H - s["top_t"]))
    tw, th, tt = s["tongue"]
    for x in s["tongue_x"]:
        b = b.union(box(tw, tt, th, x - tw / 2, s["wall"], H))
        b = b.cut(cyl(hole_r, tt + 2, x, s["wall"] - 1, H + SCREW_U, "Y"))      # 热熔铜螺母孔 Ø4.0（舌片厚 4，压 M3×4）
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
    # ---- 顶面后角倒 1 mm：斜面电路板下沿（t 8.5–10.1）正好落在顶面后沿上，留出间隙
    b = b.cut(cq.Workplane("YZ").polyline([(D - 1.2, H + 0.01), (D + 0.01, H + 0.01), (D + 0.01, H - 1.2)]).close()
              .extrude(L + 2).translate((-L / 2 - 1, 0, 0)))
    # ---- 两端 M3 孔（沿 X，深 7）
    for sx in (-1, 1):
        for z in s["end_holes_z"]:
            b = b.cut(cyl(hole_r, 7, sx * (L / 2 - 7) if sx > 0 else -L / 2, s["end_hole_y"], z, "X"))
    # ---- 背盖 M2 自攻底孔（沿 Y，从背面往里 6）
    for sx in (-1, 1):
        for z in s["cover_screw_z"]:
            b = b.cut(cyl(0.85, 6.01, sx * s["cover_screw_x"], D - 6, z, "Y"))
    return b

def keyboard_dock_cover():
    """背盖：全长盖住背面开口（POGO 小板、磁铁装好后），两端各 2 颗 M2 自攻；下沿中间开排线出线口；局部坐标同 keyboard_dock，贴在 Y = D 面上"""
    s = SPEC
    zb, zt = s["groove"][2] + s["floor"], s["H"] - s["top_t"]
    c = box(s["L"], s["cover_t"], zt - zb + 2, -s["L"] / 2, s["D"], zb - 1)
    for sx in (-1, 1):
        for z in s["cover_screw_z"]:
            c = c.cut(cyl(1.2, s["cover_t"] + 0.02, sx * s["cover_screw_x"], s["D"] - 0.01, z, "Y"))
    corner = box(4.3, s["cover_t"] + 0.2, 4.3, -2.15, s["D"] - 0.1, -2.15).rotate((0, 0, 0), (0, 1, 0), 45)   # 转 45° 的方块：切掉直角边约 3 的三角
    for sx in (-1, 1):                                                         # 两端下角倒斜角：让开下巴托底板和侧板之间的折弯圆角
        c = c.cut(corner.translate((sx * s["L"] / 2, 0, zb - 1)))
    sw, sh = s["cable_slot"]
    return c.cut(box(sw, s["cover_t"] + 0.02, sh - (zb - 1) + 0.01, -sw / 2, s["D"] - 0.01, zb - 1 - 0.01).edges("|Y and >Z").fillet(1.5))

if __name__ == "__main__":
    d = keyboard_dock()
    bb = d.val().BoundingBox()
    print(f"{bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}  solids={len(d.solids().vals())}  valid={d.val().isValid()}")
