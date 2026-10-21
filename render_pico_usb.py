"""斜面电路板上 Pico 的 Micro-USB 插头干涉局部图 → png/24_pico_usb_iso.png、png/24_pico_usb_side.png
在斜面坐标里画（不倾斜）：X = 斜面 x，Y = 从斜面外表面往里的距离 t，Z = 沿斜面向上的 u。
Pico 按实际装法：底面贴斜面电路板背面（t 10.1），元件面和 USB 座朝里。直头插头按常见尺寸 11×8×19 估。
运行：.venv/Scripts/python.exe -u render_pico_usb.py"""
import numpy as np
import render as R
import parts as P
import parts_modules as M
import parts_panel as F
import vendor_parts as V
import assembly_panel as AP
from assembly_base import to_min, C

X0, X1, U0, U1 = 35.0, 115.0, -5.0, 50.0          # 截取范围（斜面 x、u）
PLUG = (11.0, 8.0, 19.0)                            # 直头 Micro-USB 插头本体 宽 × 厚 × 长


def clip(shape, t1=40):
    return shape.intersect(P.box(X1 - X0, t1 + 5, U1 - U0, X0, -5, U0))


def pico_now():
    """现在板上的位置（SLANT D1 U1，中心斜面 (72.5, 45.5)，USB 朝下沿），元件面朝里"""
    p = M.rpi_pico().rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 1, 0), 90).rotate((0, 0, 0), (0, 0, 1), 180)
    return to_min(p, 62, 2 + AP.PCB_D + AP.PCB_T, 20)


def usb_mouth(p):
    for s in p.solids().vals():
        b = s.BoundingBox()
        if 7 < b.xlen < 8.2 and 2.2 < b.ylen < 3 and 4 < b.zlen < 6:
            return (b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2, b.zmin


def items():
    board = V.load_abs_drop(AP.SLANT_STEP, AP._slant_drop).rotate((0, 0, 0), (1, 0, 0), 90) \
        .translate((AP.PCB_X[0], 2 + AP.PCB_D + AP.PCB_T, AP.PCB_U[0]))
    pico = pico_now()
    mx, mt, mu = usb_mouth(pico)
    w, h, L = PLUG
    plug = P.box(w, h, L, mx - w / 2, mt - h / 2, mu - L)
    usb2 = F.usb_panel_ext().translate((AP.USB[1][0], 0, AP.USB[1][1]))
    usb3 = F.usb_panel_ext().translate((AP.USB[0][0], 0, AP.USB[0][1]))
    hit = plug.intersect(usb2).union(plug.intersect(board))
    out = [("slant_panel", clip(P.box(316, 2, AP.SLANT_L, 2, 0, 0)), (0.6, 0.62, 0.66, 0.35), ""),
           ("SLANT_board", clip(board), C["pcb_g"], ""),
           ("Pico", pico, C["pcb_g"][:3] + (1,), ""),
           ("USB2_ext", usb2, C["dark"], ""), ("USB3_ext", clip(usb3), C["dark"], ""),
           ("plug", plug, (0.95, 0.75, 0.2, 0.45), ""),
           ("hit", hit, (0.9, 0.05, 0.05, 1), "")]
    return out, (mx, mt, mu)


def lims(az, el, box):
    r, u, d = R.view_basis(az, el)
    pts = np.array([[x, y, z] for x in box[:2] for y in box[2:4] for z in box[4:]])
    a, b = pts @ r, pts @ u
    return (a.min(), a.max()), (b.min(), b.max())


def main():
    its, (mx, mt, mu) = items()
    lab = [((mx + 8, 14, 46), "Pico（贴在斜面电路板背面）"), ((mx - 4, mt + 6, mu - 2), f"Micro-USB 插座口 u {mu:.1f}"),
           ((76, 28, 6), "USB2 面板延长线本体\nx 58–76、u 5–15"), ((mx + 8, mt, mu - 12), "直头插头 11×8×19（黄）\n红 = 碰到的部分"),
           ((100, 9, 30), "斜面电路板（背面）"), ((40, 1, 47), "斜面板（半透明）")]
    xl, yl = lims(205, 30, (X0, X1, 0, 40, U0, U1))
    R.render(its, "png/24_pico_usb_iso.png", az=205, el=30, size=(12, 9), labels=lab, xlim=xl, ylim=yl,
             title="Pico 的 Micro-USB 插头（从斜面背后看，斜面放平画；u = 沿斜面向上）")
    # 侧视只截插头所在的一条（x 66–79），不然整块板的元件叠在一起看不清
    strip = P.box(13, 50, U1 - U0, 66, -5, U0)
    side = [(n, sh.intersect(strip), c, g) for n, sh, c, g in its if n != "USB3_ext"]
    side = [x for x in side if x[1].solids().size()]
    xl, yl = lims(90, 0, (66, 79, -2, 30, U0, 32))
    R.render(side, "png/24_pico_usb_side.png", az=90, el=0, size=(9, 10), xlim=xl, ylim=yl,
             labels=[((70, 0, 28), "斜面板"), ((70, 9.3, 30), "斜面电路板"), ((70, 14, 26), "Pico"),
                     ((70, 22, 10), "USB2 延长线本体"), ((70, 13, 3), "插头（黄）/ 碰撞（红）")],
             title="侧视：只截 x 66–79 一条（左边是斜面板，往右是机内；竖直 = 沿斜面 u）")
    print("mouth", round(mx, 1), round(mt, 1), round(mu, 1))


if __name__ == "__main__":
    main()
