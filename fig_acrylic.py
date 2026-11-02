"""前面板观察窗亚克力 ×3 加工图：外壳加工/亚克力/ 下每块一份 1:1 DXF（激光切割外形）+ 一份合并 PDF（1:1，带尺寸、贴装位置），
另出 png/34_acrylic.png（三块在前面板背面的位置示意）。尺寸取自 assembly_panel.ACRYLIC / ACRYLIC_T / ACRYLIC_R 和三个窗口。
运行：PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe fig_acrylic.py"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.backends.backend_pdf import PdfPages
import ezdxf
import assembly_panel as AP
import render as R

F = R.FONT
OUT = "外壳加工/亚克力"
FILE = {"niche": "亚克力_管龛窗", "eye": "亚克力_6E2窗", "geiger": "亚克力_盖革窗"}
NOTES = [
    "材料：透明浇铸亚克力（PMMA）",
    f"厚 {AP.ACRYLIC_T:g} mm，各 1 件，激光切割外形",
    f"四角 R{AP.ACRYLIC_R:g}，无孔；切边去毛刺，两面保护膜不撕",
    "未注公差 ±0.2",
]
MOUNT = [
    "贴装：贴在前面板内表面（背面），盖住对应窗口，四周压边见图",
    "胶：四周实心边点 UV 胶，或 ≤ 0.2 mm 薄双面胶；不用整片 VHB",
    "（背后甲板、盖革夹子板前沿离面板只有 2 mm，胶层总厚 ≤ 0.4）",
    "盖革窗这块必须装：后面有 400 V 焊盘",
]
DIM = dict(dimlfac=1.0, dimdsep=46, dimtxt=3.0, dimasz=2.0, dimexe=1.5, dimexo=1.0, dimgap=0.8, dimdec=2, dimzin=8)


def size(k):
    x0, x1, z0, z1 = AP.ACRYLIC[k]["box"]
    return x1 - x0, z1 - z0


def window(k):
    """窗口在这块亚克力自身坐标里的位置（左下角为原点，从前面看）"""
    x0, _, z0, _ = AP.ACRYLIC[k]["box"]
    wx, wz, ww, wh = getattr(AP, AP.ACRYLIC[k]["win"])[:4]
    return wx - x0, wz - z0, ww, wh


def dxf(k, fname):
    """CUT 层 = 激光切割外形（1:1，mm，原点 = 左下角，从面板正面看）；REF 层 = 窗口位置（不切）；DIM 层 = 尺寸"""
    w, h = size(k)
    r = AP.ACRYLIC_R
    doc = ezdxf.new("R2010", units=ezdxf.units.MM, setup=True)
    for n, c in (("CUT", 1), ("REF", 8), ("DIM", 3)):
        doc.layers.add(n, color=c)
    msp = doc.modelspace()
    pts = [(r, 0, 0), (w - r, 0, 0.4142), (w, r, 0), (w, h - r, 0.4142), (w - r, h, 0), (r, h, 0.4142), (0, h - r, 0), (0, r, 0.4142)]
    msp.add_lwpolyline([(x, y, 0, 0, b) for x, y, b in pts], format="xyseb", close=True, dxfattribs=dict(layer="CUT"))
    wx, wz, ww, wh = window(k)
    msp.add_lwpolyline([(wx, wz), (wx + ww, wz), (wx + ww, wz + wh), (wx, wz + wh)], close=True, dxfattribs=dict(layer="REF"))
    for base, p1, p2, ang in (((0, -8), (0, 0), (w, 0), 0), ((-8, 0), (0, 0), (0, h), 90)):
        msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=ang, dimstyle="EZDXF", override=DIM, dxfattribs=dict(layer="DIM")).render()
    doc.saveas(fname)
    print("saved", fname)


def draw(ax, k, scale_note=True):
    """一块亚克力：外形 + 窗口虚线 + 尺寸 + 四边压边"""
    w, h = size(k)
    r = AP.ACRYLIC_R
    wx, wz, ww, wh = window(k)
    ax.add_patch(FancyBboxPatch((0, 0), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc="#d9eef8", ec="#1f5f8b", lw=0.8))
    ax.add_patch(Rectangle((wx, wz), ww, wh, fc="none", ec="#888", lw=0.5, ls="--"))
    t = dict(fontproperties=F, fontsize=7, ha="center", va="center")
    ax.annotate("", (0, -5), (w, -5), arrowprops=dict(arrowstyle="<->", lw=0.5))
    ax.text(w / 2, -8, f"{w:g}", **t)
    ax.annotate("", (-5, 0), (-5, h), arrowprops=dict(arrowstyle="<->", lw=0.5))
    ax.text(-8, h / 2, f"{h:g}", rotation=90, **t)
    m = dict(fontproperties=F, fontsize=5.5, color="#555", ha="center", va="center")
    ax.text(wx / 2, wz + wh / 2, f"{wx:g}", rotation=90, **m)
    ax.text(w - (w - wx - ww) / 2, wz + wh / 2, f"{w - wx - ww:g}", rotation=90, **m)
    ax.text(wx + ww / 2, wz / 2, f"{wz:g}", **m)
    ax.text(wx + ww / 2, h - (h - wz - wh) / 2, f"{h - wz - wh:g}", **m)
    ax.text(w / 2, h / 2, f"{AP.ACRYLIC[k]['name']}\n{w:g} × {h:g} × {AP.ACRYLIC_T:g}，四角 R{r:g}", **dict(t, fontsize=8))


def pdf(fname):
    """1:1 A3 横向，三块排在一页，带说明"""
    W3, H3 = 420, 297
    fig = plt.figure(figsize=(W3 / 25.4, H3 / 25.4))
    pos = {"niche": (25, 160), "geiger": (210, 160), "eye": (230, 45)}
    for k, (px, py) in pos.items():
        w, h = size(k)
        ax = fig.add_axes(((px - 12) / W3, (py - 12) / H3, (w + 24) / W3, (h + 24) / H3))
        ax.set_xlim(-12, w + 12); ax.set_ylim(-12, h + 12); ax.set_aspect("equal"); ax.axis("off")
        draw(ax, k)
    tx = fig.add_axes((25 / W3, 20 / H3, 190 / W3, 110 / H3)); tx.axis("off")
    lines = ["MIS-01 前面板观察窗亚克力 ×3　比例 1:1　单位 mm", ""] + NOTES + [""] + MOUNT + [
        "", "图中：实线 = 切割外形；灰色虚线 = 前面板窗口位置（不切）；小字 = 四边压边宽度。",
        "从面板正面看；三块都不分正反。切割文件：" + "、".join(f"{v}.dxf" for v in FILE.values())]
    tx.text(0, 1, "\n".join(lines), va="top", fontproperties=F, fontsize=8.5, linespacing=1.6)
    with PdfPages(fname) as p:
        p.savefig(fig)
    plt.close(fig)
    print("saved", fname)


def overview(fname="png/34_acrylic.png"):
    """三块在前面板背面的位置（从前面看），和窗口、表头螺柱、托架的关系"""
    fig, ax = plt.subplots(figsize=(13, 5.2), dpi=120)
    ax.add_patch(Rectangle((AP.SHELL_X0, AP.Z_CHIN), AP.SHELL_W, 100, fc="#ece4d4", ec="#555"))
    for k, a in AP.ACRYLIC.items():
        x0, x1, z0, z1 = a["box"]
        wx, wz, ww, wh = getattr(AP, a["win"])[:4]
        ax.add_patch(Rectangle((wx, wz), ww, wh, fc="#3a3a3a", ec="none"))
        ax.add_patch(FancyBboxPatch((x0, z0), x1 - x0, z1 - z0, boxstyle=f"round,pad=0,rounding_size={AP.ACRYLIC_R}",
                                    fc="#7fc8f0", alpha=0.45, ec="#1f5f8b", lw=1.2))
        ly = (z0 + z1) / 2 - 1.5 if k == "geiger" else z1 + 2.5          # 盖革那块上面是表头螺柱说明，标签放在窗口里
        ax.text((x0 + x1) / 2, ly, f"{a['name']}  {x1 - x0:g}×{z1 - z0:g}", ha="center", fontproperties=F, fontsize=8, color="white" if k == "geiger" else "#1f5f8b")
    mx, mz = AP.METER
    ms = AP.F.METER_SPEC
    for sx in (-1, 1):
        ax.plot(mx + sx * ms["stud_dx"] / 2, mz + ms["stud_z"], "o", ms=7, mfc="none", mec="#c00")
    ax.text(mx, mz + ms["stud_z"] - 7, "表头 M3 螺柱（螺母 + 垫片到 x 244）", ha="center", fontproperties=F, fontsize=7, color="#c00")
    for x0, w, z0, lab in ((20, 2, 176, "左 EL 托架腿 x 20–22"), (298, 2, 176, "右 EL 托架 x ≥ 298、z ≥ 176")):
        ax.add_patch(Rectangle((x0, z0), w, 12, fc="#c00", alpha=0.5))
        ax.text(x0, z0 + 13, lab, fontproperties=F, fontsize=7, color="#c00", ha="center")
    ax.axhline(88.5, color="#c08000", ls=":", lw=0.8)
    ax.text(2, 84.5, "折弯内切点 z 88.5", fontproperties=F, fontsize=7, color="#c08000")
    ax.set_xlim(-5, 325); ax.set_ylim(82, 192); ax.set_aspect("equal")
    ax.set_xlabel("x（mm，从前面看）", fontproperties=F); ax.set_ylabel("z（mm）", fontproperties=F)
    ax.set_title(f"前面板观察窗亚克力 ×3（厚 {AP.ACRYLIC_T:g}，贴在面板背面；深灰 = 窗口，蓝 = 亚克力）", fontproperties=F, fontsize=11)
    fig.tight_layout(); fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname)


def main():
    os.makedirs(OUT, exist_ok=True)
    for k, n in FILE.items():
        dxf(k, f"{OUT}/{n}.dxf")
    pdf(f"{OUT}/亚克力_观察窗x3_1比1.pdf")
    overview()


if __name__ == "__main__":
    main()
