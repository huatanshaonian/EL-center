"""
MIS-01 —— 面板 / 斜面上的操作与指示器件（参数化占位模型）
坐标：原点=面板前表面上的开孔中心；面板前表面在 Y=0，露在外面的部分朝 -Y，机内部分朝 +Y；X 宽、Z 高。
尺寸取同类器件的常见规格，全部为 T（暂定）：实物到手后改各函数的 SPEC 再重新导出。
"""
import math
import cadquery as cq
from parts import box, cyl

def _hex(af, t, y0):
    """对边 af、厚 t 的六角螺母，贴在 Y=y0 起向 +Y"""
    return cq.Workplane("XZ").polygon(6, af / math.cos(math.pi / 6)).extrude(-t).translate((0, y0, 0))

def square_lamp_button():
    """方形带灯自复位按钮，开孔 Ø16（LA16 / AD16 类，一开一闭）"""
    SPEC = dict(bezel=18.0, bezel_t=3.0, cap=14.5, cap_h=5.0, thread_d=16.0, body_L=30.0, term_L=8.0, panel_t=2.0)
    s = SPEC
    b = box(s["bezel"], s["bezel_t"], s["bezel"], -s["bezel"] / 2, -s["bezel_t"], -s["bezel"] / 2)
    b = b.union(box(s["cap"], s["cap_h"], s["cap"], -s["cap"] / 2, -s["bezel_t"] - s["cap_h"], -s["cap"] / 2))
    b = b.union(cyl(s["thread_d"] / 2 - 0.1, s["body_L"], 0, 0, 0, "Y"))
    b = b.union(_hex(19, 3, s["panel_t"]))
    return b.union(box(12, s["term_L"], 6, -6, s["body_L"], -3))

def toggle_guarded():
    """带翻盖保护罩的钮子开关（M6 螺纹小钮子 + 红色保护盖）"""
    SPEC = dict(bush_d=6.0, bush_L=9.0, lever_d=3.0, lever_L=10.0, body=(8.0, 10.0, 13.0), term_L=4.0,
                cover=(15.0, 17.0, 33.0), cover_wall=1.5, panel_t=2.0)
    s = SPEC
    bx, by, bz = s["body"]
    t = cyl(s["bush_d"] / 2, s["bush_L"], 0, -s["bush_L"] + s["panel_t"], 0, "Y")
    t = t.union(cyl(s["lever_d"] / 2, s["lever_L"], 0, -s["bush_L"] + s["panel_t"] - s["lever_L"], 0, "Y"))
    t = t.union(box(bx, by, bz, -bx / 2, s["panel_t"], -bz / 2))
    t = t.union(box(bx - 2, s["term_L"], bz - 2, -bx / 2 + 1, s["panel_t"] + by, -bz / 2 + 1))
    cx, cy, cz = s["cover"]; w = s["cover_wall"]
    cover = box(cx, cy, cz, -cx / 2, -cy, -cz / 2 + 4).cut(box(cx - 2 * w, cy - w, cz - 2 * w, -cx / 2 + w, -cy + w, -cz / 2 + 4 + w))
    return t.union(cover)

def indicator_lamp():
    """Ø8 开孔金属指示灯"""
    SPEC = dict(head_d=10.0, head_h=4.0, body_d=8.0, body_L=18.0, panel_t=2.0)
    s = SPEC
    b = cyl(s["head_d"] / 2, s["head_h"], 0, -s["head_h"], 0, "Y").edges("<Y").fillet(1.5)
    return b.union(cyl(s["body_d"] / 2 - 0.1, s["body_L"], 0, 0, 0, "Y")).union(_hex(11, 2.5, s["panel_t"]))

