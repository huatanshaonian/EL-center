"""前面板简图（正视 + 中线侧剖）→ png/20_front_panel.png
坐标、尺寸全部取自 assembly_panel.py / assembly.py；斜面在正视图里按 cos33° 压扁投影。
运行：.venv/Scripts/python.exe fig_front_panel.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, Rectangle, Polygon, FancyBboxPatch
import render as R
import assembly_panel as AP
import assembly as A
from assembly_base import W, D, H, Z_DECK, Z_SHELF, Z_SCREEN, PLATE_T

F = R.FONT
CA, SA = AP.CA, AP.SA
PANEL, CHIN, CUT, GLASS = "#c9ccd1", "#6d7178", "#2a2c30", "#9fd3e6"


def label(ax, x, y, t, fs=8, **kw):
    kw.setdefault("ha", "center")
    ax.text(x, y, t, va="center", fontproperties=F, fontsize=fs, **kw)


def rect(ax, x, z, w, h, **kw):
    ax.add_patch(Rectangle((x, z), w, h, **kw))


def slant_z(u):
    return AP.Z_BASE + u * CA


def front_view(ax):
    ax.set_xlim(-40, W + 45); ax.set_ylim(-25, H + 20); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("正视（斜面按 33° 投影压扁）", fontproperties=F, fontsize=12)
    # 机架立柱 / 横梁（虚线，在面板后面）
    for x in (0, W - 20):
        rect(ax, x, 0, 20, H, fc="none", ec="#999", ls="--", lw=0.8)
    for z in (0, H - 20):
        rect(ax, 20, z, W - 40, 20, fc="none", ec="#999", ls="--", lw=0.8)
    # 竖直前面板 z 88–420
    z0 = AP.Z_CHIN
    rect(ax, 0, z0, W, H - z0, fc=PANEL, ec="#333", lw=1.2)
    # EL 视窗 + 屏
    sx0 = (W - 267) / 2
    aa_w, aa_h = 211.2, 158.4
    ex, ez = sx0 + (267 - aa_w) / 2 - 2, Z_SCREEN + (220 - aa_h) / 2 - 2
    rect(ax, ex, ez, aa_w + 4, aa_h + 4, fc="#3a2a10", ec="#111")
    rect(ax, ex + 2, ez + 2, aa_w, aa_h, fc="#d98a1c", ec="none", alpha=0.85)
    label(ax, ex + aa_w / 2, ez + aa_h / 2, f"EL 屏 LJ64K052\n视窗 {aa_w + 4:.0f}×{aa_h + 4:.0f}", 11, color="#3a2000")
    # 管龛：IN-14 ×6 + IV-18
    nx, nz, nw, nh = AP.NICHE
    rect(ax, nx, nz, nw, nh, fc=CUT, ec="#111")
    for x in A.TUBE_X:
        ax.add_patch(FancyBboxPatch((x - 9, 109.4), 18, 174.7 - 109.4, boxstyle="round,pad=0,rounding_size=8",
                                    fc="#e07a2e", ec="#7a3500", alpha=0.75))
    ax.add_patch(FancyBboxPatch((22.8, 97.6), 142 - 22.8, 18, boxstyle="round,pad=0,rounding_size=8",
                                fc="#4fd6c2", ec="#11695c", alpha=0.75))
    label(ax, nx + nw / 2, 166, "IN-14 ×6", 9, color="white")
    label(ax, 82, 106.6, "IV-18", 8, color="#063")
    # 表头
    mx, mz = AP.METER
    ax.add_patch(FancyBboxPatch((mx - 32, mz - 28), 64, 56, boxstyle="round,pad=0,rounding_size=3", fc="#222", ec="#000"))
    rect(ax, mx - 28, mz - 16, 56, 40, fc="#f3eee0", ec="none")
    ax.plot([mx, mx + 16], [mz - 14, mz + 14], color="#b00", lw=1.2)
    label(ax, mx, mz - 22, "85C1 表头", 7.5, color="white")
    # 6E2 窗
    wx, wz, ww, wh = AP.EYE_WIN
    rect(ax, wx, wz, ww, wh, fc=CUT, ec="#111")
    for x in AP.EYE_X:
        ax.add_patch(FancyBboxPatch((x - 10, 111.6 + 6), 20, 173.6 - 117.6, boxstyle="round,pad=0,rounding_size=8",
                                    fc="#55e07a", ec="#0a5a20", alpha=0.75))
    label(ax, wx + ww / 2, wz + wh + 6, "6E2 ×2", 8, color="#032")
    # 盖革窗 + J305
    gx, gz, gw, gh = AP.SBM_WIN
    rect(ax, gx, gz, gw, gh, fc=CUT, ec="#111")
    ax.add_patch(FancyBboxPatch((186, A.SBM_Z - 5), 103.5, 10, boxstyle="round,pad=0,rounding_size=4", fc="#bfc3c8", ec="#555"))
    label(ax, 237, A.SBM_Z, "J305 盖革管", 7.5, color="#222")
    # 亚克力（虚线）
    ax.add_patch(Rectangle((22.5, 89), 173 - 22.5, 179 - 89, fc="none", ec="#1f7fbf", ls=":", lw=1.2))
    ax.add_patch(Polygon([(178, 91), (299, 91), (299, 175.5), (244, 175.5), (244, 116), (178, 116)],
                         closed=True, fc="none", ec="#1f7fbf", ls=":", lw=1.2))
    # 感应器、固定孔
    ax.add_patch(Circle(AP.SENSOR, 3, fc="white", ec="#333"))
    label(ax, AP.SENSOR[0] - 22, AP.SENSOR[1], "感应窗", 7)
    holes = [(x, z) for x in (10, W - 10) for z in (140, 280, 410)] + [(x, H - 10) for x in (110, 210)]
    for x, z in holes:
        ax.add_patch(Circle((x, z), 2.25, fc="white", ec="#333", lw=0.8))
    # 斜面（投影）
    zb, zc = AP.Z_BASE, AP.Z_CHIN
    rect(ax, 2, zb, W - 4, zc - zb, fc=CHIN, ec="#222", lw=1.0)
    for x, u in [AP.SEL]:
        ax.add_patch(Ellipse((x, slant_z(u)), 33, 33 * CA, fc="#111", ec="#000"))
    for x, u in AP.USB:
        rect(ax, x - 7.5, slant_z(u) - 3, 15, 6, fc="#111", ec="#999")
    for x, u in AP.ENC:
        ax.add_patch(Ellipse((x, slant_z(u)), 15, 15 * CA, fc="#e8a33d", ec="#7a4b00"))
    for u in AP.FADER_U:
        rect(ax, AP.FADER_X - 31, slant_z(u) - 1, 62, 2, fc="#111", ec="none")
    for x in AP.TOG_X:
        rect(ax, x - 7.5, slant_z(AP.TOG_U) - 10, 15, 26, fc="#b22", ec="#600")
        ax.add_patch(Ellipse((x, slant_z(AP.LAMP_U)), 19.5, 19.5 * CA, fc="#ccc", ec="#666"))
    for x in AP.KEY_X:
        for u in AP.KEY_U:
            rect(ax, x - 12, slant_z(u) - 9 * CA, 24, 18 * CA, fc="#f2c96b", ec="#8a6a1a")
    # 底座条
    rect(ax, 2, 0, W - 4, zb, fc="#44474d", ec="#222")
    label(ax, W / 2, zb / 2, "底座条（X1 键盘座）", 8, color="white")
    # 尺寸
    ax.annotate("", (0, H + 10), (W, H + 10), arrowprops=dict(arrowstyle="<->", lw=0.8))
    label(ax, W / 2, H + 15, f"{W}", 9)
    for z, t in ((H, f"{H}"), (zc, f"{zc:.0f} 面板下沿 / 斜面上沿"), (zb, f"{zb:.1f} 斜面下沿"), (0, "0")):
        ax.plot([W + 3, W + 12], [z, z], color="#333", lw=0.8)
        ax.text(W + 14, z, t, va="center", fontproperties=F, fontsize=8)
    label(ax, -22, (zc + H) / 2, "竖直前面板\n320×332×2", 9, rotation=90)
    label(ax, -22, (zb + zc) / 2, "斜面\n展开 316×83", 8, rotation=90)
    ax.text(0, -18, "虚线框 = 后面的 2020 立柱 / 横梁；蓝点线 = 背面亚克力；白点 = M4 固定孔（锁进立柱、顶横梁的 T 螺母）",
            fontproperties=F, fontsize=8, color="#444")


def side_view(ax):
    ax.set_xlim(-75, 70); ax.set_ylim(-25, H + 20); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("侧视（x = 160 剖开，左边是前面；立柱是后方投影）", fontproperties=F, fontsize=11)
    # 机架：立柱（侧面）、前下 / 前上横梁、甲板、电脑层、底板
    rect(ax, 0, 0, 20, H, fc="#e6e6e6", ec="#999", ls="--", lw=0.8)
    label(ax, 10, 330, "2020\n立柱\n（x 0–20）", 7, color="#666")
    rect(ax, 0, 0, 20, 20, fc="#b8bcc2", ec="#555")
    rect(ax, 0, H - 20, 20, 20, fc="#b8bcc2", ec="#555")
    label(ax, 35, 10, "前下横梁", 7, ha="left")
    rect(ax, 2, Z_DECK, 70, PLATE_T, fc="#d0603a", ec="#7a2a10")
    label(ax, 48, Z_DECK + 10, "甲板 z90", 7)
    rect(ax, 30, Z_SHELF, 40, PLATE_T, fc="#d0603a", ec="#7a2a10")
    label(ax, 50, Z_SHELF + 10, "电脑层", 7)
    rect(ax, 0, -PLATE_T, 70, PLATE_T, fc="#d0603a", ec="#7a2a10")
    # EL 屏
    rect(ax, 3, Z_SCREEN, 8, 220, fc="#d98a1c", ec="#7a4b00", alpha=0.6)
    label(ax, 30, Z_SCREEN + 110, "EL 屏", 8)
    # 前面板
    rect(ax, -2, AP.Z_CHIN, 2, H - AP.Z_CHIN, fc="#555", ec="#000")
    label(ax, -12, 250, "前面板 2 mm", 8, rotation=90)
    # 斜面（2 mm 厚）、底座条、下底板
    yb, zb, zc = AP.Y_BASE, AP.Z_BASE, AP.Z_CHIN
    nx, nz = CA * 2, -SA * 2      # 斜面法向（朝里）
    ax.add_patch(Polygon([(-2, zc), (yb, zb), (yb + nx, zb + nz), (-2 + nx, zc + nz)], closed=True, fc="#333", ec="#000"))
    rect(ax, yb, 0, 2, zb - 2 * SA, fc="#333", ec="#000")
    rect(ax, yb, -3, -yb, 3, fc="#222", ec="#000")
    label(ax, (yb - 2) / 2 - 10, (zb + zc) / 2 + 4, "斜面 33°", 8, rotation=57)
    label(ax, yb - 9, zb / 2, "底座条", 7, rotation=90)
    # 斜面电路板（离斜面内表面 6.5）
    u0, u1 = AP.PCB_U
    off = 2 + AP.PCB_D
    p = lambda u, o: (yb + u * SA + o * CA, zb + u * CA - o * SA)
    ax.add_patch(Polygon([p(u0, off), p(u1, off), p(u1, off + 1.6), p(u0, off + 1.6)], closed=True, fc="#2f7d3a", ec="#174"))
    label(ax, -12, 40, "斜面\n电路板", 7, color="#174")
    # 侧封板轮廓（在 x 0–2 和 318–320，这里画外形虚线）
    ax.add_patch(Polygon([(0, 0), (0, zc), (-2, zc), (yb, zb), (yb, 0)], closed=True, fc="none", ec="#1f7fbf", ls=":", lw=1.2))
    label(ax, -40, -14, "蓝点线 = 两侧三角封板外形", 7, color="#1f7fbf")
    # 尺寸
    ax.annotate("", (yb, -10), (0, -10), arrowprops=dict(arrowstyle="<->", lw=0.8))
    label(ax, yb / 2, -6, f"前探 {-yb:.0f}", 7.5)


def main(fname="png/20_front_panel.png"):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 11), dpi=110, gridspec_kw=dict(width_ratios=[3.2, 1.25]))
    front_view(a1); side_view(a2)
    fig.suptitle("MIS-01 前面板现状（2026-10-21）", fontproperties=F, fontsize=15)
    fig.tight_layout(); fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname)


if __name__ == "__main__":
    main()
