"""斜面电路板 SLANT D1.1 左 USB 缺口加高示意图 → png/28_slant_pcb_cut.png
原因：USB 改成上下叠放双口延长线（本体 宽 23 × 高 19.2），比板上左缺口（开到 u 17）高；板已下单，到货后手工切掉一条。
要切的：板本地 x 0–24、y 17–20.5（24 × 3.5），只有 GND 铺铜（2026-10-26 查 Gerber_SLANT_D1.1）。
两个视图：顶面（推子、编码器那面，朝斜面）和背面（Pico 那面，左右镜像）。
运行：.venv/Scripts/python.exe fig_slant_pcb_cut.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle
import render as R

F = R.FONT
OUTLINE = [(0, 17), (24, 17), (24, 0), (39, 0), (39, 17), (61, 17), (61, 0), (149, 0), (149, 78), (4, 78), (4, 64), (0, 64)]
CUT = (0, 17, 24, 3.5)                                   # x, y, w, h（板本地坐标 = 斜面 x − 17, u）
USB_BODY = (-0.5, 0.4, 23, 19.2)                         # 双口件本体投影（斜面 x 16.5–39.5、u 0.4–19.6）
MODE_HOLE = ((20, 40), 17)                               # 模式开关 Ø34 开孔
HOLES = [(12, 68), (142, 72), (142, 8), (73, 8)]         # M3 安装孔
FADERS = [(106.5, 40), (106.5, 24)]                      # 推子中心，长边沿 x（顶面）
ENCS = [(81.5, 63), (106.5, 63), (131.5, 63)]            # 编码器（顶面）
PICO = (55.5, 45.5, 21, 51)                              # Pico 中心、宽（x）、长（y），背面
JK = [68, 81.5, 95, 108.5, 122, 135.5]                   # J_K1–6 中心 x，y 4，背面


def draw(ax, mirror, title):
    fx = (lambda x: 149 - x) if mirror else (lambda x: x)
    rect = lambda x, y, w, h, **k: ax.add_patch(Rectangle((min(fx(x), fx(x + w)), y), w, h, **k))
    ax.add_patch(Polygon([(fx(x), y) for x, y in OUTLINE], closed=True, fc="#2e7d32", ec="#1b3d1c", lw=1.2, alpha=0.85))
    (cx, cy), r = MODE_HOLE
    ax.add_patch(Circle((fx(cx), cy), r, fc="white", ec="#1b3d1c", lw=1))
    ax.text(fx(cx), cy, "模式开关\n直径 34 孔", fontproperties=F, fontsize=8, ha="center", va="center", color="#333")
    for x, y in HOLES:
        ax.add_patch(Circle((fx(x), y), 1.6, fc="white", ec="#c9a227", lw=1.5))
    if mirror:
        x, y, w, h = PICO
        rect(x - w / 2, y - h / 2, w, h, fc="#1e1e1e", ec="k", lw=0.8)
        ax.text(fx(x), y, "Pico", fontproperties=F, fontsize=9, ha="center", va="center", color="white")
        for x in JK:
            rect(x - 5, 1.5, 10, 5.5, fc="white", ec="#555", lw=0.6)
        ax.text(fx(102), 9.5, "J_K1–J_K6（XH 座）", fontproperties=F, fontsize=7.5, ha="center", color="white")
    else:
        for x, y in FADERS:
            rect(x - 30, y - 4.5, 60, 9, fc="#bbb", ec="#555", lw=0.6)
        ax.text(fx(106.5), 32, "推子 ×2", fontproperties=F, fontsize=8, ha="center", va="center", color="white")
        for x, y in ENCS:
            rect(x - 6, y - 6.5, 12, 13, fc="#888", ec="#333", lw=0.6)
        ax.text(fx(106.5), 73, "编码器 ×3", fontproperties=F, fontsize=8, ha="center", color="white")
    # 双口件本体（虚线）和要切掉的一条（红）
    x, y, w, h = USB_BODY
    rect(x, y, w, h, fill=False, ec="#1565c0", lw=1.2, ls="--")
    x, y, w, h = CUT
    rect(x, y, w, h, fc="#e53935", ec="#b71c1c", lw=1.2, hatch="////", alpha=0.9)
    # 切线
    ax.plot([fx(-4), fx(24)], [20.5, 20.5], color="#b71c1c", lw=1.4, ls=(0, (5, 2)))
    ax.plot([fx(24), fx(24)], [17, 20.5 + 3], color="#b71c1c", lw=1.4, ls=(0, (5, 2)))
    ax.set_xlim(-12, 161); ax.set_ylim(-14, 88); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontproperties=F, fontsize=11)


def zoom(ax, mirror, title):
    """左下角放大：标尺寸"""
    fx = (lambda x: 149 - x) if mirror else (lambda x: x)
    ax.add_patch(Polygon([(fx(x), y) for x, y in OUTLINE], closed=True, fc="#2e7d32", ec="#1b3d1c", lw=1.5, alpha=0.85))
    x, y, w, h = USB_BODY
    ax.add_patch(Rectangle((min(fx(x), fx(x + w)), y), w, h, fill=False, ec="#1565c0", lw=1.5, ls="--"))
    ax.text(fx(11), 9, "USB 双口件本体\n（23 × 19.2，虚线）", fontproperties=F, fontsize=8.5, ha="center", va="center", color="#0d47a1")
    ax.add_patch(Rectangle((min(fx(0), fx(24)), 17), 24, 3.5, fc="#e53935", ec="#b71c1c", lw=1.5, hatch="////"))
    k = -1 if mirror else 1
    # 尺寸：高 3.5、长 24、离板边 17
    xr = fx(24) + k * 3
    ax.annotate("", (xr, 17), (xr, 20.5), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text(xr + k * 1, 18.75, "3.5", fontproperties=F, fontsize=9, ha="left" if k > 0 else "right", va="center")
    ax.annotate("", (fx(0), 24.5), (fx(24), 24.5), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text(fx(12), 25, "24（到缺口右边为止）", fontproperties=F, fontsize=9, ha="center", va="bottom")
    xl = fx(0) - k * 3
    ax.annotate("", (xl, 0), (xl, 17), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text(xl - k * 1, 8.5, "17\n（原缺口）", fontproperties=F, fontsize=8.5, ha="right" if k > 0 else "left", va="center")
    ax.plot([fx(-6), fx(24)], [20.5, 20.5], color="#b71c1c", lw=1.6, ls=(0, (5, 2)))
    ax.plot([fx(24), fx(24)], [17, 23], color="#b71c1c", lw=1.6, ls=(0, (5, 2)))
    ax.text(fx(-6), 21.8, "① 横切线（离板下沿 20.5）", fontproperties=F, fontsize=8.5, color="#b71c1c", ha="left" if k > 0 else "right", va="bottom")
    ax.text(fx(24) + k * 0.8, 23.2, "② 竖切线", fontproperties=F, fontsize=8.5, color="#b71c1c", ha="left" if k > 0 else "right", va="bottom")
    ax.set_xlim(*sorted((fx(-14), fx(46)))); ax.set_ylim(-4, 32); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontproperties=F, fontsize=11)


def main():
    fig = plt.figure(figsize=(16, 10.5))
    draw(fig.add_axes([0.02, 0.50, 0.56, 0.42]), False, "顶面（推子、编码器那面，装上后朝斜面）")
    draw(fig.add_axes([0.02, 0.05, 0.56, 0.42]), True, "背面（Pico 那面，左右是反的）")
    zoom(fig.add_axes([0.60, 0.50, 0.38, 0.42]), False, "顶面左下角放大（单位 mm）")
    zoom(fig.add_axes([0.60, 0.05, 0.38, 0.42]), True, "背面右下角放大（单位 mm）")
    fig.suptitle("SLANT D1.1 斜面电路板：左 USB 缺口加高 3.5 mm（红色那条切掉）", fontproperties=F, fontsize=15)
    fig.text(0.5, 0.012, "红色一条只有接地铺铜，没有走线和元件；焊元件前切。美工刀沿钢尺两面各划 15–20 遍，钳子掰断，砂纸磨平，"
             "铜边涂指甲油。宁可多切 0.5，不要少切。", fontproperties=F, fontsize=9, ha="center", wrap=True)
    fig.savefig("png/28_slant_pcb_cut.png", dpi=130)
    print("saved png/28_slant_pcb_cut.png")


if __name__ == "__main__":
    main()