def rotary_selector():
    """波段开关（单刀多位，M10 螺纹）+ Ø32 指针旋钮"""
    SPEC = dict(body_d=26.0, body_L=12.0, bush_d=9.5, bush_L=8.0, shaft_d=6.0, shaft_L=20.0,
                knob_d=24.0, knob_h=13.0, skirt_d=32.0, skirt_h=4.0, panel_t=2.0)
    s = SPEC
    b = cyl(s["body_d"] / 2, s["body_L"], 0, s["panel_t"], 0, "Y")
    b = b.union(cyl(s["bush_d"] / 2, s["bush_L"], 0, s["panel_t"] - s["bush_L"], 0, "Y"))
    b = b.union(cyl(s["shaft_d"] / 2, s["shaft_L"], 0, s["panel_t"] - s["shaft_L"], 0, "Y"))
    b = b.union(box(s["body_d"] - 6, 5, 4, -s["body_d"] / 2 + 3, s["panel_t"] + s["body_L"], -2))        # 焊片
    y_skirt = -1.0 - s["skirt_h"]
    knob = cyl(s["skirt_d"] / 2, s["skirt_h"], 0, y_skirt, 0, "Y")
    knob = knob.union(cyl(s["knob_d"] / 2, s["knob_h"], 0, y_skirt - s["knob_h"], 0, "Y").edges("<Y").fillet(1.5))
    knob = knob.union(box(3, 1.5, s["skirt_d"] / 2, -1.5, y_skirt - s["knob_h"] - 1.5, 0))                # 指针条
    return b.union(knob)

def panel_meter():
    """方形指针表头（85C1 类）：面框 64x56，表体 Ø50 穿过面板"""
    SPEC = dict(face_w=64.0, face_h=56.0, face_t=11.0, body_d=50.0, body_L=37.0, stud_pitch=(48.0, 42.0), panel_t=2.0)
    s = SPEC
    m = box(s["face_w"], s["face_t"], s["face_h"], -s["face_w"] / 2, -s["face_t"], -s["face_h"] / 2).edges("|Y").fillet(3)
    m = m.cut(box(s["face_w"] - 8, 1.0, s["face_h"] - 16, -s["face_w"] / 2 + 4, -s["face_t"] - 0.01, -s["face_h"] / 2 + 12))   # 表盘窗
    m = m.union(cyl(s["body_d"] / 2, s["body_L"], 0, 0, 0, "Y"))
    px, pz = s["stud_pitch"]
    for sx in (-1, 1):
        for sz in (-1, 1):
            m = m.union(cyl(1.5, 12, sx * px / 2, 0, sz * pz / 2, "Y"))
    return m

def speaker_40():
    """Ø40 小喇叭，贴在面板背面"""
    SPEC = dict(frame_d=40.0, frame_t=3.0, magnet_d=20.0, depth=15.0, panel_t=2.0)
    s = SPEC
    sp = cyl(s["frame_d"] / 2, s["frame_t"], 0, s["panel_t"], 0, "Y")
    cone = cq.Workplane("XZ").circle(s["frame_d"] / 2 - 2).workplane(offset=-(s["depth"] - s["frame_t"] - 6)).circle(s["magnet_d"] / 2).loft()
    sp = sp.union(cone.translate((0, s["panel_t"] + s["frame_t"], 0)))
    return sp.union(cyl(s["magnet_d"] / 2, 6, 0, s["panel_t"] + s["depth"] - 6, 0, "Y"))

def rect_lamp_button():
    """24x18 长方形带灯按钮，键帽为透明灯罩、内可插菲林字片；面板开方孔（全部 T，到货实测）"""
    SPEC = dict(bezel=(24.0, 18.0), bezel_t=3.0, lens=(20.0, 14.0), lens_h=4.0, cut=(22.0, 16.0),
                body_L=28.0, clip_t=2.0, term_L=8.0, panel_t=2.0)
    s = SPEC
    bw, bh = s["bezel"]; lw, lh = s["lens"]; cw, ch = s["cut"]
    b = box(bw, s["bezel_t"], bh, -bw / 2, -s["bezel_t"], -bh / 2).edges("|Y").fillet(1.5)
    b = b.union(box(lw, s["lens_h"], lh, -lw / 2, -s["bezel_t"] - s["lens_h"], -lh / 2).edges("|Y").fillet(1.0))   # 灯罩（字片在其内）
    b = b.union(box(cw - 0.4, s["body_L"], ch - 0.4, -cw / 2 + 0.2, 0, -ch / 2 + 0.2).edges("|Y").fillet(2.8))  # 与开孔圆角 R3 配合
    b = b.union(box(cw + 4, s["clip_t"], ch + 4, -cw / 2 - 2, s["panel_t"], -ch / 2 - 2))                       # 背面卡框
    return b.union(box(14, s["term_L"], 8, -7, s["body_L"], -4))

