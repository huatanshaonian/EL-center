"""整机爆炸图（前等轴 + 后等轴）→ png/22_exploded_front.png、png/22_exploded_rear.png
按 assembly.build() 的分组整体平移：框架和甲板层不动，前面板/斜面往前拉，后面板往后拉，
电脑层和顶板往上抬，下舱（电源、配电板、底板）往下放。只改显示位置，不改装配坐标。
运行：.venv/Scripts/python.exe -u fig_exploded.py [front] [rear]（不带参数两张都出）"""
import os
import render as R
import assembly as A
from assembly_base import W, D, Z_DECK, Z_SHELF, H

# 分组 → 平移量 (dx, dy, dz)
GROUP_OFS = {
    "front": (0, -420, -60), "ui": (0, -420, -60), "keyboard": (0, -620, -120),
    "core": (0, -200, 260), "mech": (0, -200, 260),      # EL 屏和托架：往前上方抬，让开甲板层
    "rear": (0, 230, 0),
    "computer": (0, 0, 150), "top": (0, 0, 320),
    "power": (0, 0, -170), "covers": (0, 0, -170),
}
# 层板按名字单独处理（同属 plates 组）
NAME_OFS = {
    "shelf_plate_bakelite": (0, 0, 150),
    "base_plate_bakelite": (0, 0, -170),
}

LABELS = [
    ((W + 10, D / 2, H + 330), "顶板"),
    ((W + 10, D / 2, Z_SHELF + 170), "电脑层：Orange Pi 4、Dock、HDMI 小板"),
    ((W + 10, 60, Z_DECK + 40), "甲板层：IN-14、IV-18、6E2、盖革、ESP 底板"),
    ((W + 10, D / 2, -150), "下舱：LRS-200、PCB-3、底板"),
    ((-60, -430, 300), "前面板 + 斜面 + 表头"),
    ((-60, -210, 560), "EL 屏 + 托架"),
    ((W / 2, -680, -100), "X1 键盘"),
    ((W / 2, D + 240, 360), "后面板"),
]


def exploded(items):
    out = []
    for name, shp, col, grp in items:
        dx, dy, dz = NAME_OFS.get(name, GROUP_OFS.get(grp, (0, 0, 0)))
        out.append((name, shp.translate((dx, dy, dz)) if (dx or dy or dz) else shp, col, grp))
    return out


# 后等轴看过去 +X 在左，标签放在各组靠 x 0 的一侧
LABELS_REAR = [
    ((0, D / 2, H + 330), "顶板"),
    ((0, D / 2, Z_SHELF + 170), "电脑层：Orange Pi 4、Dock、HDMI 小板"),
    ((0, 60, Z_DECK + 40), "甲板层：IN-14、IV-18、6E2、盖革、ESP 底板"),
    ((0, D / 2, -150), "下舱：LRS-200、PCB-3、底板"),
    ((W, -430, 380), "前面板 + 斜面 + 表头"),
    ((W, -210, 680), "EL 屏 + 托架"),
    ((W / 2, -680, -100), "X1 键盘"),
    ((W / 2, D + 240, 440), "后面板"),
]


def main(which=("front", "rear")):
    os.makedirs("png", exist_ok=True)
    items = exploded(A.build())
    print("parts", len(items))
    if "front" in which:
        R.render(items, "png/22_exploded_front.png", az=30, el=22, title="MIS-01 爆炸图（前等轴）",
                 size=(14, 16), labels=LABELS)
        print("saved png/22_exploded_front.png")
    if "rear" in which:
        R.render(items, "png/22_exploded_rear.png", az=150, el=22, title="MIS-01 爆炸图（后等轴）",
                 size=(14, 16), labels=LABELS_REAR)
        print("saved png/22_exploded_rear.png")


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or ("front", "rear"))
