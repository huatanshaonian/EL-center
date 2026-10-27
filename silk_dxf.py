"""给嘉立创钣金的前壳丝印 2D 图（DXF，1:1，单位 mm）：A 竖直前面板 + B 斜面画在一张图里，带外形、开孔、定位尺寸、颜色说明。
嘉立创要求：丝印传 DWG / DXF；1:1 或标尺寸；注明颜色（不注默认黑）；只印平面、单色。
A 面局部坐标原点 = 前面板左下（x −2、z 88 折弯虚拟尖角），B 面原点 = 斜面左下（x 0、斜面下沿），B 面放在 A 面下方、左右对齐。
需要先跑 AP.front_panel()、AP.slant() 填 FEATURES（fig_silkscreen.main 里做）。"""
import numpy as np
import ezdxf
import assembly_panel as AP
import silkscreen as S

NAME = "前壳_front_shell_丝印.dxf"
A_W, A_H = AP.SHELL_W, AP.H - AP.Z_CHIN                     # 324 × 332
B_W, B_H = AP.W, AP.SLANT_TOP_U - AP.U_EDGE                 # 320 × 90.8
A_Y0 = B_H + 70                                             # A 面放在 B 面上方 70
B_X0 = -AP.SHELL_X0                                         # B 面左边对齐 A 面里的 x 0（A 面比斜面左右各宽 2）
DIM = dict(dimlfac=1.0, dimdsep=46, dimtxt=3.0, dimasz=2.0, dimexe=1.5, dimexo=1.0, dimgap=0.8, dimdec=1, dimzin=8, dimclrd=3, dimclre=3, dimclrt=3)
NOTES = [
    "MIS-01 前壳 丝印图   比例 1:1   单位 mm",
    "1. 丝印颜色：黑色，单色。底色：米白喷粉，喷粉后丝印。",
    "2. 两个印刷面，都是平面：",
    "   A 面 = 竖直前面板（从正前方看）；",
    "   B 面 = 斜面（垂直斜面看；下边 = 斜面下沿，上边 = 与 A 面的折弯线）。",
    "3. 图层：SILK = 丝印（黑色实心填充，只印这一层）；",
    "   OUTLINE = 钣金外形和开孔（定位用，不印）；DIM = 尺寸；NOTE = 说明。",
    "4. 外形线按折弯虚拟尖角画。丝印离折弯线 >= 6，离开孔 >= 1。",
    "5. 定位以开孔为准：B 面档位 1-6 以旋钮孔为圆心；",
    "   HOST / HV / DISPLAY 和 ON / OFF 以三个钮子孔为中线；推子刻度以两条槽为准。",
    "6. 最小字高 2.5，最细线 0.4。对应零件：前壳_front_shell.step。",
]


def _a(x, z):
    return (x - AP.SHELL_X0, z - AP.Z_CHIN + A_Y0)


def _b(x, u):
    return (x + B_X0, u - AP.U_EDGE)


def _map(face):
    return _a if face == "front" else _b


def _poly(msp, pts, layer):
    msp.add_lwpolyline([tuple(map(float, p)) for p in pts], close=True, dxfattribs=dict(layer=layer))


def _dim(msp, base, p1, p2, angle=0):
    msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle="EZDXF",
                       override=DIM, dxfattribs=dict(layer="DIM")).render()


def _silk(msp):
    for face, polys in S.elements():
        f = _map(face)
        for o, hs in polys:
            o2 = [f(*p) for p in o]
            h2 = [[f(*p) for p in h] for h in hs]
            hatch = msp.add_hatch(color=7, dxfattribs=dict(layer="SILK"))
            hatch.rgb = (0, 0, 0)
            hatch.paths.add_polyline_path(o2, is_closed=True, flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)
            _poly(msp, o2, "SILK")
            for h in h2:
                hatch.paths.add_polyline_path(h, is_closed=True)
                _poly(msp, h, "SILK")


def _outline(msp):
    for face, (w, h), o in (("front", (A_W, A_H), (0, A_Y0)), ("slant", (B_W, B_H), (B_X0, 0))):
        _poly(msp, [o, (o[0] + w, o[1]), (o[0] + w, o[1] + h), (o[0], o[1] + h)], "OUTLINE")
        f = _map(face)
        cut, holes = AP.FEATURES[face]
        for c in cut:
            x, y, cw, ch = c[:4]
            _poly(msp, [f(x, y), f(x + cw, y), f(x + cw, y + ch), f(x, y + ch)], "OUTLINE")
        for x, y, d in holes:
            msp.add_circle(f(x, y), d / 2, dxfattribs=dict(layer="OUTLINE"))


