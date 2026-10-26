"""
MIS-01 前壳丝印设计（2026-10-27 用户定：米白喷粉 + 黑色丝印，只印确定不变的内容）。
印的内容：前面板机名；斜面模式旋钮档位 1–5、两根推子刻度、三个钮子的名称和 ON / OFF。
不印：6 个方键（菲林字片）、编码器、推子的用途（软件定，以后贴标签）、USB。
坐标：前面板 (x, z) = 全局；斜面 (x, u) = assembly_panel 的斜面局部坐标（u 0 = 斜面电路板下沿）。
图形一律是填充多边形：elements() 返回 [(面, [(外轮廓 N×2, [孔 M×2, ...]), ...]), ...]，出图（fig_silkscreen.py）和效果图（render_silkscreen.py）共用。
"""
import math
import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
import assembly_panel as AP

FONT = FontProperties(fname=r"C:\Windows\Fonts\bahnschrift.ttf")   # DIN 1451 风格，仪器面板常用
LINE = 0.4                                   # 刻度线宽（丝印最细按 0.2 算，留余量）
CAP = dict(logo=9.0, sub=3.0, name=3.0, onoff=2.5, num=3.0, scale=2.5)   # 各类字的大写字母高
TOGGLE_NAMES = ("HOST", "HV", "DISPLAY")      # 钮子从左到右：主机、高压、屏幕（整机架构 5.1；都是拨上 = 开）
SEL_POS = 5                                  # 模式旋钮印 1–5（开关是 6 位，第 6 位用止动片挡掉）
SEL_ANG = [180 - 45 * k for k in range(SEL_POS)]   # 1 在左（水平）、3 朝上、5 在右，45° 一格；装开关时把 1 档对准左边
SEL_R = (18.0, 21.0, 24.5)                   # 刻度内径（旋钮裙边 Ø32 外 2）、外径、数字中心半径
FADER_TICKS = 11                             # 推子刻度 0–10，行程 60 → 每格 6
FADER_TICK = (2.0, 3.0)                      # 短 / 长（0、5、10）刻度长
FADER_GAP = 7.0                              # 刻度离槽中心（推子帽 12 宽，外 1）
TOG_ONOFF_DU = 9.0                           # ON / OFF 离钮子螺纹孔中心
TOG_NAME_U = 45.0                            # 钮子名称（开关 u 26 和指示灯 u 63 之间）
FRONT_LOGO = ("MIS-01", "MULTI-INDICATOR STATION")
LOGO_Z = 383.0                               # 机名基线 z（EL 视窗上沿 369.2，顶部 M4 螺钉 z 410）
U_MAX, Z_MIN = 77.0, 93.0                    # 丝印不进折弯区：斜面 u ≤ 77、前面板 z ≥ 93（折弯在 u 83 / z 88）


def _cap_scale():
    p = TextPath((0, 0), "H", size=100, prop=FONT)
    return 100.0 / (p.get_extents().y1 - p.get_extents().y0)


_K = _cap_scale()


def text(s, x, y, cap, ha="center", va="center", rot=0.0):
    """文字 → 填充多边形（带孔）。va center = 大写字母高的中线；rot 绕 (x, y) 逆时针（度）"""
    p = TextPath((0, 0), s, size=100, prop=FONT)
    k = cap * _K / 100
    ext = p.get_extents()
    dx = {"left": -ext.x0, "center": -(ext.x0 + ext.x1) / 2, "right": -ext.x1}[ha] * k
    dy = {"base": 0.0, "center": -cap / 2, "top": -cap}[va]
    polys = [np.asarray(q) * k + (dx, dy) for q in p.to_polygons(closed_only=True) if len(q) > 2]
    return [(_rot(o, x, y, rot), [_rot(h, x, y, rot) for h in hs]) for o, hs in _nest(polys)]


def _rot(pts, x, y, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.column_stack([pts[:, 0] * c - pts[:, 1] * s + x, pts[:, 0] * s + pts[:, 1] * c + y])


def _area(p):
    return 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])


def _nest(polys):
    """字形轮廓分成 外轮廓 + 孔：被奇数个轮廓包住的是孔，归到包住它的最小轮廓"""
    paths = [Path(p) for p in polys]
    depth, parent = [], []
    for i, p in enumerate(polys):
        inside = [j for j in range(len(polys)) if j != i and paths[j].contains_point(p[0])]
        depth.append(len(inside))
        parent.append(min(inside, key=lambda j: abs(_area(polys[j]))) if inside else None)
    out = {i: (polys[i], []) for i in range(len(polys)) if depth[i] % 2 == 0}
    for i in range(len(polys)):
        if depth[i] % 2 == 1:
            out[parent[i]][1].append(polys[i])
    return list(out.values())


