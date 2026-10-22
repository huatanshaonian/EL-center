"""2D 加工图公用工具（fig_dock_drawing.py、fig_sheet_drawing.py 共用）：
- hlr()：用 OCC 隐藏线算法把 3D 实体投影成可见线 / 隐藏线；
- Sheet：一页 A3 横向图纸（坐标单位 = 图纸 mm），画视图、尺寸、坐标标注、引线、标题栏，存进 PdfPages。
视图方向：eye = 从零件指向看图人的方向，xdir = 图纸 x 轴对应的零件方向，图纸 y 轴 = eye × xdir。"""
import datetime
import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
import render as R

F = R.FONT
VIEWS = {"front": ((0, -1, 0), (1, 0, 0)), "back": ((0, 1, 0), (-1, 0, 0)),
         "top": ((0, 0, 1), (1, 0, 0)), "bottom": ((0, 0, -1), (1, 0, 0)),
         "right": ((1, 0, 0), (0, 1, 0)), "left": ((-1, 0, 0), (0, -1, 0))}


def proj(p, view):
    eye, xd = (np.array(v, float) for v in VIEWS[view])
    p = np.array(p, float)
    return float(p @ xd), float(p @ np.cross(eye, xd))


def hlr(shape, view):
    """返回 (可见线, 隐藏线)，每条是 N×2 数组（投影坐标）"""
    eye, xd = VIEWS[view]
    h = HLRBRep_Algo(); h.Add(shape.val().wrapped)
    h.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*eye), gp_Dir(*xd)))); h.Update(); h.Hide()
    r = HLRBRep_HLRToShape(h)

    def lines(names):
        out = []
        for n in names:
            c = getattr(r, n)()
            if c.IsNull():
                continue
            for e in cq.Shape.cast(c).Edges():
                k = 2 if e.geomType() == "LINE" else 32
                out.append(np.array([(q.x, q.y) for q in (e.positionAt(t) for t in np.linspace(0, 1, k))]))
        return out
    return lines(("VCompound", "Rg1LineVCompound", "OutLineVCompound")), lines(("HCompound", "OutLineHCompound"))


def extent(shape, view):
    """零件在该视图里的投影范围 (xmin, xmax, ymin, ymax)，用包围盒 8 个角算"""
    b = shape.val().BoundingBox()
    pts = [proj((x, y, z), view) for x in (b.xmin, b.xmax) for y in (b.ymin, b.ymax) for z in (b.zmin, b.zmax)]
    xs, ys = zip(*pts)
    return min(xs), max(xs), min(ys), max(ys)


def place(shape, view, sc, x_left, y_bottom):
    """让视图投影范围的左下角落在图纸 (x_left, y_bottom)：返回 Sheet.view 要的 (ox, oy)"""
    x0, _, y0, _ = extent(shape, view)
    return x_left - sc * x0, y_bottom - sc * y0


