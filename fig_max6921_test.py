"""MAX6921 测真伪接线图（测试座不插面包板，用杜邦线母头套座子针）→ png/32_max6921_test_circuit.png
对应 el_driver/上电测试清单.txt 第 8a 节；脚位见 png/31_max6921_pinout.png。运行：python fig_max6921_test.py"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

F = FontProperties(fname=r"C:\Windows\Fonts\msyh.ttc")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "png", "32_max6921_test_circuit.png")
RED, BLK, BLU, GRN, GRY = "#d32f2f", "#212121", "#1565c0", "#2e7d32", "#757575"


def t(ax, x, y, s, c=BLK, fs=10, ha="left", va="center", bold=False):
    ax.text(x, y, s, color=c, fontproperties=F, fontsize=fs, ha=ha, va=va, fontweight="bold" if bold else "normal")


def wire(ax, pts, c=BLK, lw=1.8):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=c, lw=lw, solid_capstyle="round")


def dot(ax, x, y, c=BLK):
    ax.add_patch(Circle((x, y), 0.09, fc=c, ec=c, zorder=5))


def resistor(ax, x, y0, y1, label, c=BLK):
    """竖放电阻（y0 上端到 y1 下端）。"""
    m = (y0 + y1) / 2
    wire(ax, [(x, y0), (x, m + 0.45)], c)
    ax.add_patch(Rectangle((x - 0.18, m - 0.45), 0.36, 0.9, fc="white", ec=c, lw=1.6, zorder=4))
    wire(ax, [(x, m - 0.45), (x, y1)], c)
    t(ax, x + 0.3, m, label, c, 9)


def gnd(ax, x, y):
    wire(ax, [(x, y), (x, y - 0.3)])
    for i, w in enumerate((0.4, 0.26, 0.12)):
        ax.plot([x - w, x + w], [y - 0.3 - i * 0.13] * 2, color=BLK, lw=1.6)


def cap(ax, x, y0, y1, label):
    m = (y0 + y1) / 2
    wire(ax, [(x, y0), (x, m + 0.1)])
    ax.plot([x - 0.3, x + 0.3], [m + 0.1] * 2, color=BLK, lw=2)
    ax.plot([x - 0.3, x + 0.3], [m - 0.1] * 2, color=BLK, lw=2)
    wire(ax, [(x, m - 0.1), (x, y1)])
    t(ax, x + 0.4, m, label, BLK, 9)


fig, ax = plt.subplots(figsize=(15, 11), dpi=130)
ax.set_xlim(0, 31.5)
ax.set_ylim(-1, 21)
ax.set_aspect("equal")
ax.axis("off")
t(ax, 15, 20.4, "MAX6921 测真伪接线（测试座不插面包板：杜邦线母头直接套座子底下的针）", BLK, 14, "center", bold=True)

# 测试座（简化成只画要接线的 8 只脚，左右按真实位置）
sx, sy, sw, sh = 11, 3.2, 5.6, 14.6
ax.add_patch(FancyBboxPatch((sx, sy), sw, sh, boxstyle="round,pad=0.1", fc="#eceff1", ec="#455a64", lw=2))
t(ax, sx + sw / 2, sy + sh - 0.6, "SOP28 翻盖测试座", BLK, 11, "center", bold=True)
t(ax, sx + sw / 2, sy + sh - 1.3, "（芯片圆点对准座子“1”标记）", GRY, 9, "center")
t(ax, sx + sw / 2, sy + 6.0, "OUT0–OUT19\n（3–12、17–26 脚）\n不接线，\n万用表直接点针", GRY, 10, "center")
PIN = {  # 脚号: (左/右, y, 名称)
    1: ("L", 15.6, "1  VBB"), 2: ("L", 14.4, "2  DOUT"), 13: ("L", 6.0, "13 BLANK"), 14: ("L", 4.6, "14 GND"),
    28: ("R", 15.6, "VCC  28"), 27: ("R", 14.4, "DIN  27"), 16: ("R", 6.0, "LOAD 16"), 15: ("R", 4.6, "CLK  15")}
for n, (side, y, lab) in PIN.items():
    if side == "L":
        ax.add_patch(Rectangle((sx - 0.5, y - 0.15), 0.5, 0.3, fc="#b0bec5", ec="#455a64"))
        t(ax, sx + 0.2, y, lab, BLK, 10)
    else:
        ax.add_patch(Rectangle((sx + sw, y - 0.15), 0.5, 0.3, fc="#b0bec5", ec="#455a64"))
        t(ax, sx + sw - 0.2, y, lab, BLK, 10, "right")

# 左侧：电源
LX = sx - 0.5
# 12 V 电源 → 1 脚
ax.add_patch(FancyBboxPatch((0.4, 15.0), 3.8, 1.3, boxstyle="round,pad=0.1", fc="#ffebee", ec=RED))
t(ax, 2.3, 15.65, "12 V 电源（限流 20 mA）\n或 9 V 电池  +", RED, 9, "center")
wire(ax, [(4.3, 15.6), (LX, 15.6)], RED)
t(ax, 6.6, 15.95, "VBB", RED, 9)
# 2 脚 DOUT → 表
wire(ax, [(LX, 14.4), (6.4, 14.4)], BLU)
ax.add_patch(Circle((6.4, 14.4), 0.12, fc="white", ec=BLU, lw=1.6, zorder=5))
t(ax, 6.2, 13.85, "表笔点这里量 DOUT", BLU, 9, "right")
# 13 脚 BLANK → GND（第 4 步改接 3.3 V）
wire(ax, [(LX, 6.0), (8.5, 6.0), (8.5, 4.6)], BLU)
t(ax, 6.1, 6.45, "BLANK：先接 GND；第 4 步改接 3.3 V", BLU, 9, "right")
# 14 脚 GND
wire(ax, [(LX, 4.6), (2.5, 4.6)], BLK)
dot(ax, 8.5, 4.6)
gnd(ax, 2.5, 4.6)
t(ax, 2.9, 3.85, "公共地：12 V 电源负极、3.3 V 电源负极、\n万用表黑笔都接这里", BLK, 9)

# 右侧：3.3 V、DIN、LOAD、CLK
RX = sx + sw + 0.5
V33y = 18.6
ax.add_patch(FancyBboxPatch((24.4, V33y - 0.65), 5.0, 1.3, boxstyle="round,pad=0.1", fc="#ffebee", ec=RED))
t(ax, 26.9, V33y, "3.3 V（ESP 开发板 3V3 针\n或电源第二路）", RED, 9, "center")
wire(ax, [(RX, 15.6), (21.0, 15.6), (21.0, V33y), (24.3, V33y)], RED)
dot(ax, 21.0, 15.6, RED)
cap(ax, 21.0, 15.6, 13.6, "100 nF\n（VCC 去耦，\n尽量靠近 28 脚）")
gnd(ax, 21.0, 13.6)
t(ax, 18.3, 16.0, "VCC", RED, 9)
# 27 脚 DIN：跳线
wire(ax, [(RX, 14.4), (19.2, 14.4), (19.2, 12.0)], BLU)
ax.add_patch(Circle((19.2, 12.0), 0.13, fc="white", ec=BLU, lw=1.6, zorder=5))
t(ax, 19.5, 12.0, "DIN 跳线：插 3.3 V = 送 1，插 GND = 送 0", BLU, 9)
# 16 脚 LOAD、15 脚 CLK：10 k 下拉 + 碰 3.3 V 的跳线
# CLK（下面那只脚）的节点放近处、LOAD 的放远处，两条线不交叉
for y, name, x in ((6.0, "LOAD", 27.0), (4.6, "CLK", 20.6)):
    wire(ax, [(RX, y), (x, y)], BLU)
    dot(ax, x, y, BLU)
    resistor(ax, x, y, y - 2.6, "10 kΩ 下拉", BLU)
    gnd(ax, x, y - 2.6)
    jx, jy = (x, y + 1.3) if name == "LOAD" else (x + 1.4, y)  # LOAD 跳线头朝上、CLK 朝右，文字不打架
    wire(ax, [(x, y), (jx, jy)], BLU)
    ax.add_patch(Circle((jx, jy), 0.13, fc="white", ec=BLU, lw=1.6, zorder=5))
    t(ax, jx + 0.3, jy + 0.05, f"{name}：跳线碰一下 3.3 V\n再拿开 = 一个脉冲", BLU, 9)

# 底部说明
t(ax, 0.4, 0.6,
  "接法：测试座底下的针插不进面包板也没关系——只有上面 8 只脚要接线，用杜邦线母头直接套在座子针上（套不上就用小鳄鱼夹或焊一根线），"
  "另一头接面包板；面包板上只放 100 nF、两只 10 kΩ 和电源。\n"
  "上电顺序：先 3.3 V（28 脚），再 VBB（1 脚）；断电反过来。两路电源的负极必须接在一起（14 脚 GND）。"
  "测试步骤和每步该读到多少，见上电测试清单 8a；20 个 OUT 脚的位置见 png/31。",
  BLK, 9.5, va="top")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print(OUT)