def fader_60(pos=0.5):
    """60 mm 行程直滑推子（Bourns PTA6043 类）+ 推子帽，本体贴在面板背面，拨杆穿过开槽
    原点=开槽中心（面板前表面），槽沿 X；pos=推子帽位置 0..1
    本体 75x9、行程 60、拨杆 15：C（PTA6043-2015 型号/规格书标称）；本体高 9.5 由总高 24.5 反推；开槽、推子帽：T"""
    SPEC = dict(body_L=75.0, body_W=9.0, body_H=9.5, travel=60.0, lever_L=15.0, lever=(4.0, 1.2),
                cap=(10.0, 12.0, 12.0), slot=(62.0, 2.0), panel_t=2.0)
    s = SPEC
    L, Wb, Hb, t = s["body_L"], s["body_W"], s["body_H"], s["panel_t"]
    f = box(L, Hb, Wb, -L / 2, t, -Wb / 2)
    for k in range(3):                                                                    # 焊针
        f = f.union(box(0.8, 4, 0.8, -L / 2 + 3 + k * 2.5, t + Hb, -0.4))
    x = -s["travel"] / 2 + pos * s["travel"]
    lx, lz = s["lever"]                                                                   # 拨杆沿槽宽 4、横穿槽 1.2
    tip = t - s["lever_L"]                                                                # 拨杆端（伸出面板外）
    f = f.union(box(lx, s["lever_L"], lz, x - lx / 2, tip, -lz / 2))
    cx, cy, cz = s["cap"]
    return f.union(box(cx, cy, cz, x - cx / 2, tip - 2, -cz / 2).edges("|Z").fillet(1.5))

def usb_a_panel():
    """面板安装 USB-A 母座（卡入式 / 延长线母头占位）：开孔 13.4x6，前沿 15.5x8 法兰在面板外（全部 T）"""
    SPEC = dict(cut=(13.4, 6.0), flange=(15.5, 8.0, 1.2), shell_L=16.0, port=(12.5, 5.1, 12.0), tongue=(11.2, 1.8), panel_t=2.0)
    s = SPEC
    fw, fh, ft = s["flange"]; cw, ch = s["cut"]; pw, ph, pd = s["port"]
    u = box(fw, ft, fh, -fw / 2, -ft, -fh / 2)
    u = u.union(box(cw - 0.2, s["shell_L"], ch - 0.2, -cw / 2 + 0.1, 0, -ch / 2 + 0.1))
    u = u.cut(box(pw, pd, ph, -pw / 2, -ft - 0.01, -ph / 2))                               # 插口
    tw, th = s["tongue"]
    return u.union(box(tw, pd - 1, th, -tw / 2, -ft + 1, -ph / 2 + 0.6))                 # 舌片

def iec_c14_inlet():
    """后面板 IEC C14 三合一电源座（插座 + 保险丝 + 船型开关），开孔 27x47；原点=开孔中心，法兰在面板外侧（-Y）"""
    SPEC = dict(cut_w=27.0, cut_h=47.0, flange_w=31.0, flange_h=60.0, flange_t=2.5, depth=30.0)
    s = SPEC
    b = box(s["flange_w"], s["flange_t"], s["flange_h"], -s["flange_w"] / 2, -s["flange_t"], -s["flange_h"] / 2)
    b = b.union(box(s["cut_w"], s["depth"], s["cut_h"], -s["cut_w"] / 2, 0, -s["cut_h"] / 2))
    b = b.cut(box(20, 12, 16, -10, -s["flange_t"] - 0.01, -s["cut_h"] / 2 + 3))            # 插口
    b = b.union(box(14, 3, 10, -7, -s["flange_t"] - 3, s["cut_h"] / 2 - 14))               # 船型开关
    return b.union(box(18, 6, 30, -9, s["depth"], -15))                                    # 接线片