def bar(x0, y0, x1, y1, w=LINE):
    """线段 → 宽 w 的矩形"""
    d = np.array([x1 - x0, y1 - y0]); n = np.array([-d[1], d[0]]) / np.hypot(*d) * w / 2
    a, b = np.array([x0, y0]), np.array([x1, y1])
    return [(np.array([a + n, b + n, b - n, a - n]), [])]


def front():
    """前面板：左上机名、右上副标题，基线对齐，左右与 EL 视窗边对齐"""
    sx0 = (AP.W - 267) / 2
    ex0 = sx0 + (267 - 211.2) / 2 - 2
    ex1 = ex0 + 211.2 + 4
    out = text(FRONT_LOGO[0], ex0, LOGO_Z, CAP["logo"], ha="left", va="base")
    out += text(FRONT_LOGO[1], ex1, LOGO_Z, CAP["sub"], ha="right", va="base")
    return out


def slant():
    out = []
    # 模式旋钮：5 根刻度 + 数字
    cx, cu = AP.SEL
    r0, r1, rn = SEL_R
    for k, a in enumerate(SEL_ANG):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        out += bar(cx + r0 * c, cu + r0 * s, cx + r1 * c, cu + r1 * s, 0.6)
        out += text(str(k + 1), cx + rn * c, cu + rn * s, CAP["num"])
    # 推子：上面那根刻度在槽上方、下面那根在槽下方（两槽之间只有 16，放不下两排）
    trav = 60.0
    for u, side in zip(AP.FADER_U, (1, -1)):
        u0 = u + side * FADER_GAP
        for k in range(FADER_TICKS):
            x = AP.FADER_X - trav / 2 + k * trav / (FADER_TICKS - 1)
            L = FADER_TICK[1] if k % 5 == 0 else FADER_TICK[0]
            out += bar(x, u0, x, u0 + side * L)
        um = u0 + side * FADER_TICK[1] / 2
        out += text("0", AP.FADER_X - trav / 2 - 3.5, um, CAP["scale"], ha="right")
        out += text("10", AP.FADER_X + trav / 2 + 3.5, um, CAP["scale"], ha="left")
    # 钮子：名称在开关和指示灯之间，ON 在上（拨上 = 开）、OFF 在下
    for x, name in zip(AP.TOG_X, TOGGLE_NAMES):
        out += text(name, x, TOG_NAME_U, CAP["name"])
        out += text("ON", x, AP.TOG_U + TOG_ONOFF_DU, CAP["onoff"])
        out += text("OFF", x, AP.TOG_U - TOG_ONOFF_DU, CAP["onoff"])
    return out


def elements():
    return [("front", front()), ("slant", slant())]


def bbox(polys):
    a = np.vstack([o for o, _ in polys])
    return a.min(0), a.max(0)


def check():
    """丝印离折弯、开孔的最小距离（开孔取 assembly_panel.FEATURES，要先跑 AP.front_panel()、AP.slant()）"""
    msg = []
    for face, polys in elements():
        lo, hi = bbox(polys)
        if face == "slant" and hi[1] > U_MAX:
            msg.append(f"斜面丝印进折弯区：u 最高 {hi[1]:.1f}")
        if face == "front" and lo[1] < Z_MIN:
            msg.append(f"前面板丝印进折弯区：z 最低 {lo[1]:.1f}")
        cut, holes = AP.FEATURES[face]
        pts = np.vstack([o for o, _ in polys])
        for x, z, d in holes:
            m = np.hypot(pts[:, 0] - x, pts[:, 1] - z).min() - d / 2
            if m < 1.0:
                msg.append(f"{face} 孔 ({x:.1f},{z:.1f}) Ø{d} 离丝印 {m:.2f}")
        for c in cut:
            x, z, w, h = c[:4]
            dx = np.maximum(np.maximum(x - pts[:, 0], pts[:, 0] - x - w), 0)
            dz = np.maximum(np.maximum(z - pts[:, 1], pts[:, 1] - z - h), 0)
            m = np.hypot(dx, dz).min()
            if m < 1.0:
                msg.append(f"{face} 开窗 ({x:.1f},{z:.1f},{w},{h}) 离丝印 {m:.2f}")
    return msg
