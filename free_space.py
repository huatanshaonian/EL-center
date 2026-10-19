"""
MIS-01 机内空间分析：每一层（底层 / 管座层 / 电脑层）从层板往上有多高是空的。
做法：整机装配里每个零件三角化后细分到 ≤1.5 mm，投到 2 mm 俯视网格上，记下每格里最低的障碍物高度；
      穿过层板的零件（立柱、屏、托架…）再用一片薄板截一刀补上实心截面。
每层出两张俯视图：
  上排"贴层板放"：从层板面往上到第一个障碍物有多高；
  下排"架高放"：把板架到这一格所有东西的上面，离上一层板还有多高（电源上方这类空间）。
输出 png/08_free_space.png，终端打印最大空矩形列表。范围只算框架内侧 X 20–300（两侧敞开、没有侧板）。
高度从层板上表面算起；PCB 用铜柱架高、板厚 1.6 要另外扣掉。
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import BoundaryNorm, ListedColormap
import render as R
import assembly as A
from parts import box

CELL = 2.0
# 层名, 层板面 Z, 顶 Z（上一层板底）, 俯视范围 (x0, x1, y0, y1)
LAYERS = [
    ("底层", 0.0, 90.0, (21, 299, -48, 220)),
    ("管座层", 92.0, 260.0, (21, 299, 0, 220)),
    ("电脑层", 262.0, 420.0, (21, 299, 0, 220)),
]
SKIP = ("RESERVE_", "base_plate", "deck_plate", "shelf_plate", "top_plate", "IV18_PSU", "NID100")
EXTRA = [("IEC_C14（预留，未建模）", box(33, 36, 60, 263, 184, 24))]    # 后面板 IEC 座的机内部分
THRESH = (20, 50, 100)                                         # 列空矩形用的高度门槛
MIN_SIDE = 30                                                          # 空矩形最短边

def height_map(items, z0, z1, ext):
    x0, x1, y0, y1 = ext
    nx, ny = int((x1 - x0) / CELL), int((y1 - y0) / CELL)
    h = np.full((ny, nx), z1 - z0)
    top = np.zeros((ny, nx))                       # 每格障碍物最高点（相对层板面）
    labels = []

    def mark(pts):
        p = pts[(pts[:, 2] > z0 + 0.05) & (pts[:, 2] < z1 - 0.05)]
        if not len(p):
            return False
        ix = ((p[:, 0] - x0) / CELL).astype(int); iy = ((p[:, 1] - y0) / CELL).astype(int)
        ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
        np.minimum.at(h, (iy[ok], ix[ok]), p[ok, 2] - z0)
        np.maximum.at(top, (iy[ok], ix[ok]), p[ok, 2] - z0)
        return ok.any()

    for name, shp in items:
        bb = shp.val().BoundingBox()
        if bb.zmax <= z0 + 0.05 or bb.zmin >= z1 - 0.05 or bb.xmax < x0 or bb.xmin > x1 or bb.ymax < y0 or bb.ymin > y1:
            continue
        v, t = R.tess(shp, 0.3)
        if not len(t):
            continue
        tri = v[t]
        tri = tri[(tri[:, :, 2].max(1) > z0) & (tri[:, :, 2].min(1) < z1)]
        hit = False
        if len(tri):
            tri = R.subdivide(tri, 1.5)
            hit |= mark(tri.reshape(-1, 3)) | mark(tri.mean(1))
        if bb.zmin < z0 + 0.5:                                         # 穿过层板：截一片补实心
            try:
                sl = shp.intersect(box(x1 - x0, y1 - y0, 0.4, x0, y0, z0 + 0.3))
                if sl.vals():
                    sv, st = R.tess(sl, 0.2)
                    if len(st):
                        s3 = R.subdivide(sv[st], 1.5)
                        hit |= mark(s3.reshape(-1, 3)) | mark(s3.mean(1))
            except Exception:
                pass
        if hit:
            labels.append((name, bb))
    return h, (z1 - z0) - top, labels

def max_rect(free):
    """二值网格里面积最大的全空矩形（直方图法），返回 (iy0, iy1, ix0, ix1) 半开区间"""
    ny, nx = free.shape
    hist = np.zeros(nx, int); best = (0, None)
    for r in range(ny):
        hist = np.where(free[r], hist + 1, 0)
        st = []
        for c in range(nx + 1):
            cur = hist[c] if c < nx else 0
            start = c
            while st and st[-1][1] >= cur:
                s0, hh = st.pop()
                if hh * (c - s0) > best[0]:
                    best = (hh * (c - s0), (r - hh + 1, r + 1, s0, c))
                start = s0
            st.append((start, cur))
    return best[1]

def rects(h, ext, thr, n=4):
    x0, _, y0, _ = ext
    free = h >= thr
    out = []
    for _ in range(n):
        r = max_rect(free)
        if r is None:
            break
        a, b, c, d = r
        w, l = (d - c) * CELL, (b - a) * CELL
        if min(w, l) < MIN_SIDE:
            break
        out.append((x0 + c * CELL, x0 + d * CELL, y0 + a * CELL, y0 + b * CELL, float(h[a:b, c:d].min())))
        free[a:b, c:d] = False
    return out

def main(fname="png/08_free_space.png"):
    items = [(n, s) for n, s, c, g in A.build() if not n.startswith(SKIP)] + EXTRA
    bounds = [0, 20, 50, 100, 200]
    cmap = ListedColormap(["#d9d9d9", "#fdd0a2", "#a1d99b", "#31a354"])
    norm = BoundaryNorm(bounds, cmap.N)
    fig, axs = plt.subplots(2, 3, figsize=(24, 15.5), dpi=90)
    F = R.FONT
    for col, (name, z0, z1, ext) in enumerate(LAYERS):
        h, above, labels = height_map(items, z0, z1, ext)
        x0, x1, y0, y1 = ext
        for row, (hm, kind) in enumerate(((h, "贴层板放"), (above, "架高放（在障碍物上方）"))):
            ax = axs[row, col]
            ax.imshow(hm, origin="lower", extent=(x0, x1, y0, y1), cmap=cmap, norm=norm, interpolation="nearest")
            print(f"\n== {name} · {kind}（层板面 Z={z0:g}，到 Z={z1:g}）==")
            seen = set()
            for thr in THRESH:
                for rx0, rx1, ry0, ry1, hmin in rects(hm, ext, thr, n=3):
                    key = (rx0, rx1, ry0, ry1)
                    if key in seen:
                        continue
                    seen.add(key)
                    base = "" if row == 0 else f"  板底可放到 Z≥{z1 - hmin:.0f}"
                    print(f"  ≥{thr:<4} X {rx0:4.0f}–{rx1:<4.0f} Y {ry0:4.0f}–{ry1:<4.0f}  {rx1-rx0:4.0f}×{ry1-ry0:<4.0f}  可用高 {hmin:4.0f}{base}")
                    c = {20: "#a50f15", 50: "#08519c", 100: "#000000"}[thr]
                    ax.add_patch(Rectangle((rx0, ry0), rx1 - rx0, ry1 - ry0, fill=False, ec=c, lw=1.6, ls=(0, (4, 2)) if thr == 20 else "-"))
                    ax.text(rx0 + 2, ry1 - 2 - 9 * len(seen) % 27, f"{rx1-rx0:.0f}×{ry1-ry0:.0f}×{hmin:.0f}", fontproperties=F, fontsize=9, va="top", color=c,
                            bbox=dict(fc="white", ec="none", alpha=0.6, pad=0.5))
            for n, bb in labels:                                        # 标主要障碍物
                if any(k2 in n for k2 in ("2020", "corner", "standoff", "clip", "Indicator", "Toggle", "Rect_lamp", "EC11", "Fader", "USB-A",
                                           "IN14_socket", "IN-14_", "chin", "base_strip", "slant", "Noval", "bracket", "cheek", "fan", "rear_panel")):
                    continue
                cx, cy = (max(bb.xmin, x0) + min(bb.xmax, x1)) / 2, (max(bb.ymin, y0) + min(bb.ymax, y1)) / 2
                ax.text(cx, cy, n.replace("_", " "), fontproperties=F, fontsize=8, ha="center", va="center", color="#333", alpha=0.85)
            ax.axhline(0, color="k", lw=0.6, ls=":"); ax.text(x1, 1, "框架前沿 Y=0 ", fontproperties=F, fontsize=8, va="bottom", ha="right")
            ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
            ax.set_xticks(range(20, 301, 40)); ax.set_yticks(range(int(np.ceil(y0 / 20) * 20), int(y1) + 1, 20))
            ax.grid(color="w", lw=0.3, alpha=0.6)
            ax.set_title(f"{name} · {kind}\n层板面 Z={z0:g}，到上一层板 Z={z1:g}（最多 {z1 - z0:g} 高）", fontproperties=F, fontsize=13)
            ax.set_xlabel("X（左→右）", fontproperties=F); ax.set_ylabel("Y（前→后）", fontproperties=F)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=axs, orientation="horizontal", fraction=0.025, pad=0.04, ticks=bounds)
    cb.set_label("可用高度（mm）。框 = 能放下的最大空矩形，标注 长×宽×可用高；红虚线 ≥20 高、蓝 ≥50、黑 ≥100", fontproperties=F, fontsize=13)
    fig.suptitle("MIS-01 机内可用空间（俯视，前面在下；只算框架内侧 X 20–300；还没画的自制板不计入；铜柱和板厚需另扣）",
                 fontproperties=F, fontsize=17)
    fig.savefig(fname, facecolor="white", bbox_inches="tight"); plt.close(fig)
    print("\nsaved", fname)


# ---------------------------------------------------------------- 立体示意：把主要空间画成半透明盒子放进机箱
# 字母, 说明, X0, X1, Y0, Y1, Z0, Z1（数值取自上面的分析结果，布局改了要跟着改）
SPACES_FLOOR = [
    ("A", "底层前条", 41, 299, 22, 80, 0, 88),
    ("B", "底层电源右边", 261, 299, 80, 184, 0, 90),
    ("D", "斜面下楔形", 53, 245, -42, 0, 0, 23),
    ("E", "管座层后半区", 21, 299, 56, 220, 92, 260),
    ("F", "电脑层整层（Orange Pi、FPGA 未安装）", 21, 299, 30, 200, 262, 420),
]
SPACES_RAISED = [
    ("C", "电源上方（板底 Z≥40）", 41, 245, 6, 220, 40, 90),
    ("C2", "电源右上方（板底 Z≥40）", 245, 299, 34, 184, 40, 90),
]
SPACE_COL = {0: (0.95, 0.45, 0.10, 0.35), 92: (0.15, 0.55, 0.95, 0.30), 262: (0.20, 0.75, 0.30, 0.30)}

def figure_3d():
    ctx = [it for it in A.build() if it[3] not in ("front", "rear", "top", "covers", "keyboard")]
    ctx = [(n, s, (0.55, 0.55, 0.57, 1) if g == "frame" else (0.80, 0.80, 0.80, 1), g) for n, s, c, g in ctx]
    for spaces, fname, kind, az, side in ((SPACES_FLOOR, "png/09a_free_space_3d_floor.png", "贴层板放", 35, "前方俯视"),
                                          (SPACES_RAISED, "png/09b_free_space_3d_raised.png", "架高放（在已有东西上方）", 150, "后方俯视")):
        items = [it for it in ctx if az > 90 or it[3] not in ("core", "mech")]      # 前方视角隐藏 EL 屏和托架，免得挡住中间
        labels = []
        print(f"\n{kind}：")
        for k, desc, x0, x1, y0, y1, z0, z1 in spaces:
            layer = 0 if z0 < 92 else (92 if z0 < 262 else 262)
            items.append((k, box(x1 - x0, y1 - y0, z1 - z0, x0, y0, z0), SPACE_COL[layer], "space"))
            txt = f"{k} {desc}\n{x1-x0}×{y1-y0}×{z1-z0}"
            labels.append((((x0 + x1) / 2, (y0 + y1) / 2, z1), txt))
            print(f"  {k} {desc}: {x1-x0}×{y1-y0}×{z1-z0}  (X {x0}–{x1}, Y {y0}–{y1}, Z {z0}–{z1})")
        R.render(items, fname, az=az, el=28, size=(11, 12), labels=labels,
                 title=f"MIS-01 机内可用空间 · {kind}\n橙=底层  蓝=管座层  绿=电脑层；标注 长(X)×宽(Y)×高(Z)，单位 mm；{side}，前面板/后面板/顶板已隐藏")
        print("saved", fname)

if __name__ == "__main__":
    import sys
    if "3d" in sys.argv[1:]:
        figure_3d()
    else:
        main()
