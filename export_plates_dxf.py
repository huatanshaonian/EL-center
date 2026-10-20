"""电木隔板 CNC 加工图（DXF，单位 mm）→ procurement/电木隔板_DXF/P1_甲板.dxf 等 4 个文件
几何全部来自 frame_spec.py（和 png/15 同源）。图层：CUT = 外形和所有孔（加工用），NOTE = 文字和尺寸（只作说明）。
坐标原点 = 板的左前角，x 向右（左右方向），y 向后（前后方向）。
运行：.venv/Scripts/python.exe export_plates_dxf.py"""
import os
import ezdxf
from ezdxf import units
import frame_spec as S

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "procurement", "电木隔板_DXF")
FILE = {"P1": "P1_甲板", "P2": "P2_电脑层板", "P3": "P3_顶板", "P4": "P4_底板"}


def outline(code, L, Wd):
    """外形多段线点列（甲板前两角切 18×18）"""
    if code == "P1":
        n = 18
        return [(n, 0), (L - n, 0), (L - n, n), (L, n), (L, Wd), (0, Wd), (0, n), (n, n)]
    return [(0, 0), (L, 0), (L, Wd), (0, Wd)]


def slot(msp, x, y, w, h):
    """圆角长圆孔（两端半圆），中心 (x, y)，外形 w×h"""
    r = min(w, h) / 2
    if w >= h:
        a, b = x - w / 2 + r, x + w / 2 - r
        pts = [(a, y - r, 0, 0, 0), (b, y - r, 0, 0, 1), (b, y + r, 0, 0, 0), (a, y + r, 0, 0, 1)]
    else:
        a, b = y - h / 2 + r, y + h / 2 - r
        pts = [(x + r, a, 0, 0, 0), (x + r, b, 0, 0, 1), (x - r, b, 0, 0, 0), (x - r, a, 0, 0, 1)]
    msp.add_lwpolyline(pts, format="xyseb", close=True, dxfattribs={"layer": "CUT"})


def export(plate):
    code, name, (L, Wd, th), mat, notch, holes, hd, note = plate
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.MM
    doc.layers.add("CUT", color=1)
    doc.layers.add("NOTE", color=7)
    doc.styles.add("CN", font="simhei.ttf")                                 # 黑体 .ttf：AutoCAD 按文件名找字体，.ttc（宋体）常找不到
    msp = doc.modelspace()
    msp.add_lwpolyline(outline(code, L, Wd), close=True, dxfattribs={"layer": "CUT"})
    for x, y in holes:                                                       # 固定孔 M4
        msp.add_circle((x, y), hd / 2, dxfattribs={"layer": "CUT"})
    g = S.grid_holes(code)
    for x, y in g:                                                           # 电路板孔阵 M3
        msp.add_circle((x, y), S.GRID_D / 2, dxfattribs={"layer": "CUT"})
    for x, y, w, h in S.slots(code):                                         # 走线长圆孔
        slot(msp, x, y, w, h)
    if code == "P3":
        for x, y in S.VENTS:                                                 # 通风孔
            msp.add_circle((x, y), 4.0, dxfattribs={"layer": "CUT"})

    # ---- 说明（NOTE 层）
    def txt(s, x, y, h=4.0):
        msp.add_text(s, height=h, dxfattribs={"layer": "NOTE", "style": "CN"}).set_placement((x, y))
    lines = [f"{code} {name}  {L} x {Wd} x {th} mm  数量 1",
             f"材料：{mat}，CNC 铣削/钻孔（不可激光）",
             f"固定孔 Ø{hd} x {len(holes)}（M4）"]
    if g:
        lines.append(f"孔阵 Ø{S.GRID_D} x {len(g)}，间距 10")
    if S.slots(code):
        lines.append(f"走线长圆孔 x {len(S.slots(code))}（宽 14，两端半圆）")
    if code == "P3":
        lines.append(f"通风孔 Ø8 x {len(S.VENTS)}")
    if code == "P1":
        lines.append("前两角切 18 x 18")
    lines.append("原点 = 左前角；图中下边 = 机器前面；未注公差 ±0.2")
    for i, s in enumerate(lines):
        txt(s, 0, -14 - i * 7)
    dim = msp.add_linear_dim(base=(0, Wd + 12), p1=(0, Wd), p2=(L, Wd), dxfattribs={"layer": "NOTE"})
    dim.render()
    dim = msp.add_linear_dim(base=(-12, 0), p1=(0, 0), p2=(0, Wd), angle=90, dxfattribs={"layer": "NOTE"})
    dim.render()
    path = os.path.join(OUT_DIR, FILE[code] + ".dxf")
    doc.saveas(path)
    return path, len(holes) + len(g) + len(S.slots(code)) + (len(S.VENTS) if code == "P3" else 0)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for p in S.PLATES:
        path, n = export(p)
        print("saved", os.path.basename(path), "features:", n)


if __name__ == "__main__":
    main()
