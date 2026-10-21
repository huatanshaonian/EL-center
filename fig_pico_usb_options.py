"""Pico Micro-USB 插头空间示意（x 72.5 处剖面，按真实倾角）→ png/25_pico_usb_options.png
左：现在 USB 朝斜面下沿；右：Pico 转 180°、USB 朝上沿。尺寸取自 assembly_panel.py、parts_panel.USB_EXT、render_pico_usb.py。
插头本体按 11×8 截面估：直头从插座口伸出 19，弯头伸出 10 后线转向机内。
运行：.venv/Scripts/python.exe fig_pico_usb_options.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
import render as R
import assembly_panel as AP
from parts_panel import USB_EXT

F = R.FONT
SA, CA = AP.SA, AP.CA
A = (AP.Y_BASE, AP.Z_BASE)
T_BOARD = 2 + AP.PCB_D                     # 斜面电路板元件面 t 8.5
T_BACK = T_BOARD + AP.PCB_T                # 背面 t 10.1
MOUTH_T = 12.4                             # 插座中心 t
PLUG_H = 8.0


def P(u, t):
    return (A[0] + u * SA + t * CA, A[1] + u * CA - t * SA)


def quad(ax, u0, u1, t0, t1, **kw):
    ax.add_patch(Polygon([P(u0, t0), P(u1, t0), P(u1, t1), P(u0, t1)], closed=True, **kw))


def note(ax, xy, txt, tx, ty, color="#222"):
    ax.annotate(txt, xy, (tx, ty), fontproperties=F, fontsize=9, color=color,
                arrowprops=dict(arrowstyle="-", lw=0.6, color="#666"), va="center")


def base(ax, title, board_u0):
    ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-75, 40); ax.set_ylim(5, 112)
    ax.set_title(title, fontproperties=F, fontsize=12)
    quad(ax, 0, AP.SLANT_L, 0, 2, fc="#8a8f96", ec="#333")                         # 斜面板
    ax.add_patch(Rectangle((-2, 88), 2, 30, fc="#8a8f96", ec="#333"))               # 竖直前面板
    ax.add_patch(Rectangle((2, 90), 40, 4, fc="#c0602a", ec="none"))                # 甲板
    ax.text(22, 97, "甲板（底面 z 90）", ha="center", fontproperties=F, fontsize=9)
    quad(ax, board_u0, AP.PCB_U[1], T_BOARD, T_BACK, fc="#1f7a3a", ec="none")       # 斜面电路板
    # USB2 面板延长线：耳板 + 本体 + 线尾
    ew, eh, et = USB_EXT["ear"]; bw, bh, bl = USB_EXT["body"]
    u = AP.USB[1][1]
    quad(ax, u - eh / 2, u + eh / 2, 2, 2 + et, fc="#333", ec="none")
    quad(ax, u - bh / 2, u + bh / 2, 2 + et, 2 + et + bl, fc="#222", ec="none")
    quad(ax, u - 4, u + 4, 2 + et + bl, 2 + et + bl + 15, fc="#444", ec="none")
    note(ax, P(u, 20), "USB2 面板延长线本体\n（u 5–15，伸进机内 26 mm）", -73, 18)


def pico(ax, u0, u1, mouth_u):
    quad(ax, u0, u1, T_BACK, T_BACK + 1, fc="#2e9e4f", ec="none")                  # Pico 板
    quad(ax, min(mouth_u, mouth_u + (5 if mouth_u < u0 + 3 else -5)), max(mouth_u, mouth_u + (5 if mouth_u < u0 + 3 else -5)),
         T_BACK + 1, T_BACK + 3.5, fc="#bbb", ec="#555")                            # USB 座


def plug(ax, u_from, length, sign, color, right_angle=False):
    u0, u1 = (u_from, u_from + sign * length)
    quad(ax, min(u0, u1), max(u0, u1), MOUTH_T - PLUG_H / 2, MOUTH_T + PLUG_H / 2, fc=color, ec="#333", alpha=0.75)
    if right_angle:
        uc = u1 - sign * 4
        quad(ax, uc - 2.5, uc + 2.5, MOUTH_T + PLUG_H / 2, MOUTH_T + PLUG_H / 2 + 14, fc=color, ec="#333", alpha=0.6)


def main(fname="png/25_pico_usb_options.png"):
    fig, axs = plt.subplots(1, 2, figsize=(16, 9), dpi=110)
    # 左：现在
    ax = axs[0]
    base(ax, "现在：Pico 的 USB 朝斜面下沿", 17)
    pico(ax, 21.3, 72.3, 20.6)
    plug(ax, 20.6, 19, -1, "#f0c040")
    plug(ax, 20.6, 10, -1, "#e06030", right_angle=True)
    note(ax, P(20.6, 13.6), "USB 插座口（u 20.6）", 8, 40)
    note(ax, P(12, 16.4), "直头插头（黄，伸出约 19）\n直接撞进延长线本体", 8, 28)
    note(ax, P(15, 12), "弯头插头（橙，伸出约 10 才拐弯）\n还是撞；插座口到本体只有 5.6 mm", 8, 15)
    # 右：方案①
    ax = axs[1]
    base(ax, "方案①：Pico 转 180°，USB 朝斜面上沿", 0)
    pico(ax, 27.0, 78.0, 78.0)
    plug(ax, 78.0, 19, +1, "#f0c040")
    plug(ax, 78.0, 10, +1, "#e06030", right_angle=True)
    note(ax, P(95, 12), "直头（黄）伸出 19：\n顶到甲板底面（约 13 mm 处就碰）", -73, 104)
    note(ax, P(84, 18), "弯头（橙）伸出 10 就拐弯：放得下\n或者用“公头转接板”（伸出 10–12，线焊在上面）", 8, 64)
    note(ax, P(78, 13.6), "USB 插座口移到板子上沿", 8, 50)
    fig.suptitle("Pico 的 Micro-USB 插头放在哪（x 72.5 处剖面；左边是前面，斜面后仰 33°；单位 mm）", fontproperties=F, fontsize=13)
    fig.tight_layout(); fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname)


if __name__ == "__main__":
    main()
