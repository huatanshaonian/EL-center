"""斜面面板布局示意图（正对斜面看）→ png/13_slant_layout.png
坐标、尺寸取自 assembly_panel.py；旋钮直径按用户选定（编码器 Ø15、指针旋钮 Ø33）。
运行：.venv/Scripts/python.exe fig_slant_layout.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
import render as R
import assembly_panel as AP

F = R.FONT
ENC_KNOB, SEL_KNOB = 15.0, 33.0


def label(ax, x, y, t, fs=9, **kw):
    ax.text(x, y, t, ha="center", va="center", fontproperties=F, fontsize=fs, **kw)


def main(fname="png/13_slant_layout.png", enc=None, fader_u=None):
    """enc / fader_u 可传入候选位置做方案对比，不改模型"""
    enc = enc or AP.ENC
    fader_u = fader_u or AP.FADER_U
    W, L = 316.0, AP.SLANT_L
    fig, ax = plt.subplots(figsize=(18, 6.6), dpi=110)
    ax.set_xlim(-5, W + 10); ax.set_ylim(-14, L + 10); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((2, 0), W, L, fc="#55585e", ec="#222", lw=1.2))
    label(ax, W / 2 + 2, L + 5, "斜面面板（正对斜面看；x 向右，u 沿斜面向上，单位 mm）", 12, color="#222")

    # ① 模式开关 + USB
    x, u = AP.SEL
    ax.add_patch(Circle((x, u), SEL_KNOB / 2, fc="#1c1c1c", ec="#000"))
    ax.plot([x, x], [u, u + SEL_KNOB / 2 - 2], color="#ddd", lw=2)
    label(ax, x, u - 3, f"模式开关\n指针旋钮 Ø{SEL_KNOB:.0f}", 8, color="white")
    for (x, u), t in zip(AP.USB, ("USB3", "USB2")):
        ax.add_patch(FancyBboxPatch((x - 7.5, u - 4), 15, 8, boxstyle="round,pad=0,rounding_size=3.5", fc="#111", ec="#888"))
        label(ax, x, u - 9, t, 8, color="white")

    # ② 编码器 + 推子
    for k, (x, u) in enumerate(enc):
        ax.add_patch(Circle((x, u), ENC_KNOB / 2, fc="#e8a33d", ec="#7a4b00", lw=1.5, zorder=3))
        label(ax, x, u, f"编码器{k + 1}", 7.5, zorder=4)
    (x1, u1), (x2, _) = enc[0], enc[1]
    ax.annotate("", (x1, u1 + 12), (x2, u1 + 12), arrowprops=dict(arrowstyle="<->", color="#ffd27a"))
    label(ax, (x1 + x2) / 2, u1 + 15, f"中心距 {x2 - x1:.0f}", 8.5, color="#ffd27a")
    g0, g1 = x1 + ENC_KNOB / 2, x2 - ENC_KNOB / 2
    ax.annotate("", (g0, u1 - 10), (g1, u1 - 10), arrowprops=dict(arrowstyle="<->", color="#ffd27a"))
    label(ax, (g0 + g1) / 2, u1 - 13, f"旋钮间隙 {g1 - g0:.0f}", 8.5, color="#ffd27a")
    for u, pos in zip(fader_u, (0.7, 0.35)):
        ax.add_patch(Rectangle((AP.FADER_X - 31, u - 1), 62, 2, fc="#111", ec="#888"))
        cx = AP.FADER_X - 30 + pos * 60
        ax.add_patch(Rectangle((cx - 5, u - 6), 10, 12, fc="#ddd", ec="#555", zorder=3))      # 推子帽 10x12（T）
        label(ax, AP.FADER_X + 40, u, "推子", 8, color="white")
    if len(fader_u) > 1:
        label(ax, AP.FADER_X - 40, sum(fader_u) / 2, f"推子间距 {abs(fader_u[0] - fader_u[1]):.0f}", 8.5, color="#ffd27a")

    # ③ 钮子 + 指示灯
    for x in AP.TOG_X:
        ax.add_patch(Rectangle((x - 7.5, AP.TOG_U - 12.5), 15, 33, fc="#b22", ec="#600"))
        ax.add_patch(Circle((x, AP.LAMP_U), 19.5 / 2, fc="#ccc", ec="#666"))
    label(ax, AP.TOG_X[1], AP.TOG_U - 18, "保护盖钮子 ×3", 8, color="white")
    label(ax, AP.TOG_X[1], AP.LAMP_U + 13, "Ø16 指示灯 ×3", 8, color="white")

    # ④ 带灯方键
    for x in AP.KEY_X:
        for u in AP.KEY_U:
            ax.add_patch(FancyBboxPatch((x - 12, u - 9), 24, 18, boxstyle="round,pad=0,rounding_size=1.5", fc="#f2c96b", ec="#8a6a1a"))
    label(ax, sum(AP.KEY_X) / 2, -5, "LA16 带灯方键 ×6", 8.5, color="#222")

    for xx, t in ((37, "① 模式"), (123.5, "② 调节"), (201.5, "③ 电源"), (271, "④ 功能键")):
        label(ax, xx, -10, t, 10, color="#222")
    fig.tight_layout(); fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname)


if __name__ == "__main__":
    main()
