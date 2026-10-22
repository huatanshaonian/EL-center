"""键盘座 CNC 询价图：STEP + 同名 2D 图纸 PDF → 外壳加工/键盘座_CNC询价/
嘉立创 CNC 询价要求 3D（STEP，必须）+ 2D（PDF），同一零件文件名一致。
CNC 版 7 个 M3 孔为 Ø2.5 攻丝底孔（打印版是 Ø4 压热熔铜螺母，见 parts_dock.INSERT_R）。
视图由 3D 模型隐藏线投影（OCC HLR）得到，尺寸从 parts_dock.SPEC 算，和模型同源。
第 1 页 A3 1:1 全长视图 + 4:1 端视图；第 2 页 A3 2:1 右半详图（零件左右对称）。
运行：.venv/Scripts/python.exe fig_dock_drawing.py"""
import datetime
import os
import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
import render as R
import parts_dock as PD

F = R.FONT
OUT = os.path.join("外壳加工", "键盘座_CNC询价")
CNC_HOLE_R = 1.25                                   # Ø2.5 攻 M3
S = PD.SPEC
L, D, H = S["L"], S["D"], S["H"]
TW, TH, TT = S["tongue"]
GL, GW, GD = S["groove"]
GY = S["groove_y"] + GW / 2                          # 槽宽中线 Y 4.4
Z_FL = GD + S["floor"]                               # 槽底板上表面 2.5
inner = PD._inner

# 视图：名称 → (视线方向 eye（从零件指向看图人）, 图纸 x 轴方向)
VIEWS = {"front": ((0, -1, 0), (1, 0, 0)), "back": ((0, 1, 0), (-1, 0, 0)), "bottom": ((0, 0, -1), (1, 0, 0)),
         "top": ((0, 0, 1), (1, 0, 0)), "end": ((1, 0, 0), (0, 1, 0))}


def proj(p, view):
    eye, xd = (np.array(v, float) for v in VIEWS[view])
    yd = np.cross(eye, xd)
    p = np.array(p, float)
    return float(p @ xd), float(p @ yd)


def hlr(shape, view):
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


class Sheet:
    """一页 A3 横向，坐标单位 = 图纸 mm"""
    def __init__(self, pdf, title, page, total=2):
        self.pdf, self.title, self.page, self.total = pdf, title, page, total
        self.fig = plt.figure(figsize=(420 / 25.4, 297 / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1]); self.ax.set_xlim(0, 420); self.ax.set_ylim(0, 297); self.ax.axis("off")
        self.ax.add_patch(plt.Rectangle((5, 5), 410, 287, fill=False, lw=0.8))

    def text(self, x, y, s, size=7, **kw):
        self.ax.text(x, y, s, fontproperties=F, fontsize=size, **kw)

    def view(self, shape, view, ox, oy, sc, label, clip_x=None, hidden=True, label_below=True):
        vis, hid = hlr(shape, view)
        T = lambda a: np.column_stack((ox + sc * a[:, 0], oy + sc * a[:, 1]))
        keep = (lambda a: True) if clip_x is None else (lambda a: a[:, 0].max() >= clip_x[0] - 1e-6 and a[:, 0].min() <= clip_x[1] + 1e-6)
        clipper = (lambda a: a) if clip_x is None else (lambda a: np.column_stack((np.clip(a[:, 0], *clip_x), a[:, 1])))
        if hidden:
            for a in hid:
                if keep(a):
                    b = T(clipper(a)); self.ax.plot(b[:, 0], b[:, 1], color="0.6", lw=0.25, ls=(0, (2, 1.5)))
        for a in vis:
            if keep(a):
                b = T(clipper(a)); self.ax.plot(b[:, 0], b[:, 1], color="k", lw=0.5)
        lx = ox + sc * (clip_x[0] if clip_x else -L / 2) + 3
        ly = oy + sc * (-D if view == "bottom" else 0) - 7 if label_below else oy + sc * self.ymax(view) + 3
        self.text(lx, ly, label, size=8, weight="bold")
        return lambda p: (ox + sc * proj(p, view)[0], oy + sc * proj(p, view)[1])

    @staticmethod
    def ymax(view):
        return {"front": H + TH, "back": H + TH, "bottom": 0, "top": D, "end": H + TH}[view]

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

    def ordinate(self, pts, y0, ylab, txts, size=6, up=True):
        """坐标标注：每个点竖线引到 ylab，文字竖排；y0 处画 0 基准"""
        for (x, y), t in zip(pts, txts):
            self.ax.plot([x, x], [y, ylab], color="0.35", lw=0.2)
            self.text(x, ylab + (0.5 if up else -0.5), t, size=size, rotation=90, ha="center", va="bottom" if up else "top")

    def leader(self, p, q, txt, size=6.5):
        self.ax.annotate(txt, p, q, fontproperties=F, fontsize=size, arrowprops=dict(arrowstyle="-|>", lw=0.35, mutation_scale=5),
                         va="center")

    def title_block(self, scale):
        x0, y0 = 275, 8
        self.ax.add_patch(plt.Rectangle((x0, y0), 137, 40, fill=False, lw=0.6))
        rows = [("零件", self.title), ("材料", "黑色 POM（均聚甲醛）"), ("数量", "1"), ("比例", scale),
                ("单位 / 未注公差", "mm / ±0.1"), ("日期 / 页", f"{datetime.date.today()} / 第 {self.page} 页 共 {self.total} 页")]
        for i, (k, v) in enumerate(rows):
            y = y0 + 40 - 6.4 * (i + 1) + 1.6
            self.text(x0 + 2, y, k, size=7); self.text(x0 + 32, y, v, size=7.5)
            if i:
                self.ax.plot([x0, x0 + 137], [y + 4.8, y + 4.8], color="k", lw=0.3)
        self.ax.plot([x0 + 30, x0 + 30], [y0, y0 + 40], color="k", lw=0.3)

    def save(self):
        self.pdf.savefig(self.fig); plt.close(self.fig)


