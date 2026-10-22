"""层板手钻孔位图 → png/27_drill_map.png（层板已做好，2026-10-23 起装配前自己钻的孔）。
数据全部来自 frame_spec.DRILL；每块板画出已有的孔阵、固定孔、走线孔，红色为要钻的新孔。
坐标一律从板的左边、前边量（俯视，前边朝下）；表里另给“离最近孔阵孔”的偏移，画线时从那个孔量最准。
运行：.venv/Scripts/python.exe fig_drill_map.py"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
import render as R
import frame_spec as S

F = R.FONT
ORIGIN = {"P1": (2, 2), "P2": (2, 30), "P3": (0, 0), "P4": (0, 0)}   # 板左前角的全局坐标
PLATE = {p[0]: p for p in S.PLATES}


def nearest_grid(code, x, y):
    """离 (x, y)（板自身坐标）最近的孔阵孔：返回 (dx, dy, 孔阵孔) 或 None"""
    holes = S.grid_holes(code)
    if not holes:
        return None
    g = min(holes, key=lambda h: math.hypot(x - h[0], y - h[1]))
    return x - g[0], y - g[1], g


def plate_ax(ax, code):
    _, name, (L, Wd, _), _, _, mount, md, _ = PLATE[code]
    ox, oy = ORIGIN[code]
    ax.add_patch(Rectangle((0, 0), L, Wd, fill=False, lw=1.2))
    for x, y in S.grid_holes(code):
        ax.add_patch(Circle((x, y), S.GRID_D / 2, fill=False, lw=0.4, color="0.6"))
    for x, y in mount:
        ax.add_patch(Circle((x, y), md / 2, fill=False, lw=0.8, color="0.3"))
    for x, y, w, h in S.slots(code):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle=f"round,pad=0,rounding_size={min(w, h) / 2}",
                                    fill=False, lw=0.6, color="0.5"))
    if code == "P3":
        for x, y in S.VENTS:
            ax.add_patch(Circle((x, y), 4, fill=False, lw=0.4, color="0.6"))
    rows = []
    for k, (gx, gy, d, part, note) in enumerate(S.DRILL.get(code, []), 1):
        x, y = gx - ox, gy - oy
        if d:
            ax.add_patch(Circle((x, y), max(d / 2, 2.2), color="red", lw=1.4, fill=False))
        else:
            ax.add_patch(Rectangle((x - 4, y - 4), 8, 8, color="darkorange", lw=1.2, fill=False, ls="--"))
        ax.annotate(f"{code[1]}-{k}", (x, y), (x + 4, y + 4), fontsize=7, color="red", fontproperties=F)
        ng = nearest_grid(code, x, y)
        ref = f"孔阵孔 ({ng[2][0]:g},{ng[2][1]:g}) {ng[0]:+.1f} / {ng[1]:+.1f}" if ng and math.hypot(ng[0], ng[1]) < 30 else "量板边"
        dia = f"Ø{d:g}" if d else "按实物"
        rows.append(f"{code[1]}-{k:<2} {part:<10} 左 {x:6.1f}  前 {y:6.1f}  {dia:<5} {ref}  {note}")
    ax.set_xlim(-8, L + 8); ax.set_ylim(-8, Wd + 8); ax.set_aspect("equal")
    ax.set_title(f"{code} {name}（{L:g}×{Wd:g}，前边在下）", fontproperties=F, fontsize=11)
    ax.tick_params(labelsize=7)
    return rows


def main(fname="png/27_drill_map.png"):
    fig = plt.figure(figsize=(16, 19))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 0.75])
    rows = []
    for i, code in enumerate(("P1", "P2", "P3", "P4")):
        rows += [""] if rows else []
        rows += plate_ax(fig.add_subplot(gs[i // 2, i % 2]), code)
    tx = fig.add_subplot(gs[2, :]); tx.axis("off")
    head = ["红圈 = 要钻的孔（M3 用 Ø3.4，M2.5 用 Ø2.8）；橙色虚线框 = 按实物配钻（零件放到位，从它的安装孔里画线）。",
            "坐标从板左边、前边量（mm）；偏移 = 新孔相对最近孔阵孔的 右(+)/左(−)、后(+)/前(−)，画线时从孔阵孔量。",
            "按实物配钻的孔离孔阵孔中心至少 4 mm，不够就把零件挪 1–2 mm，别让两个孔钻穿连成缝。", ""]
    tx.text(0, 1, "\n".join(head + rows), va="top", fontproperties=F, fontsize=9.5, family="monospace")
    fig.suptitle("MIS-01 层板手钻孔位（2026-10-23）", fontproperties=F, fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(fname, facecolor="white", dpi=110); plt.close(fig)
    print("saved", fname)
    print("\n".join(rows))


if __name__ == "__main__":
    main()
