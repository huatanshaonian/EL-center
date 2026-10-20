"""机架下料加工图 → png/14_frame_drawing.png（型材）、png/15_plates_drawing.png（隔板）
数据全部来自 frame_spec.py。运行：.venv/Scripts/python.exe fig_frame_drawing.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
import render as R
import frame_spec as S
from assembly_base import W, D, H

F = R.FONT
ALU, EDGE = "#d9dce0", "#333"


def t(ax, x, y, s, fs=9, ha="center", va="center", **kw):
    ax.text(x, y, s, ha=ha, va=va, fontproperties=F, fontsize=fs, **kw)


def dim(ax, p0, p1, s, off=(0, 0), fs=8.5, col="#1f5fbf"):
    ax.annotate("", p0, p1, arrowprops=dict(arrowstyle="<->", color=col, lw=0.8))
    t(ax, (p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], s, fs, color=col,
      bbox=dict(fc="white", ec="none", pad=0.5))


def bar(ax, x, y, w, h, label=None, fc=ALU):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=EDGE, lw=0.8))
    if label:
        t(ax, x + w / 2, y + h / 2, label, 9, fontweight="bold")


def tap(ax, x, y):      # 端面攻丝接头
    ax.add_patch(Circle((x, y), 4.5, fc="#e8462c", ec="#8a1c0c", zorder=5))


def bracket(ax, x, y):  # L 角码接头
    ax.plot([x], [y], marker="^", ms=8, color="#2c7be8", zorder=5)


def frame_sheet(fname="png/14_frame_drawing.png"):
    fig = plt.figure(figsize=(20, 13), dpi=110)
    fig.suptitle("MIS-01 机架下料加工图（2020 欧标 6 槽；端面攻丝连接；单位 mm）", fontproperties=F, fontsize=17)

    # ---- 正视（看前面）
    ax = fig.add_axes([0.02, 0.30, 0.30, 0.62]); ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-60, W + 40); ax.set_ylim(-60, H + 30)
    t(ax, W / 2, H + 18, "正视（从前往后看）", 12)
    bar(ax, 0, 0, 20, H, "A1"); bar(ax, W - 20, 0, 20, H, "A2")
    bar(ax, 20, 0, W - 40, 20, "B"); bar(ax, 20, H - 20, W - 40, 20, "B")
    for x in (20, W - 20):
        for z in S.POST_X_HOLES:
            tap(ax, x, z)
    dim(ax, (0, -25), (W, -25), f"{W}")
    dim(ax, (20, -45), (W - 20, -45), f"B = {W - 40}")
    dim(ax, (-25, 0), (-25, H), f"{H}", off=(-12, 0))

    # ---- 侧视（看左侧）
    ax = fig.add_axes([0.33, 0.30, 0.25, 0.62]); ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-50, D + 60); ax.set_ylim(-60, H + 30)
    t(ax, D / 2, H + 18, "侧视（从左往右看，前在左）", 12)
    bar(ax, 0, 0, 20, H, "A1"); bar(ax, D - 20, 0, 20, H, "A3")
    rails = (("D", 0), ("C", S.POST_Y_HOLES[0] - 10), ("C", S.POST_Y_HOLES[1] - 10), ("D", H - 20))
    for lab, z in rails:
        bar(ax, 20, z, D - 40, 20, lab)
        for x in (20, D - 20):
            (tap if lab == "C" else bracket)(ax, x, z + 10)
    for lab, z in rails:
        t(ax, D + 8, z + 10, f"顶面高 {z + 20:.0f}", 8.5, ha="left")
    dim(ax, (0, -25), (D, -25), f"{D}")
    dim(ax, (20, -45), (D - 20, -45), f"C、D = {D - 40}")

    # ---- 图例 + 下料表
    ax = fig.add_axes([0.60, 0.55, 0.39, 0.37]); ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    t(ax, 0, 97, "下料表", 13, ha="left", fontweight="bold")
    rows = [("编号", "名称", "长度", "数量", "加工")] + [(a, b, f"{c}", f"{n}", e) for a, b, c, n, e, _ in S.PROFILES]
    for i, r in enumerate(rows):
        y = 88 - i * 9
        for x, s, w in zip((0, 7, 33, 43, 51), r, (6, 26, 10, 8, 49)):
            t(ax, x, y, s, 9 if i else 9.5, ha="left", wrap=True, fontweight="bold" if i == 0 else "normal")
    ax.add_patch(Circle((2, 38), 1.6, fc="#e8462c", ec="#8a1c0c")); t(ax, 5, 38, f"端面攻丝接头：{S.SCREW} 从立柱外侧穿过通孔，锁入梁的端面（{S.TAP['thread']} 深 {S.TAP['depth']}）", 9, ha="left")
    ax.plot([2], [30], marker="^", ms=8, color="#2c7be8"); t(ax, 5, 30, "L 型角码接头：底、顶的前后纵梁 D，和横梁 B 同高，螺丝会相撞，所以用角码", 9, ha="left")
    t(ax, 0, 20, "说明：B、C 端面攻丝请卖家加工；A 立柱按右下图打孔。立柱、横梁切面要垂直（±0.2），长度公差 ±0.3。", 9, ha="left", color="#444")
    t(ax, 0, 13, "面板（前、后、斜面）不在此单，单独做钣金 / 亚克力。", 9, ha="left", color="#444")
    t(ax, 0, 6, "T 螺母一律用旋入式（船型）：立柱槽里有螺丝头挡着，滑入式装不进去。", 9, ha="left", color="#c0392b")

    # ---- 立柱打孔图
    ax = fig.add_axes([0.60, 0.04, 0.39, 0.48]); ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-40, 330); ax.set_ylim(-40, H + 30)
    t(ax, 145, H + 18, "立柱 A 打孔（4 根各不相同，高度从立柱下端量起）", 12)
    for k, (code, pos, xface, yface) in enumerate(S.POSTS):
        x0 = k * 82
        bar(ax, x0, 0, 20, H)
        t(ax, x0 + 10, -12, f"{code} {pos}", 9)
        for z in S.POST_X_HOLES:
            ax.add_patch(Circle((x0 + 10, z), 4, fc="white", ec="#e8462c", lw=1.5, zorder=4))
        for z in S.POST_Y_HOLES:
            ax.add_patch(Circle((x0 + 10, z), 4, fc="white", ec="#2c9e3f", lw=1.5, zorder=4))
        t(ax, x0 + 24, 40, f"红孔沉孔：{xface}", 7.5, ha="left", rotation=90, color="#c0392b")
        t(ax, x0 + 34, 40, f"绿孔沉孔：{yface}", 7.5, ha="left", rotation=90, color="#2c9e3f")
    for z in sorted(S.POST_X_HOLES + S.POST_Y_HOLES):
        ax.plot([-30, 0], [z, z], color="#999", lw=0.6, ls=":")
        t(ax, -32, z, f"{z:.0f}", 8.5, ha="right")
    t(ax, 145, -30, f"红孔 = 接横梁 B，左右方向打穿；绿孔 = 接纵梁 C，前后方向打穿。孔 Ø{S.HOLE['d']} 通孔，沉孔 Ø{S.HOLE['cb_d']} 深 {S.HOLE['cb_depth']}",
      8.5, color="#333")
    fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname)


def plates_sheet(fname="png/15_plates_drawing.png"):
    fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=110)
    fig.suptitle("MIS-01 隔板加工图（橘红色电木板 4 mm，CNC 铣削 / 钻孔，不能激光；孔 Ø4.5 配 M4×10 螺丝 + T 螺母；单位 mm；坐标原点 = 板的左前角）", fontproperties=F, fontsize=15)
    for ax, (code, name, (L, Wd, th), mat, notch, holes, hd, note) in zip(axs.ravel(), S.PLATES):
        ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-45, W + 25); ax.set_ylim(-55, D + 30)
        ax.add_patch(Rectangle((0, 0), L, Wd, fc=ALU, ec=EDGE, lw=1))
        if "18×18" in notch:
            for x in (0, L - 18):
                ax.add_patch(Rectangle((x, 0), 18, 18, fc="white", ec=EDGE, lw=1))
        if code == "P3":
            for x, y in S.VENTS:
                ax.add_patch(Circle((x, y), 4, fc="white", ec="#777", lw=0.6))
        for x, y, w, h in S.slots(code):
            ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle=f"round,pad=0,rounding_size={min(w, h) / 2 - 0.01}",
                                        fc="white", ec="#1f5fbf", lw=1.2))
            t(ax, x, y, f"{w}×{h}", 6.5, color="#1f5fbf", rotation=90 if h > w else 0)
        g = S.grid_holes(code)
        for x, y in g:
            ax.add_patch(Circle((x, y), S.GRID_D / 2, fc="white", ec="#5a6", lw=0.4))
        if g:
            xs = sorted({x for x, _ in g}); ys = sorted({y for _, y in g})
            sl = "；蓝色为走线长圆孔（宽 14，圆角）" if S.slots(code) else ""
            t(ax, L / 2, Wd + 7, f"绿色孔阵：Ø{S.GRID_D} × {len(g)} 个，间距 10，x {xs[0]:.0f}–{xs[-1]:.0f}、y {ys[0]:.0f}–{ys[-1]:.0f}（板坐标）{sl}", 8.5, color="#2c7a3f")
        for x, y in holes:
            ax.add_patch(Circle((x, y), hd / 2 + 1.2, fc="white", ec="#e8462c", lw=1.4))
            t(ax, x, y + 9, f"({x:.0f},{y:.0f})", 7, color="#c0392b")
        t(ax, L / 2, Wd + 18, f"{code} {name}：{L}×{Wd}×{th}，{mat}", 12, fontweight="bold")
        dim(ax, (0, -14), (L, -14), f"{L}（左右）")
        dim(ax, (-14, 0), (-14, Wd), f"{Wd}（前后）", off=(-14, 0))
        t(ax, L / 2, -38, f"切角：{notch}。{note}", 8.5, color="#333")
        t(ax, L / 2, -3, "（图中下边 = 机器前面）", 8, va="top", color="#666")
    fig.tight_layout(rect=(0, 0, 1, 0.95)); fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname)


if __name__ == "__main__":
    frame_sheet()
    plates_sheet()