NOTES = [
    "技术要求",
    "1. 材料黑色 POM，整件机加工；以 3D STEP 为准，本图标注主要尺寸。零件以长度中线左右对称。",
    "2. 7 处 M3 螺纹孔（底孔 Ø2.5）：顶部 3 个舌片各 1 处，贯通（舌片厚 4）；两端面各 2 处，孔深 7、螺纹深 6。",
    "3. 底面槽内 4 处 Ø1.3 为 M1.6 自攻底孔，从背面凸台贯通到槽面；4 处 Ø1.65 通孔。",
    "4. 关键配合：槽宽 3.8、磁铁开孔宽 2.2、触点开孔 17.1×2 取 0 / +0.1；其余未注 ±0.1。",
    "5. 最薄处：槽底板 0.8 厚（槽深 1.7 之上），横向加强筋 1.2，正面磁铁槽后壁 1.0，注意装夹变形。",
    "6. 背面敞开（内部空腔、加强筋、自攻凸台见背面视图）；顶面后棱倒角 1.2×45°。",
    "7. 去毛刺，锐边倒钝 0.2；表面为原色机加工面（可选细喷砂）。",
]


def page1(pdf, shp):
    s = Sheet(pdf, "MIS-01 键盘座", 1)
    ox = 50 + L / 2
    f = s.view(shp, "front", ox, 248, 1, "正视图（屏幕面，从前往后看）")
    s.dim_h(f((-L / 2, 0, 0)), f((L / 2, 0, 0)), 228, f"{L:g}")
    s.dim_v(f((L / 2, 0, 0)), f((L / 2, 0, H)), 375, f"{H:g}")
    s.dim_v(f((L / 2, 0, 0)), f((120 + TW / 2, 0, H + TH)), 384, f"{H + TH:g}")
    tx = list(S["tongue_x"])
    s.ordinate([f((x, 0, H + TH)) for x in tx], 0, 248 + H + TH + 2, [f"舌片中心 {x:+g}" for x in tx])
    s.leader(f((tx[2] + 2, 0, H + PD.SCREW_U)), (f((tx[2], 0, 0))[0] + 22, 248 + H + TH + 8),
             f"舌片宽 {TW:g}、高出顶面 {TH:g}；M3 贯通，孔心高 {H + PD.SCREW_U:g}")

    b = s.view(shp, "bottom", ox, 200, 1, "底视图（槽面，图上方 = 屏幕面）")
    s.dim_h(b((-GL / 2, GY, 0)), b((GL / 2, GY, 0)), 200 + 11, f"槽长 {GL:g}（两端半圆）")
    s.dim_v(b((L / 2, 0, 0)), b((L / 2, D, 0)), 375, f"{D:g}")
    mx = inner(98.5, 51.0)
    s.dim_h(b((mx - 25.5, GY, 0)), b((mx + 25.5, GY, 0)), 200 + 4, "磁铁开孔 51")
    s.dim_h(b((-mx + 25.5, GY, 0)), b((mx - 25.5, GY, 0)), 200 + 4, "两开孔内距 98.5")

    k = s.view(shp, "back", ox, 140, 1, "背视图（背面敞开，从后往前看；左右与正视图相反）")
    s.dim_h(k((-L / 2 + S["end_wall"], D, 0)), k((-L / 2, D, 0)), 140 - 6, f"端块 {S['end_wall']:g}")
    ribs = (40.2, 110.0, 120.0, 130.0, 140.0)
    s.ordinate([k((x, D, H)) for x in ribs], 0, 140 + H + TH + 2, [f"筋 {x:g}" for x in ribs], size=5.5)
    s.text(k((40, D, H))[0], 140 - 7, f"加强筋厚 {S['rib_t']:g}，左右对称（X = ±40.2、±110、±120、±130、±140）", size=6.5)


    e = s.view(shp, "end", 30, 16, 4, "右端视图 4:1（图右 = 背面）", label_below=False)
    s.dim_h(e((L / 2, 0, 0)), e((L / 2, D, 0)), 11, f"{D:g}")
    s.dim_h(e((L / 2, S["wall"], H + TH)), e((L / 2, S["wall"] + TT, H + TH)), 16 + 4 * (H + TH) + 2, f"舌片厚 {TT:g}，离屏幕面 {S['wall']:g}")
    s.dim_v(e((L / 2, 0, 0)), e((L / 2, 0, H)), 22, f"{H:g}")
    for z in S["end_holes_z"]:
        s.leader(e((L / 2, S["end_hole_y"], z)), (e((L / 2, D, 0))[0] + 8, e((0, 0, z))[1]), f"M3 深 6（底孔 Ø2.5 深 7），高 {z:g}")
    s.leader(e((L / 2, S["end_hole_y"], S["end_holes_z"][1])), (e((L / 2, D, 0))[0] + 8, e((0, 0, 14.5))[1]),
             f"两孔离屏幕面 {S['end_hole_y']:g}")
    s.leader(e((L / 2, GY, GD / 2)), (e((L / 2, D, 0))[0] + 8, e((0, 0, 1.5))[1]), f"槽 {GW:g} 宽 × {GD:g} 深，离屏幕面 {S['groove_y']:g}")
    for i, n in enumerate(NOTES):
        s.text(150, 112 - 6 * i, n, size=8 if i == 0 else 7)
    s.title_block("1:1（端视图 4:1）")
    s.save()


