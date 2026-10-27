"""EL 接口板位置图（俯视 + 侧视）→ png/33_elif_placement.png。
位置、插座、过线孔取自 assembly_computers（EL_IF_REF、SHELF_PMOD_HOLE、el_if_pt）；周围零件外框取自整机 items 的包围盒。
用法：main(items)，items = assembly.build() 的返回值；单独运行时现建（约 5 min）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import render as R
import assembly_computers as AC
from assembly_base import W, Z_SCREEN

F = R.FONT
J_LOCAL = {"J_EL": (90.7, 47), "P1": (4.2, 50), "P2": (4.2, 30), "P3": (4.2, 74), "J_PWR": (72, 94), "J_PF": (27.4, 96), "J_LAMP": (75, 4.5)}   # EL-IF D1.2/D1.3 变更记录
HDR = {"DISPLAY 位": 184.5, "CAM 位": 204, "TP 位": 225, "GPIO 位": 247.5}   # Dock 前沿 4 个 2×6 座中心 x（整机模型 Tang20K_Dock 切片），y ≈ 111
CN5 = (W / 2, 26.5, Z_SCREEN + 220 / 2 - 59)                                   # 屏背面中线、中心以下 59（2026-10-28 用户确认）


def main(items=None, fname="png/33_elif_placement.png"):
    if items is None:
        import assembly as A
        items = A.build()
    meta = {}
    for n, shp, *_ in items:
        b = shp.val().BoundingBox()
        meta.setdefault(n, [b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax])
    X0, Y0 = AC.EL_IF_REF
    ZT = AC.EL_IF_TOP
    g = AC.el_if_pt
    HOLE = (AC.SHELF_PMOD_HOLE[0], AC.SHELF_PMOD_HOLE[1], AC.SHELF_PMOD_HOLE[2] / 2)
    J = {k: g(*v) for k, v in J_LOCAL.items()}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(17, 9), dpi=110, gridspec_kw=dict(width_ratios=[1.45, 1]))
    # ---- 俯视（只画电脑层上下相关的东西）
    a1.set_title("俯视：EL-IF 吊在电脑层板下面（元件朝上，转 180°）", fontproperties=F, fontsize=12)
    for n, c, a in (("Sharp_LJ64K052", "#d98a1c", 0.25), ("Tang20K_Dock", "#2f7d3a", 0.25), ("OrangePi_4", "#3b6fb6", 0.2),
                    ("USB_Hub_4port", "#888", 0.25), ("EL_bracket_L", "#aaa", 0.4), ("EL_bracket_R", "#aaa", 0.4)):
        b = meta[n]; a1.add_patch(Rectangle((b[0], b[1]), b[3] - b[0], b[4] - b[1], fc=c, alpha=a, ec="#555", lw=0.6))
        a1.text((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, n.replace("_", " ") + ("（层板上面）" if n in ("Tang20K_Dock", "OrangePi_4", "USB_Hub_4port") else ""),
                ha="center", va="center", fontproperties=F, fontsize=7, color="#333")
    a1.add_patch(Rectangle((X0 - 100, Y0 - 100), 100, 100, fc="#1f6b35", alpha=0.55, ec="#0b3", lw=1.5))
    a1.text(X0 - 50, Y0 - 9, f"EL-IF D1.3  100×100  板面 z {ZT:g}（层板下面）", ha="center", va="center", fontproperties=F, fontsize=9, color="white")
    for hx, hy in ((5, 5), (95, 5), (5, 95), (95, 95)):
        a1.add_patch(Circle(g(hx, hy), 2.5, fc="white", ec="k", lw=0.8))
    a1.add_patch(Circle(HOLE[:2], HOLE[2], fc="none", ec="#c00", lw=1.6, ls="--"))
    a1.text(HOLE[0] + HOLE[2] + 3, HOLE[1] + 3, "层板新开 Ø25\n过线孔（以孔阵孔\n为圆心当导孔）", fontproperties=F, fontsize=8, color="#c00")
    for k, (x, y) in J.items():
        a1.plot(x, y, "s", color="#ff0", mec="k", ms=6); a1.text(x + 2, y + 2, k, fontproperties=F, fontsize=8)
    for k, x in HDR.items():
        a1.add_patch(Rectangle((x - 7.6, 108.6), 15.2, 5.1, fc="#fff", ec="#060", lw=1)); a1.text(x - 7, 104, k, fontproperties=F, fontsize=6.5, color="#060")
    jx, jy = J["J_EL"]
    a1.plot([jx, jx - 20, 130, 130, CN5[0]], [jy, jy, jy - 12, 50, CN5[1] + 8], color="#06c", lw=2.2)
    a1.text(108, 70, "DF11 20P\n走线约 12 cm\n（20 cm 线，余量盘起）", fontproperties=F, fontsize=8.5, color="#06c")
    a1.plot(CN5[0], CN5[1], "o", color="#06c", ms=8); a1.text(CN5[0] + 3, CN5[1] - 9, "屏 CN5（背面）", fontproperties=F, fontsize=8, color="#06c")
    for k in ("P1", "P2", "P3"):
        x, y = J[k]; a1.plot([x, HOLE[0]], [y, HOLE[1]], color="#c60", lw=1.4)
    a1.set_xlim(0, 320); a1.set_ylim(0, 200); a1.set_aspect("equal"); a1.grid(alpha=0.2)
    a1.set_xlabel("x（mm，向右）", fontproperties=F); a1.set_ylabel("y（mm，向后；前面板在 y 0）", fontproperties=F)
    # ---- 侧视（x = 225 附近剖，看高度）
    a2.set_title("侧视（从右往左看，前面在左）", fontproperties=F, fontsize=12)
    def zr(n, c, a=0.3, lab=None):
        b = meta[n]; a2.add_patch(Rectangle((b[1], b[2]), b[4] - b[1], b[5] - b[2], fc=c, alpha=a, ec="#555", lw=0.6))
        if lab: a2.text((b[1] + b[4]) / 2, (b[2] + b[5]) / 2, lab, ha="center", va="center", fontproperties=F, fontsize=7.5)
    zr("Sharp_LJ64K052", "#d98a1c", 0.3, "EL 屏")
    zr("shelf_plate_bakelite", "#d0603a", 0.8)
    zr("Tang20K_Dock", "#2f7d3a", 0.35, "Dock")
    a2.add_patch(Rectangle((Y0 - 100, ZT - 1.6), 100, 1.6, fc="#1f6b35", ec="k"))
    a2.add_patch(Rectangle((Y0 - 100, ZT), 100, 15.7, fc="#1f6b35", alpha=0.25, ec="#1f6b35", ls=":"))
    for yy in (Y0 - 5, Y0 - 95):
        a2.add_patch(Rectangle((yy - 2.75, ZT), 5.5, 30, fc="#c9a227", ec="k", lw=0.5))
    a2.text(Y0 - 50, ZT + 21, f"M3×{AC.EL_IF_STANDOFF} 铜柱 ×4（吊在层板下，孔阵孔，上面沉头）", ha="center", fontproperties=F, fontsize=8)
    a2.add_patch(Rectangle((HOLE[1] - HOLE[2], 260), 2 * HOLE[2], 4, fc="white", ec="#c00", lw=1.2, ls="--"))
    a2.plot([CN5[1], 50, 113], [CN5[2], ZT + 2, ZT + 2], color="#06c", lw=2); a2.plot(CN5[1], CN5[2], "o", color="#06c", ms=7)
    a2.text(32, 212, "CN5 z 229，DF11 基本水平", fontproperties=F, fontsize=8, color="#06c")
    a2.set_xlim(0, 200); a2.set_ylim(170, 300); a2.set_aspect("equal"); a2.grid(alpha=0.2)
    a2.set_xlabel("y（mm）", fontproperties=F); a2.set_ylabel("z（mm）", fontproperties=F)
    fig.suptitle("EL-IF 位置方案：电脑层板下面、屏背后（2026-10-28 用户确认）", fontproperties=F, fontsize=14)
    fig.tight_layout(); fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname)


if __name__ == "__main__":
    main()