class Sheet:
    """一页 A3 横向图纸"""
    def __init__(self, pdf, title, page=1, total=1, material="", qty="1", tol="±0.1"):
        self.pdf, self.title, self.page, self.total = pdf, title, page, total
        self.material, self.qty, self.tol = material, qty, tol
        self.fig = plt.figure(figsize=(420 / 25.4, 297 / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1]); self.ax.set_xlim(0, 420); self.ax.set_ylim(0, 297); self.ax.axis("off")
        self.ax.add_patch(plt.Rectangle((5, 5), 410, 287, fill=False, lw=0.8))

    def text(self, x, y, s, size=7, **kw):
        self.ax.text(x, y, s, fontproperties=F, fontsize=size, **kw)

    def view(self, shape, view, ox, oy, sc, label, clip_x=None, hidden=True, label_below=True):
        """画一个视图：投影坐标 (u, v) → 图纸 (ox + sc·u, oy + sc·v)。返回 3D 点 → 图纸坐标的函数"""
        vis, hid = hlr(shape, view)
        T = lambda a: np.column_stack((ox + sc * a[:, 0], oy + sc * a[:, 1]))
        keep = (lambda a: True) if clip_x is None else \
            (lambda a: a[:, 0].max() >= clip_x[0] - 1e-6 and a[:, 0].min() <= clip_x[1] + 1e-6)
        clipper = (lambda a: a) if clip_x is None else (lambda a: np.column_stack((np.clip(a[:, 0], *clip_x), a[:, 1])))
        if hidden:
            for a in hid:
                if keep(a):
                    b = T(clipper(a)); self.ax.plot(b[:, 0], b[:, 1], color="0.6", lw=0.25, ls=(0, (2, 1.5)))
        for a in vis:
            if keep(a):
                b = T(clipper(a)); self.ax.plot(b[:, 0], b[:, 1], color="k", lw=0.5)
        x0, x1, y0, y1 = extent(shape, view)
        lx = ox + sc * (clip_x[0] if clip_x else x0) + 3
        ly = oy + sc * y0 - 7 if label_below else oy + sc * y1 + 3
        self.text(lx, ly, label, size=8, weight="bold")
        return lambda p: (ox + sc * proj(p, view)[0], oy + sc * proj(p, view)[1])

    def overall(self, shape, view, f, gap=8, txt_w=None, txt_h=None, gap_w=14):
        """在视图下方标总宽、右侧标总高（投影包围盒）"""
        x0, x1, y0, y1 = extent(shape, view)
        sx0, sy0 = f_inv(f, shape, view, x0, y0)
        sx1, sy1 = f_inv(f, shape, view, x1, y1)
        self.dim_h((sx0, sy0), (sx1, sy0), sy0 - gap_w, txt_w or f"{x1 - x0:.1f}".rstrip("0").rstrip("."))
        if txt_h is not False:                   # txt_h=False：不标高
            self.dim_v((sx1, sy0), (sx1, sy1), sx1 + gap, txt_h or f"{y1 - y0:.1f}".rstrip("0").rstrip("."))

    # ---- 尺寸
    def dim_h(self, p1, p2, y, txt=None, size=6.5):
        (x1, y1), (x2, y2) = p1, p2
        for x, yy in ((x1, y1), (x2, y2)):
            self.ax.plot([x, x], [yy, y + (1 if y > yy else -1)], color="k", lw=0.25)
        self.ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<->", lw=0.35, shrinkA=0, shrinkB=0, mutation_scale=5))
        self.text((x1 + x2) / 2, y + 0.6, txt, size=size, ha="center", va="bottom")

    def dim_v(self, p1, p2, x, txt=None, size=6.5):
        (x1, y1), (x2, y2) = p1, p2
        for xx, yy in ((x1, y1), (x2, y2)):
            self.ax.plot([xx, x + (1 if x > xx else -1)], [yy, yy], color="k", lw=0.25)
        self.ax.annotate("", (x, y1), (x, y2), arrowprops=dict(arrowstyle="<->", lw=0.35, shrinkA=0, shrinkB=0, mutation_scale=5))
        self.text(x + (0.8 if x > x1 else -0.8), (y1 + y2) / 2, txt, size=size, ha="left" if x > x1 else "right", va="center")

    def ordinate(self, pts, ylab, txts, size=6, up=True):
        """坐标标注：每个点竖线引到 ylab，文字竖排"""
        for (x, y), t in zip(pts, txts):
            self.ax.plot([x, x], [y, ylab], color="0.35", lw=0.2)
            self.text(x, ylab + (0.5 if up else -0.5), t, size=size, rotation=90, ha="center", va="bottom" if up else "top")

    def leader(self, p, q, txt, size=6.5):
        self.ax.annotate(txt, p, q, fontproperties=F, fontsize=size, arrowprops=dict(arrowstyle="-|>", lw=0.35, mutation_scale=5),
                         va="center")

    def notes(self, x, y, lines, step=6):
        for i, n in enumerate(lines):
            self.text(x, y - step * i, n, size=8 if i == 0 else 7)

    def title_block(self, scale):
        x0, y0 = 275, 8
        self.ax.add_patch(plt.Rectangle((x0, y0), 137, 40, fill=False, lw=0.6))
        rows = [("零件", self.title), ("材料", self.material), ("数量", self.qty), ("比例", scale),
                ("单位 / 未注公差", f"mm / {self.tol}"),
                ("日期 / 页", f"{datetime.date.today()} / 第 {self.page} 页 共 {self.total} 页")]
        for i, (k, v) in enumerate(rows):
            y = y0 + 40 - 6.4 * (i + 1) + 1.6
            self.text(x0 + 2, y, k, size=7); self.text(x0 + 32, y, v, size=7.5)
            if i:
                self.ax.plot([x0, x0 + 137], [y + 4.8, y + 4.8], color="k", lw=0.3)
        self.ax.plot([x0 + 30, x0 + 30], [y0, y0 + 40], color="k", lw=0.3)

    def save(self):
        self.pdf.savefig(self.fig); plt.close(self.fig)


def f_inv(f, shape, view, u, v):
    """投影坐标 (u, v) → 图纸坐标（借 f 的平移、比例：f 把 3D 点映射到图纸）"""
    a, b = f((0, 0, 0)), proj((0, 0, 0), view)
    e = np.array(VIEWS[view][1], float)
    sc = (f(tuple(e))[0] - a[0]) / (proj(tuple(e), view)[0] - b[0])
    return a[0] + sc * (u - b[0]), a[1] + sc * (v - b[1])
