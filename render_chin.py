"""前壳 + 下巴托 + 后仰键盘座 → png/26_chin_iso.png、png/26_chin_side.png、png/26_chin_exploded.png
前壳 = 前面板 + 斜面一块铝板；下巴托 = 底板 + 两侧板一块铝板；键盘座两端锁侧板、顶部舌片从斜面下沿锁沉头。
只取下半截（z < 200）和机架下部，省得 EL 屏挡住。
运行：.venv/Scripts/python.exe -u render_chin.py"""
import render as R
import assembly as A
import assembly_panel as AP

KEEP = ("front_shell", "chin_tray", "Keyboard_dock", "X1_", "rubber_foot", "2020_post", "2020_Xrail_L280_FB", "2020_Yrail_L180_bot",
        "2020_Yrail_L180_deck", "base_plate", "deck_plate", "SLANT_board", "RPi_Pico", "USB", "Rotary", "EC11", "Fader", "Toggle",
        "Indicator", "Rect_lamp", "Speaker", "corner_bracket")


def pick(items, zmax=200):
    out = []
    for n, sh, col, g in items:
        if not n.startswith(KEEP):
            continue
        bb = sh.val().BoundingBox()
        if bb.zmin > zmax:
            continue
        if n.startswith("2020_post"):
            sh = sh.intersect(A.P.box(400, 400, zmax, -40, -40, -10))
        if n.startswith(("deck_plate", "base_plate")):
            col = (col[0], col[1], col[2], 0.35)
        out.append((n, sh, col, g))
    return out


def main():
    items = pick(A.build())
    lab = [((AP.SIDE_X[0], 20, 45), "下巴托侧板（机架外侧）\nM4 锁立柱 ×2、Y 梁 ×2"), ((160, -30, 60), "前壳：前面板 + 斜面一块铝板"),
           ((40, -52, 4), "键盘座（后仰，两端锁侧板）"), ((160, -150, -6), "X1 键盘"), ((300, -20, -2), "下巴托底板")]
    R.render(items, "png/26_chin_iso.png", az=-35, el=18, size=(13, 9), labels=lab,
             title="前壳 + 下巴托 + 后仰键盘座（左前下方看）")
    R.render([x for x in items if not x[0].startswith("2020_post")], "png/26_chin_side.png", az=-90, el=0, size=(12, 8),
             title="左侧视：侧板外形、M4 孔（锁型材）、M3 孔（斜面翻边、键盘座两端）")
    ofs = {"front_shell": (0, -60, 40), "Keyboard_dock": (0, -110, -10), "X1_": (0, -170, -30)}
    ex = []
    for n, sh, col, g in items:
        d = next((v for k, v in ofs.items() if n.startswith(k)), None)
        if d is None and n.startswith(("SLANT_board", "RPi_Pico", "USB", "Rotary", "EC11", "Fader", "Toggle", "Indicator", "Rect_lamp")):
            d = ofs["front_shell"]
        ex.append((n, sh.translate(d) if d else sh, col, g))
    R.render(ex, "png/26_chin_exploded.png", az=-35, el=20, size=(13, 10),
             labels=[((-2, -60, 140), "前壳（前面板 + 斜面）\n斜面两侧翻边 M3 锁侧板"), ((40, -165, 0), "键盘座 + 背盖"),
                     ((AP.SIDE_X[0], 30, 60), "下巴托（底板 + 两侧板）\n底板后边上翻 M4 ×3 锁前下横梁")],
             title="拆开看：前壳 / 键盘座 / 下巴托")


if __name__ == "__main__":
    main()
