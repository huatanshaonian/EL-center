"""MAX6921AWI（SOIC-28 宽体）脚位示意 + SOP28 翻盖测试座测真伪接线 → png/31_max6921_pinout.png
脚位按 el_driver/上电测试清单.txt 第 8a 节（与 IV18 网表一致）。运行：python fig_max6921_pinout.py（项目目录下）"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle

F = FontProperties(fname=r"C:\Windows\Fonts\msyh.ttc")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "png", "31_max6921_pinout.png")


def name(n):
    if n == 1: return "VBB"
    if n == 2: return "DOUT"
    if 3 <= n <= 12: return f"OUT{22 - n}"      # 3 → OUT19 … 12 → OUT10
    if n == 13: return "BLANK"
    if n == 14: return "GND"
    if n == 15: return "CLK"
    if n == 16: return "LOAD"
    if 17 <= n <= 26: return f"OUT{26 - n}"     # 17 → OUT9 … 26 → OUT0
    if n == 27: return "DIN"
    return "VCC"


# 测真伪时每只脚接什么（清单 8a 第 2 步）
WIRE = {1: "接 12 V（限流 20 mA）或 9 V 电池", 2: "量这里", 13: "先接 GND", 14: "接 GND",
        15: "10 kΩ 下拉到 GND；用跳线碰 3.3 V 打时钟", 16: "10 kΩ 下拉到 GND；碰 3.3 V 锁存",
        27: "跳线：接 3.3 V = 送 1，接 GND = 送 0", 28: "接 3.3 V（对地并 100 nF）"}
ROLE = {1: "#d32f2f", 28: "#d32f2f", 14: "#212121", 2: "#1565c0", 13: "#1565c0", 15: "#1565c0", 16: "#1565c0", 27: "#1565c0"}


def pin_y(n, top, pitch):
    """左排 1–14 从上往下，右排 15–28 从下往上（逆时针）。"""
    return top - (n - 1) * pitch if n <= 14 else top - (28 - n) * pitch


def chip(ax, x0, title, wiring):
    w, pitch, top = 3.2, 1.0, 13.5
    body = Rectangle((x0, top - 13 * pitch - 0.7), w, 13 * pitch + 1.4, fc="#2b2b2b", ec="black", lw=1.5)
    ax.add_patch(body)
    ax.add_patch(Circle((x0 + 1.15, top - 0.05), 0.24, fc="#9e9e9e", ec="none"))
    ax.add_patch(matplotlib.patches.Wedge((x0 + w / 2, top + 0.7), 0.45, 180, 360, fc="white", ec="#555", lw=1))  # 半圆缺口（有的芯片只有这个）            # 1 脚圆点
    ax.plot([x0 + 0.08, x0 + 0.08], [top - 13 * pitch - 0.62, top + 0.62], color="#bdbdbd", lw=3)  # 1–14 侧倒角
    ax.text(x0 + w / 2, top - 6.5 * pitch, "MAX6921AWI", color="white", ha="center", va="center",
            fontproperties=F, fontsize=10, rotation=270)  # 字底朝 1–14 脚那条长边
    for n in range(1, 29):
        y = pin_y(n, top, pitch)
        left = n <= 14
        px = x0 - 0.7 if left else x0 + w
        ax.add_patch(Rectangle((px, y - 0.18), 0.7, 0.36, fc="#cfd8dc", ec="#607d8b"))
        nx = x0 + 0.35 if left else x0 + w - 0.35
        ax.text(nx, y, str(n), color="white", ha="center", va="center", fontsize=8, fontweight="bold")
        c = ROLE.get(n, "#555555")
        tx = x0 - 0.85 if left else x0 + w + 0.85
        lab = name(n)
        if wiring and n in WIRE:
            lab = f"{lab}：{WIRE[n]}" if not left else f"{WIRE[n]}：{lab}"
        elif wiring and name(n).startswith("OUT"):
            lab = f"{lab}（量）" if not left else f"（量）{lab}"
        ax.text(tx, y, lab, color=c, ha="right" if left else "left", va="center", fontproperties=F, fontsize=8.5,
                fontweight="bold" if n in ROLE else "normal")
    ax.text(x0 + w / 2, top + 1.6, title, ha="center", va="bottom", fontproperties=F, fontsize=13, fontweight="bold")
    return x0, w, top, pitch


fig, ax = plt.subplots(figsize=(16, 10.5), dpi=130)
ax.set_xlim(0, 32)
ax.set_ylim(-4.6, 17)
ax.set_aspect("equal")
ax.axis("off")

# 左：怎么数
x0, w, top, pitch = chip(ax, 5.2, "① 怎么数脚（从上往下看芯片）", wiring=False)
ax.add_patch(FancyArrowPatch((x0 - 3.3, top - 0.5), (x0 - 3.3, top - 12.5), arrowstyle="-|>", mutation_scale=18, color="#2e7d32", lw=2))
ax.add_patch(FancyArrowPatch((x0 + w + 3.6, top - 12.5), (x0 + w + 3.6, top - 0.5), arrowstyle="-|>", mutation_scale=18, color="#2e7d32", lw=2))
ax.text(x0 - 3.6, top - 6.5, "1 → 14\n往下数", color="#2e7d32", ha="right", va="center", fontproperties=F, fontsize=10)
ax.text(x0 + w + 3.9, top - 6.5, "15 → 28\n往上数", color="#2e7d32", ha="left", va="center", fontproperties=F, fontsize=10)
ax.add_patch(FancyArrowPatch((x0 + 0.5, top - 13.3), (x0 + w - 0.5, top - 13.3), connectionstyle="arc3,rad=0.4",
                             arrowstyle="-|>", mutation_scale=14, color="#2e7d32", lw=1.5))
ax.text(0.2, -1.6,
        "认 1 脚：\n"
        "• 芯片表面有个小圆坑（圆点）的那个角就是 1 脚。\n"
        "• 也有的是一头有半圆缺口：缺口朝上，缺口左边第一只是 1 脚。\n"
        "• 没有圆点时，看两条长边：带斜面（倒角）的那条长边是 1–14 脚这一排。\n"
        "• 多数芯片字正着读时，1 脚在左下角（左图是把芯片顺时针转了 90° 画的）。\n"
        "• 数法：1 脚在左上，沿左边往下数到 14，绕到右下是 15，沿右边往上数到 28（逆时针一圈）。",
        fontproperties=F, fontsize=10, va="top", ha="left")

# 右：测试座接线
x1, *_ = chip(ax, 22.6, "② 放进测试座后，面包板上每只脚接什么", wiring=True)
ax.text(17.2, -1.6,
        "测试座：翻盖座上有“1”或三角形标记，芯片 1 脚（圆点或缺口那头）对准这个标记放进去再合盖。\n"
        "座子下面的 28 根针就是标准 DIP-28 排法：和左图一样逆时针数，针号 = 芯片脚号，一一对应。\n"
        "座子针插不进面包板时，按 png/32 用杜邦线母头直接套针；合盖后用通断档确认 1、28 号针各通到芯片对应脚。\n"
        "上电顺序：先给 28 脚 3.3 V，再给 1 脚 VBB；断电反过来。\n"
        "红 = 电源　黑 = 地　蓝 = 控制 / 读数脚　灰 = 20 个输出 OUT0–OUT19（用表量对地电压）",
        fontproperties=F, fontsize=10, va="top", ha="left")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print(OUT)