def _dims(msp):
    els = dict(S.elements())
    # A 面：外形；机名左边、上沿离面板顶边；副标题右边、上沿
    _dim(msp, (0, A_Y0 + A_H + 12), (0, A_Y0 + A_H), (A_W, A_Y0 + A_H))
    _dim(msp, (-12, 0), (0, A_Y0), (0, A_Y0 + A_H), 90)
    logo = S.text(S.FRONT_LOGO[0], 0, 0, S.CAP["logo"])                         # 只为取外框，位置用 front() 里的
    lo, hi = S.bbox(els["front"][:len(logo)])
    lo, hi = _a(*lo), _a(*hi)
    top = A_Y0 + A_H
    _dim(msp, (lo[0] / 2, top - 6), (0, top - 4), (lo[0], hi[1]))
    _dim(msp, (lo[0] - 8, 0), (lo[0], hi[1]), (lo[0], top), 90)
    lo2, hi2 = S.bbox(els["front"][len(logo):])
    lo2, hi2 = _a(*lo2), _a(*hi2)
    _dim(msp, (hi2[0] + 6, 0), (hi2[0], hi2[1]), (hi2[0], top), 90)
    _dim(msp, (0, top - 10), (hi2[0], hi2[1]), (A_W, top - 4))
    # B 面：外形；旋钮孔中心、推子刻度首格、两排刻度、钮子列
    _dim(msp, (0, -14), (B_X0, 0), (B_X0 + B_W, 0))
    _dim(msp, (B_X0 + B_W + 12, 0), (B_X0 + B_W, 0), (B_X0 + B_W, B_H), 90)
    c = _b(*AP.SEL)
    _dim(msp, (0, -7), (B_X0, 0), (c[0], c[1]))
    _dim(msp, (B_X0 - 8, 0), (B_X0, 0), c, 90)
    t0 = _b(AP.FADER_X - 30, AP.FADER_U[1] - S.FADER_GAP)
    t1 = _b(AP.FADER_X - 30, AP.FADER_U[0] + S.FADER_GAP)
    _dim(msp, (0, -7), c, (t0[0], t0[1]))
    _dim(msp, (t0[0] - 6, 0), (B_X0, 0), t0, 90)
    _dim(msp, (t0[0] - 12, 0), (B_X0, 0), t1, 90)
    _dim(msp, (0, B_H + 8), t1, _b(AP.FADER_X + 30, AP.FADER_U[0] + S.FADER_GAP))
    tg = [_b(x, AP.TOG_U) for x in AP.TOG_X]
    _dim(msp, (0, -7), (t0[0], 0), (tg[0][0], tg[0][1]))
    _dim(msp, (0, B_H + 8), tg[0], tg[1])
    _dim(msp, (0, B_H + 8), tg[1], tg[2])


def _notes(msp):
    x0, y = A_W + 25, A_Y0 + A_H
    for k, line in enumerate(NOTES):
        msp.add_text(line, height=5.0 if k == 0 else 3.5,
                     dxfattribs=dict(layer="NOTE", style="CN")).set_placement((x0, y - (8 if k == 0 else 6) * (k > 0) - 6 * max(k - 1, 0)))
    msp.add_text("A 面：竖直前面板（正视）", height=5.0, dxfattribs=dict(layer="NOTE", style="CN")).set_placement((0, A_Y0 + A_H + 22))
    msp.add_text("B 面：斜面（垂直斜面看，上边接 A 面下沿折弯）", height=5.0,
                 dxfattribs=dict(layer="NOTE", style="CN")).set_placement((B_X0, B_H + 18))


def write(fname):
    doc = ezdxf.new("R2010", units=ezdxf.units.MM, setup=True)
    doc.styles.add("CN", font="simhei.ttf")
    for name, col in (("SILK", 7), ("OUTLINE", 1), ("DIM", 3), ("NOTE", 5)):
        doc.layers.add(name, color=col)
    msp = doc.modelspace()
    _outline(msp); _silk(msp); _dims(msp); _notes(msp)
    doc.saveas(fname)
    print("saved", fname)
    return doc
