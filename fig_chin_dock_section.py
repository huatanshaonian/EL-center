"""下巴 + 后仰键盘座 连接方案剖面图（x 中线处 YZ 剖面）→ png/23_chin_dock_section.png
方案草图（2026-10-22，待用户确认）：键盘座接在斜面下沿，屏幕面与斜面外表面共面、一起后仰 33°；
斜面板与两侧三角板做成一个钣金件；键盘座两端锁三角板、顶部舌片从斜面背后用沉头螺丝锁住。
运行：.venv/Scripts/python.exe fig_chin_dock_section.py"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
import render as R
import assembly_panel as AP
import parts_dock as PD

F = R.FONT
SA, CA = AP.SA, AP.CA
A = (AP.Y_BASE, AP.Z_BASE)                 # 斜面外表面下沿
DH = PD.SPEC["H"]                          # 键盘座屏幕面高
DD = PD.SPEC["D"]                          # 键盘座厚
SPINE_T = 5.0                              # 键盘连接条厚（T，待实测）
TONGUE_U, TONGUE_T = 6.0, 4.5              # 舌片：沿斜面向上 6，厚 4.5（斜面内表面到斜面电路板元件面 6.5）
SCREW_U = 3.0


def P(u, t):
    """斜面坐标 → (y, z)：u 沿斜面向上（下沿 = 0），t 从外表面往里"""
    return (A[0] + u * SA + t * CA, A[1] + u * CA - t * SA)


def quad(u0, u1, t0, t1):
    return [P(u0, t0), P(u1, t0), P(u1, t1), P(u0, t1)]


def poly(ax, pts, **kw):
    ax.add_patch(Polygon(pts, closed=True, **kw))


def label(ax, xy, txt, tx, ty, fs=8.5):
    """xy = 箭头指向点，(tx, ty) = 文字左端位置"""
    ax.annotate(txt, xy, (tx, ty), fontproperties=F, fontsize=fs,
                arrowprops=dict(arrowstyle="-", lw=0.6, color="#555"), va="center")


def main(fname="png/23_chin_dock_section.png"):
    fig, ax = plt.subplots(figsize=(13, 10), dpi=120)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-150, 45); ax.set_ylim(-22, 112)
    ax.set_title("下巴 + 后仰键盘座连接方案（x 中线剖面，左边是前面；单位 mm）", fontproperties=F, fontsize=13)

    desk = -4 - 3
    ax.axhline(desk, color="#888", lw=1)
    ax.text(-148, desk - 3, "桌面（底板下 3 mm 橡胶脚垫）", fontproperties=F, fontsize=8, color="#666")
    # 机架：前下横梁、前立柱（虚线），甲板，底板，前面板
    ax.add_patch(Rectangle((0, 0), 20, 20, fc="#ddd", ec="#888", ls="--"))
    ax.text(10, 10, "前下\n横梁", ha="center", va="center", fontproperties=F, fontsize=7)
    ax.add_patch(Rectangle((0, -4), 45, 4, fc="#c0602a", ec="none"))
    ax.add_patch(Rectangle((2, 90), 43, 4, fc="#c0602a", ec="none"))
    ax.add_patch(Rectangle((-2, 88), 2, 24, fc="#333", ec="none"))
    label(ax, (-1, 105), "竖直前面板", -45, 106)
    label(ax, (30, 92), "甲板", 30, 102)

    # 三角板（钣金件的两侧翻边）外形：沿斜面到键盘座底面，再沿底面、座子背面回到底
    cheek = [(0, 0), (0, 88), (-2, 88), A, P(-DH, 0), P(-DH, DD), (P(-DH, DD)[0], 0)]
    poly(ax, cheek, fc="none", ec="#1f5fa8", lw=1.2, ls="--")
    label(ax, (0, 60), "两侧三角板（蓝虚线，在 x 0–2 / 318–320）\n后边翻边，M4 ×2 锁前立柱正面 T 槽", 4, 72)

    # 斜面板 2 mm + 斜面电路板
    poly(ax, quad(0, AP.SLANT_L, 0, 2), fc="#4a4d52", ec="#222")
    poly(ax, quad(AP.PCB_U[0], AP.PCB_U[1], 2 + AP.PCB_D, 2 + AP.PCB_D + AP.PCB_T), fc="#1f7a3a", ec="none")
    label(ax, P(60, 1), "斜面板 2 mm（与两侧三角板一个钣金件）", -140, 80)
    label(ax, P(40, 9.3), "斜面电路板", 4, 45)
    # USB 延长线耳板（u 4.5–15.5，只在 x 12–85）
    poly(ax, quad(4.5, 15.5, 2, 4.5), fc="none", ec="#999", lw=0.8, ls=":")

    # 键盘座：屏幕面墙、底板（带槽）、新加顶板、顶部舌片
    u0 = -DH
    poly(ax, quad(u0, 0, 0, 2), fc="#222", ec="#000")                       # 屏幕面墙
    poly(ax, quad(u0 + 1.7, u0 + 2.5, 0, DD), fc="#222", ec="#000")         # 槽底板
    poly(ax, quad(u0, u0 + 1.7, 0, 2.5), fc="#222", ec="#000")              # 槽前唇
    poly(ax, quad(u0, u0 + 1.7, 6.3, DD), fc="#222", ec="#000")             # 槽后唇
    poly(ax, quad(-2.5, 0, 0, DD), fc="#222", ec="#000")                    # 新加顶板 2.5
    poly(ax, quad(-DH, 0, DD - 2, DD), fc="#3a3a3a", ec="#000", alpha=0.6)  # 背面（新加，盖住 POGO 小板）
    poly(ax, quad(0, TONGUE_U, 2, 2 + TONGUE_T), fc="#222", ec="#000")      # 舌片
    # 沉头螺丝（斜面外 → 舌片）
    s0, s1 = P(SCREW_U, -0.2), P(SCREW_U, 2 + TONGUE_T - 0.3)
    ax.plot([s0[0], s1[0]], [s0[1], s1[1]], color="#d0a020", lw=3)
    label(ax, s0, "M3 沉头 ×3（黑色，斜面下沿一排）\n拧进舌片（POM 直接攻丝 / 打印件热熔铜螺母）", -148, 45)
    label(ax, P(-7, 1), "键盘座（POM CNC 或打印）\n屏幕面与斜面共面，一起后仰 33°\n长 300 → 316，两端各 M3 ×2 锁三角板", -148, 26)
    label(ax, P(-9, DD - 1), "键盘座背面加盖板\n（POGO 小板、磁铁装好后盖上）", -38, 22)

    # 键盘连接条（假设 5 厚）+ 平放的键盘
    poly(ax, quad(u0 - SPINE_T, u0, 0, DD), fc="none", ec="#c0392b", lw=1.2, ls="--")
    label(ax, P(u0 - SPINE_T / 2, 0), f"键盘连接条（红虚线，按 {SPINE_T:.0f} 厚估，待实测）", -148, 9)
    kb_y1 = P(u0 - SPINE_T, 0)[0] - 3
    ax.add_patch(Rectangle((kb_y1 - 90, desk), 90, 5, fc="#1a1a1a", ec="none"))
    ax.text(kb_y1 - 45, desk + 8, "X1 键盘平放", ha="center", fontproperties=F, fontsize=8)

    # 下巴底板：钣金件，后边上翻锁前下横梁
    ax.add_patch(Rectangle((P(-DH, DD)[0] + 1, -2), -P(-DH, DD)[0] - 1, 2, fc="#555", ec="none"))
    ax.add_patch(Rectangle((-2, 0), 2, 18, fc="#555", ec="none"))
    label(ax, (-25, -1), "下巴底板 2 mm（钣金，后边上翻 M4 ×3 锁前下横梁）", -45, -17)

    lo = P(u0 - SPINE_T, DD)
    ax.plot([lo[0]], [lo[1]], "o", color="#c0392b", ms=3)
    ax.text(lo[0] + 2, lo[1] - 2.5, f"z {lo[1]:.1f}", fontproperties=F, fontsize=7, color="#c0392b")
    fb = P(u0, 0)
    ax.text(fb[0] - 2, fb[1] + 1, f"y {fb[0]:.1f}", fontproperties=F, fontsize=7, ha="right")
    fig.tight_layout(); fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname, "dock front-bottom", [round(v, 1) for v in P(u0, 0)], "spine low", [round(v, 1) for v in lo])


if __name__ == "__main__":
    main()
