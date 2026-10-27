"""丝印设计稿：png/29_silkscreen.png（两面预览，带操作件外形）+ 外壳加工/丝印/ 下两面 1:1 PDF 和给嘉立创的合并 DXF（silk_dxf.py）。
图形取自 silkscreen.py，开孔取自 assembly_panel.FEATURES。
运行：PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe fig_silkscreen.py"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Rectangle, Circle, FancyBboxPatch
from matplotlib.path import Path
import assembly_panel as AP
import parts_dock as PD
import parts_panel as F
import silkscreen as S
import render as R

OUT = "外壳加工/丝印"
CREAM, INK, HOLE, REF = "#ece4d4", "#111111", "#4a4a4a", "#d0201a"
FACE = {  # 面外形（x0, y0, w, h）、标题
    "front": ((AP.SHELL_X0, AP.Z_CHIN + 0.5, AP.SHELL_W, AP.H - AP.Z_CHIN - 0.5), "前面板（正视，x–z）"),
    "slant": ((0.0, AP.U_EDGE, AP.W, AP.SLANT_TOP_U - AP.U_EDGE), "斜面（垂直斜面看，x–u；u 0 = 斜面电路板下沿）"),
}


def poly_path(polys):
    verts, codes = [], []
    for o, hs in polys:
        for ring in [o] + hs:
            verts += list(ring) + [ring[0]]
            codes += [Path.MOVETO] + [Path.LINETO] * (len(ring) - 1) + [Path.CLOSEPOLY]
    return Path(np.array(verts), codes)


def draw_ref(ax, face, color, lw, fill=None):
    """面外形 + 开孔 / 开窗（参考，不印）"""
    (x0, y0, w, h), _ = FACE[face]
    ax.add_patch(Rectangle((x0, y0), w, h, fc=fill or "none", ec=color, lw=lw))
    cut, holes = AP.FEATURES[face]
    for c in cut:
        x, y, cw, ch = c[:4]
        ax.add_patch(Rectangle((x, y), cw, ch, fc=HOLE if fill else "none", ec=color, lw=lw))
    for x, y, d in holes:
        ax.add_patch(Circle((x, y), d / 2, fc=HOLE if fill else "none", ec=color, lw=lw))


def draw_parts(ax, face):
    """操作件外形（虚线，看丝印会不会被盖住）"""
    kw = dict(fc="none", ec="#7a8899", ls="--", lw=0.7)
    if face == "front":
        mx, mz = AP.METER
        ax.add_patch(FancyBboxPatch((mx - 32, mz - 28), 64, 56, boxstyle="round,pad=0,rounding_size=3", **kw))
        for x, z in [(x, z) for x in (10, AP.W - 10) for z in (140, 280, 410)] + [(110, AP.H - 10), (210, AP.H - 10)]:
            ax.add_patch(Circle((x, z), 4.0, **kw))                                     # M4 螺钉头
        return
    ax.add_patch(Circle(AP.SEL, 16, **kw))                                              # 指针旋钮裙边 Ø32
    for x, u in AP.USB:
        ax.add_patch(Rectangle((x - 7.75, u - 7.25), 15.5, 14.5, **kw))
        for sx in (-1, 1):
            ax.add_patch(Circle((x + sx * 15, u), 3.0, **kw))                            # M3 螺钉头
    for x, u in AP.ENC:
        ax.add_patch(Circle((x, u), 7.5, **kw))                                         # 旋钮 Ø15
    cw = 10.0
    for u, pos in zip(AP.FADER_U, (0.7, 0.35)):
        x = AP.FADER_X - 30 + 60 * pos
        ax.add_patch(Rectangle((x - cw / 2, u - 6), cw, 12, **kw))                      # 推子帽 10×12
    for x in AP.TOG_X:
        ax.add_patch(Circle((x, AP.TOG_U), 6.0, **kw))                                  # 钮子螺母 + 垫圈
        ax.add_patch(Circle((x, AP.LAMP_U), 9.5, **kw))                                 # 指示灯灯头 Ø19
    for x in AP.KEY_X:
        for u in AP.KEY_U:
            ax.add_patch(Rectangle((x - 12, u - 9), 24, 18, **kw))                      # 方键面框 24×18
    for x in PD.SPEC["tongue_x"]:
        ax.add_patch(Circle((AP.W / 2 + x, AP.U_EDGE + PD.SCREW_U), 3.0, **kw))         # 键盘座 M3 沉头
    ax.axhline(S.U_MAX, color="#c08000", lw=0.6, ls=":")


def preview(fname="png/29_silkscreen.png"):
    els = dict(S.elements())
    fig, axs = plt.subplots(2, 1, figsize=(13, 17.5), dpi=130, gridspec_kw=dict(height_ratios=[332, 115]))
    for ax, face in zip(axs, ("front", "slant")):
        draw_ref(ax, face, "#555", 0.6, fill=CREAM)
        draw_parts(ax, face)
        ax.add_patch(PathPatch(poly_path(els[face]), fc=INK, ec="none"))
        (x0, y0, w, h), title = FACE[face]
        ax.set_xlim(x0 - 4, x0 + w + 4); ax.set_ylim(y0 - 4, y0 + h + 4)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(title, fontproperties=R.FONT, fontsize=12)
    note = ("米白喷粉 + 黑色丝印。虚线 = 装上后的旋钮 / 灯头 / 键框 / 螺钉头外形（不印）；橙点线 = 斜面丝印上限 u 77（折弯在 u 83）。\n"
            f"字体 Bahnschrift（DIN 风格）；字高：机名 {S.CAP['logo']:g}、钮子名 {S.CAP['name']:g}、档位 {S.CAP['num']:g}、ON/OFF {S.CAP['onoff']:g}、"
            f"推子数字 {S.CAP['scale']:g}；线宽 {S.LINE:g}（档位刻度 0.6）。")
    fig.text(0.5, 0.012, note, ha="center", fontproperties=R.FONT, fontsize=10)
    fig.suptitle("MIS-01 前壳丝印设计稿", fontproperties=R.FONT, fontsize=16)
    fig.tight_layout(rect=(0, 0.03, 1, 0.98)); fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname)


def pdf_1to1(face, fname):
    """1:1 PDF：黑 = 丝印，红细线 = 面外形和开孔（定位参考，不印），四周留 15 mm 写说明"""
    (x0, y0, w, h), title = FACE[face]
    m = 15.0
    fig = plt.figure(figsize=((w + 2 * m) / 25.4, (h + 2 * m) / 25.4))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(x0 - m, x0 + w + m); ax.set_ylim(y0 - m, y0 + h + m); ax.axis("off")
    draw_ref(ax, face, REF, 0.3)
    ax.add_patch(PathPatch(poly_path(dict(S.elements())[face]), fc="black", ec="none"))
    ax.text(x0, y0 - 6, f"MIS-01 {title} 丝印 1:1（单位 mm）。黑色 = 丝印（黑），红线 = 钣金外形与开孔，仅定位用，不印。",
            fontproperties=R.FONT, fontsize=7, color=REF, va="center")
    fig.savefig(fname); plt.close(fig)
    print("saved", fname)


def main():
    import silk_dxf
    AP.front_panel(); AP.slant()                                                   # 填 FEATURES
    for m in S.check():
        print("CHECK", m)
    preview()
    os.makedirs(OUT, exist_ok=True)
    for face, name in (("front", "前面板"), ("slant", "斜面")):
        pdf_1to1(face, f"{OUT}/丝印_{name}_1比1.pdf")
    silk_dxf.write(f"{OUT}/{silk_dxf.NAME}")


if __name__ == "__main__":
    main()