def page2(pdf, shp):
    s = Sheet(pdf, "MIS-01 键盘座（右半详图）", 2)
    sc, ox, clip = 2, 45, (0, L / 2)
    f = s.view(shp, "front", ox, 222, sc, "正视图右半 2:1（X = 0 为长度中线）", clip_x=clip)
    pk = [(inner(31.0, 10.9), 10.9), (inner(182.7, 34.5), 34.5)]
    pz0 = 12.35 - 5.5
    pts, txt = [], []
    for cx, ln in pk:
        pts += [f((cx - ln / 2, 0, 12.35)), f((cx + ln / 2, 0, 12.35))]
        txt += [f"{cx - ln / 2:.2f}", f"{cx + ln / 2:.2f}"]
    pts += [f((x, 0, H + TH)) for x in (45 - TW / 2, 45 + TW / 2, 120 - TW / 2, 120 + TW / 2)]
    txt += [f"{x:g}" for x in (45 - TW / 2, 45 + TW / 2, 120 - TW / 2, 120 + TW / 2)]
    s.ordinate(pts, 0, 222 + sc * (H + TH) + 3, txt)
    s.dim_v(f((inner(182.7, 34.5) + 17.25, 0, pz0)), f((inner(182.7, 34.5) + 17.25, 0, 12.35)), f((140, 0, 0))[0], "磁铁槽高 5.5（深 3）")
    s.dim_v(f((L / 2, 0, 0)), f((L / 2, 0, pz0)), f((L / 2, 0, 0))[0] + 8, f"{pz0:g}")
    s.text(f((60, 0, 0))[0], 222 - 14, "正面 4 处磁铁槽（左右各 2）从屏幕面铣入，深 3；槽处墙内侧加厚到 4，下沿 45° 斜面（见背视图）", size=6.5)

    b = s.view(shp, "bottom", ox, 150, sc, "底视图右半 2:1（槽面；图上方 = 屏幕面）", clip_x=clip)
    feats = [("触点开孔端", 17.1 / 2), ("Ø1.65", inner(45, 1.65)), ("限位孔", 51.8 / 2), ("限位孔", 63.2 / 2),
             ("Ø1.65", inner(65.9, 1.65)), ("Ø1.3", inner(93.2, 1.55)), ("磁铁孔", inner(98.5, 51) - 25.5),
             ("横筋", inner(134.2, 0.8)), ("横筋", inner(161.0, 0.8)), ("磁铁孔", inner(98.5, 51) + 25.5),
             ("Ø1.3", inner(203.8, 1.55)), ("槽端", GL / 2)]
    s.ordinate([b((x, GY, 0)) for _, x in feats], 0, 150 + 8, [f"{n} {x:.2f}" for n, x in feats], size=5.5)
    s.dim_v(b((L / 2, S["groove_y"], 0)), b((L / 2, S["groove_y"] + GW, 0)), b((L / 2, 0, 0))[0] + 6, f"槽宽 {GW:g}")
    s.dim_v(b((L / 2, 0, 0)), b((L / 2, S["groove_y"], 0)), b((L / 2, 0, 0))[0] + 18, f"{S['groove_y']:g}")
    s.text(ox + 3, 150 - sc * D - 14, "槽内各孔中心都在槽宽中线（离屏幕面 4.4）上，Ø1.3 自攻底孔偏后 0.2（离屏幕面 4.6）。"
           "触点开孔 17.1×2 长圆；限位孔 5.7×3.33 圆角 R1；磁铁开孔 51×2.2，孔内 2 道 0.8 宽横筋高出槽底板 1.2。", size=6.5)

    k = s.view(shp, "back", ox + sc * L / 2, 62, sc, "背视图右半 2:1（从后往前看，图左 = 零件右端）", clip_x=(-L / 2, 0))
    s.dim_v(k((L / 2, D, 0)), k((L / 2, D, Z_FL)), k((L / 2, D, 0))[0] - 6, f"槽底板顶 {Z_FL:g}")
    s.dim_v(k((L / 2, D, H - S["top_t"])), k((L / 2, D, H)), k((L / 2, D, 0))[0] - 6, f"顶板 {S['top_t']:g}")
    s.leader(k((inner(93.2, 1.55), D, Z_FL + 1.55)), (k((inner(93.2, 1.55), D, 0))[0] + 15, 62 + sc * H + 6),
             "自攻凸台 Ø3 高 1.55，底孔 Ø1.3 贯通")
    s.title_block("2:1")
    s.save()


