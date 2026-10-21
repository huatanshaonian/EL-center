"""生成 png/ 下的预览图：零件一览 + 整机前/后等轴、正视、侧视"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import render as R
import assembly as A
from build_parts import PARTS

GREY = (0.62, 0.66, 0.70, 1)

def parts_sheet(fname, cols=6):
    rows = -(-len(PARTS) // cols)
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 3.3, rows * 3.5), dpi=100)
    for ax in axs.ravel():
        ax.axis("off")
    for ax, (name, fn) in zip(axs.ravel(), PARTS.items()):
        s = fn()
        bb = s.val().BoundingBox()
        R.draw(ax, [(name, s, GREY, "")], az=30, el=25, maxlen=max(bb.xlen, bb.ylen, bb.zlen) / 6)
        ax.set_title(f"{name}\n{bb.xlen:.1f}×{bb.ylen:.1f}×{bb.zlen:.1f}", fontproperties=R.FONT, fontsize=9)
    fig.suptitle("MIS-01 零件模型一览（包围盒尺寸 mm）", fontproperties=R.FONT, fontsize=14)
    fig.tight_layout(); fig.savefig(fname, facecolor="white"); plt.close(fig)

def views(outdir):
    """全高侧板 / 背板（分组 sides、rear）是可选盖板：01 / 05 不画侧板，04 / 07 全部装上"""
    items = A.build()
    no_front = [it for it in items if it[3] not in ("front", "covers", "keyboard", "sides")]
    no_rear = [it for it in items if it[3] not in ("rear", "covers", "top", "sides")]
    no_sides = [it for it in items if it[3] != "sides"]
    R.render(no_sides, f"{outdir}/01_front_iso.png", az=30, el=20, title="前等轴（不装全高侧板 / 背板）")
    R.render(no_front, f"{outdir}/02_front_iso_no_panel.png", az=30, el=20, title="前等轴（去前壳 / 下巴 / 侧板）")
    R.render(no_rear, f"{outdir}/03_rear_iso_no_panel.png", az=150, el=25, title="后等轴（去背板 / 顶板 / 侧板）")
    R.render(items, f"{outdir}/04_rear_iso.png", az=150, el=20, title="后等轴（全部装上，含可选侧板 / 背板）")
    R.render(no_sides, f"{outdir}/05_front_ortho.png", az=0, el=0, title="正视")
    R.render(no_rear, f"{outdir}/06_side_view.png", az=90, el=0, title="右侧视（去背板 / 顶板 / 侧板）", size=(8, 11))
    R.render(items, f"{outdir}/07_front_iso_full.png", az=30, el=20, title="前等轴（全部装上，含可选侧板 / 背板）")

if __name__ == "__main__":
    os.makedirs("png", exist_ok=True)
    parts_sheet("png/00_parts_sheet.png")
    views("png")
