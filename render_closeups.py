"""局部说明图 → png/16–19：6E2 开口（面板拉开示意、正视）、PCB-3 倒挂在甲板下（等轴、正视）
PCB-3 位置见 assembly.py lower()（用 mis-01-56 导出的整板 STEP）。
运行：.venv/Scripts/python.exe render_closeups.py（约 8 分钟）"""
import render as R
import assembly as A

def inbox(sh, b):
    bb = sh.val().BoundingBox()
    return bb.xmin < b[1] and bb.xmax > b[0] and bb.ymin < b[3] and bb.ymax > b[2] and bb.zmin < b[5] and bb.zmax > b[4]


def eye_window(items):
    box = (170, 320, -60, 60, 80, 200)
    sel = [(n, sh.translate((0, -50, 0)) if n == "front_panel_2mm" else sh, col, g)
           for n, sh, col, g in items if inbox(sh, box)]
    R.render(sel, "png/16_6e2_window_exploded.png", az=35, el=15, title="6E2 开口（前面板往前拉开 50 mm 示意）", size=(11, 9),
             labels=[((250, -52, 180), "前面板：6E2 窗和盖革窗\n中间留横条隔开"), ((290, 0, 120), "透明亚克力 2 mm\n贴在面板背面"),
                     ((285, 27, 176), "6E2 ×2"), ((300, 8, 100), "盖革管 J305")])
    sel = [x for x in items if inbox(x[1], box)]
    R.render(sel, "png/17_6e2_window_front.png", az=0, el=0, title="6E2 开口正视（装好后）", size=(9, 8))


def pcb3(items):
    box = (0, 320, 20, 220, -5, 100)
    keep = ("MeanWell", "Mains_hood", "deck_plate", "PCB-3", "standoff_M3x10_PCB3", "2020_post", "2020_Yrail", "base_plate", "Speaker")
    sel = [(n, sh, (col[0], col[1], col[2], 0.25) if n.startswith("deck_plate") else col, g)
           for n, sh, col, g in items if n.startswith(keep) and inbox(sh, box)]
    R.render(sel, "png/18_pcb3_under_deck_iso.png", az=30, el=18, title="PCB-3 倒挂在甲板下（甲板半透明）", size=(12, 8))
    R.render([x for x in sel if not x[0].startswith("2020_post")], "png/19_pcb3_under_deck_front.png", az=0, el=0,
             title="正视（去掉前面板）：甲板底 z 90 / PCB-3 元件最低 z 51 / LRS 顶 z 30", size=(12, 6))


if __name__ == "__main__":
    items = A.build()
    eye_window(items)
    pcb3(items)