def cover_pdf(path, shp):
    with PdfPages(path) as pdf:
        s = Sheet(pdf, "MIS-01 键盘座背盖", 1, total=1)
        f = s.view(shp, "back", 50 + L / 2, 180, 1, "背盖（从后往前看）")
        cl = L - 2 * S["end_wall"]
        zb, zt = GD + S["floor"] - 1, H - S["top_t"] + 1
        s.dim_h(f((cl / 2, D + S["cover_t"], zb)), f((-cl / 2, D + S["cover_t"], zb)), 170, f"{cl:g}")
        s.dim_v(f((-cl / 2, D, zb)), f((-cl / 2, D, zt)), f((-cl / 2, D, 0))[0] + 6, f"{zt - zb:g}")
        for i, n in enumerate(["技术要求", f"1. 黑色 POM 平板，厚 {S['cover_t']:g}，外形 {cl:g} × {zt - zb:g}。",
                               "2. 4 角 M2 自攻螺丝孔和排线出线槽位置待定（询价可先按无孔平板报价）。", "3. 去毛刺，锐边倒钝。"]):
            s.text(60, 120 - 7 * i, n, size=8 if i == 0 else 7.5)
        s.title_block("1:1")
        s.save()


def main():
    os.makedirs(OUT, exist_ok=True)
    shp = PD.keyboard_dock(hole_r=CNC_HOLE_R)
    cq.exporters.export(shp, os.path.join(OUT, "键盘座_keyboard_dock.step"))
    with PdfPages(os.path.join(OUT, "键盘座_keyboard_dock.pdf")) as pdf:
        page1(pdf, shp)
        page2(pdf, shp)
    cov = PD.keyboard_dock_cover()
    cq.exporters.export(cov, os.path.join(OUT, "键盘座背盖_dock_cover.step"))
    cover_pdf(os.path.join(OUT, "键盘座背盖_dock_cover.pdf"), cov)
    print("saved", OUT)


if __name__ == "__main__":
    main()
