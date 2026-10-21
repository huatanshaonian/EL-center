"""
MIS-01 外罩：左右全高侧板、整块背板（2 mm 铝，嘉立创钣金）。2026-10-22 用户：模型都建好，但不一定装。
所以它们只是盖板，上面不固定任何东西，拆掉不影响机器：
- 侧板在机架外侧（x −2..0 / 320..322），和下巴托侧板同一平面，左下前角让出下巴托侧板（y < SIDE_BACK、z < 88）；
- 背板在 y 220..222，右下角让出 IEC 小板（assembly.IEC_PLATE），两块拼在一起；
- 都用 M4 锁型材外侧 T 槽；开通风长孔（左右两侧原来敞开散热，装上侧板后靠这些孔和顶板孔走风）。
"""
import cadquery as cq
import parts as P
import assembly_panel as AP
from assembly_base import W, D, H, Z_SHELF, PLATE_T, add

T = 2.0
SIDE_M4 = [(10, 200), (10, 350), (D - 10, 40), (D - 10, 200), (D - 10, 350), (110, H - 10), (110, Z_SHELF - 10), (150, 10)]   # (y, z)
REAR_M4 = [(10, 40), (10, 210), (10, H - 10), (W - 10, 210), (W - 10, H - 10), (110, H - 10), (200, H - 10)]          # (x, z)


def _slots(shape, rows, plane):
    """通风长孔（竖向圆头）：rows = [(c0, c1, z, n, 长, 宽)]，沿 c 方向均布 n 个；plane = 'YZ'（侧板，c = y）或 'XZ'（背板，c = x）"""
    for c0, c1, z, n, ln, wd in rows:
        for k in range(n):
            c = c0 + (c1 - c0) * k / max(n - 1, 1)
            h = ln - wd
            if plane == "YZ":
                cut = P.box(T + 2, wd, h, -1, c - wd / 2, z - h / 2)
                cut = cut.union(P.cyl(wd / 2, T + 2, -1, c, z - h / 2, "X")).union(P.cyl(wd / 2, T + 2, -1, c, z + h / 2, "X"))
            else:
                cut = P.box(wd, T + 2, h, c - wd / 2, -1, z - h / 2)
                cut = cut.union(P.cyl(wd / 2, T + 2, c, -1, z - h / 2, "Y")).union(P.cyl(wd / 2, T + 2, c, -1, z + h / 2, "Y"))
            shape = shape.cut(cut)
    return shape


def side_cover():
    """一块侧板（x 0..2 局部，之后平移）：y 0..D+2、z −PLATE_T..H+PLATE_T，左下前角让出下巴托侧板"""
    y1, z0, z1 = D + T, -PLATE_T, H + PLATE_T
    zc = AP.SIDE_TOP + 0.5                                       # 下巴托侧板上沿 + 0.5
    pts = [(AP.SIDE_BACK, z0), (y1, z0), (y1, z1), (0, z1), (0, zc), (AP.SIDE_BACK, zc)]
    s = cq.Workplane("YZ").polyline(pts).close().extrude(T)
    for y, z in SIDE_M4:
        s = s.cut(P.cyl(2.25, T + 2, -1, y, z, "X"))
    rows = [(110, 200, 45, 7, 40, 5),        # 下舱（LRS-200、PCB-3）
            (40, 200, 170, 9, 40, 5),        # 甲板层
            (60, 190, 300, 8, 40, 5)]        # 电脑层
    return _slots(s, rows, "YZ")


def rear_cover(iec_plate):
    """背板：x 0..W、z 0..H，右下角让出 IEC 小板（iec_plate = (x0, z0, 宽, 高)）；保留原来两个 Ø56 通风孔"""
    x0, z0, pw, ph = iec_plate
    s = P.box(W, T, H).cut(P.box(pw + 1, T + 2, ph + 1, x0 - 0.5, -1, z0 - 1))
    for x, z in REAR_M4:
        s = s.cut(P.cyl(2.25, T + 2, x, -1, z, "Y"))
    for cx in (100, 220):
        s = s.cut(P.cyl(28, T + 2, cx, -1, 340, "Y"))
    s = _slots(s, [(40, 190, 60, 7, 50, 5), (40, 280, 200, 11, 60, 5)], "XZ")
    return s.translate((0, D, 0))


def build(iec_plate):
    sc = side_cover()
    add("side_cover_L", sc.translate((-T, 0, 0)), "panel", "sides")
    add("side_cover_R", sc.translate((W, 0, 0)), "panel", "sides")
    add("rear_cover_alu", rear_cover(iec_plate), "panel", "rear")
