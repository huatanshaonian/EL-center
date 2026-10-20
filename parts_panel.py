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
    """Ø16 开孔指示灯，12 V（灯头外径 19.5 按商品页；灯头高、身长为 T）"""
    SPEC = dict(head_d=19.5, head_h=6.0, body_d=16.0, body_L=40.0, panel_t=2.0)
    s = SPEC
    b = cyl(s["head_d"] / 2, s["head_h"], 0, -s["head_h"], 0, "Y").edges("<Y").fillet(1.5)
    return b.union(cyl(s["body_d"] / 2 - 0.1, s["body_L"], 0, 0, 0, "Y")).union(_hex(20, 3.0, s["panel_t"]).rotate((0, 0, 0), (0, 1, 0), 30))   # 螺母平边对平边（灯距 21）

def rotary_selector():
    """六钧 MFR01-A2F05L1S-R 波段开关 + Ø32 指针旋钮。
    本体 Ø32×14 贴面板背面、焊片再伸 4.5；M10 螺纹 5.5；轴 Ø6，从本体前面起 14；
    2 个 Ø4.1 防转凸柱（间距 22，伸出 1.5）插面板孔（C：六钧图纸 2015-10-22）；旋钮 T"""
    SPEC = dict(body_d=32.0, body_L=14.0, lug_L=4.5, bush_d=10.0, bush_L=5.5, shaft_d=6.0, shaft_L=14.0,
                pin_d=4.1, pin_dx=22.0, pin_L=1.5,
                knob_d=24.0, knob_h=13.0, skirt_d=32.0, skirt_h=4.0, panel_t=2.0)
    s = SPEC
    t = s["panel_t"]
    b = cyl(s["body_d"] / 2, s["body_L"], 0, t, 0, "Y")
    b = b.union(cyl(s["bush_d"] / 2, s["bush_L"], 0, t - s["bush_L"], 0, "Y"))
    b = b.union(cyl(s["shaft_d"] / 2, s["shaft_L"], 0, t - s["shaft_L"], 0, "Y"))
    for sx in (-1, 1):
        b = b.union(cyl(s["pin_d"] / 2 - 0.05, s["pin_L"], sx * s["pin_dx"] / 2, t - s["pin_L"], 0, "Y"))
    b = b.union(box(24, s["lug_L"], 24, -12, t + s["body_L"], -12))                                    # 焊片区
    y_skirt = -1.0 - s["skirt_h"]
    knob = cyl(s["skirt_d"] / 2, s["skirt_h"], 0, y_skirt, 0, "Y")
    knob = knob.union(cyl(s["knob_d"] / 2, s["knob_h"], 0, y_skirt - s["knob_h"], 0, "Y").edges("<Y").fillet(1.5))
    knob = knob.union(box(3, 1.5, s["skirt_d"] / 2, -1.5, y_skirt - s["knob_h"] - 1.5, 0))                # 指针条
    return b.union(knob)

def panel_meter():
    """方形指针表头 85C1（0–1 mA）：面框 64x56，背面凸台 Ø49x2.5 嵌进面板 Ø50 孔，表体 Ø26；
    2 颗 M3 螺柱水平孔距 52、在表心下方 13；板后总深 47.5（C：浦江 Enerdis 矩形电表样本 p20；面框厚 T）"""
    SPEC = dict(face_w=64.0, face_h=56.0, face_t=11.0, boss_d=49.0, boss_t=2.5, body_d=26.0, depth=47.5,
                stud_dx=52.0, stud_z=-13.0, stud_L=12.0, panel_t=2.0)
    s = SPEC
    m = box(s["face_w"], s["face_t"], s["face_h"], -s["face_w"] / 2, -s["face_t"], -s["face_h"] / 2).edges("|Y").fillet(3)
    m = m.cut(box(s["face_w"] - 8, 1.0, s["face_h"] - 16, -s["face_w"] / 2 + 4, -s["face_t"] - 0.01, -s["face_h"] / 2 + 12))   # 表盘窗
    m = m.union(cyl(s["boss_d"] / 2, s["boss_t"], 0, 0, 0, "Y"))                                   # 凸台
    m = m.union(cyl(s["body_d"] / 2, s["depth"], 0, 0, 0, "Y"))                                   # 表体
    for sx in (-1, 1):
        m = m.union(cyl(1.5, s["stud_L"], sx * s["stud_dx"] / 2, 0, s["stud_z"], "Y"))
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
    """正泰 LA16 系列长方形带灯自复位按钮：头部 24x18，面板开 Ø16 圆孔（LA16 类通用：Ø16 +0.2，安装间距 ≥18x24，
    M16 螺纹 + 背面锁紧圈）。头部、身长、开关元件尺寸为 T，到货实测"""
    SPEC = dict(bezel=(24.0, 18.0), bezel_t=3.0, lens=(20.0, 14.0), lens_h=4.0, thread_d=16.0, thread_L=12.0,
                ring_d=21.0, ring_t=3.0, elem=17.0, elem_L=18.0, term_L=8.0, panel_t=2.0)
    s = SPEC
    bw, bh = s["bezel"]; lw, lh = s["lens"]; t = s["panel_t"]
    b = box(bw, s["bezel_t"], bh, -bw / 2, -s["bezel_t"], -bh / 2).edges("|Y").fillet(1.5)
    b = b.union(box(lw, s["lens_h"], lh, -lw / 2, -s["bezel_t"] - s["lens_h"], -lh / 2).edges("|Y").fillet(1.0))   # 灯罩（字片在其内）
    b = b.union(cyl(s["thread_d"] / 2 - 0.1, s["thread_L"], 0, 0, 0, "Y"))                                      # M16 螺纹筒
    b = b.union(cyl(s["ring_d"] / 2, s["ring_t"], 0, t, 0, "Y"))                                                 # 锁紧圈
    e = s["elem"]
    b = b.union(box(e, s["elem_L"], e, -e / 2, s["thread_L"], -e / 2))                                          # 开关元件
    return b.union(box(14, s["term_L"], 8, -7, s["thread_L"] + s["elem_L"], -4))

def fader_60(pos=0.5):
    """60 mm 行程直滑推子（Bourns PTA6043 类）+ 推子帽，本体贴在面板背面，拨杆穿过开槽
    原点=开槽中心（面板前表面），槽沿 X；pos=推子帽位置 0..1
    本体 75x9、行程 60、拨杆 15、外壳顶面到 PCB 座面 6.5：C（Bourns PTA 规格书 p2 PTAxx43 图）；开槽、推子帽：T"""
    SPEC = dict(body_L=75.0, body_W=9.0, body_H=6.5, travel=60.0, lever_L=15.0, lever=(4.0, 1.2),
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

USB_EXT = dict(cut=(15.0, 8.0), ear=(35.0, 11.0, 2.5), hole_dx=28.0, body=(18.0, 10.0, 22.0), boot_d=8.0, boot_L=15.0,
               port=(12.5, 5.1, 12.0), panel_t=2.0)

def usb_panel_ext():
    """带安装耳的 USB-A 面板安装延长线母头（USB3 / USB2 同外形）：开孔 15x8，耳板 35x11 贴面板背面，
    2 个 M3 耳孔距 28，母座口与面板前表面齐平；后面接线尾（全部 T，按常见商品估计，到货实测）"""
    s = USB_EXT
    cw, ch = s["cut"]; ew, eh, et = s["ear"]; bw, bh, bl = s["body"]; pw, ph, pd = s["port"]; t = s["panel_t"]
    u = box(cw - 0.3, t, ch - 0.3, -cw / 2 + 0.15, 0, -ch / 2 + 0.15).edges("|Y").fillet((ch - 0.3) / 2 - 0.05)   # 口部，配 P.panel 的长圆开孔
    u = u.union(box(ew, et, eh, -ew / 2, t, -eh / 2))                                        # 耳板
    for sx in (-1, 1):
        u = u.cut(cyl(1.6, et + 0.02, sx * s["hole_dx"] / 2, t - 0.01, 0, "Y"))
    u = u.union(box(bw, bl, bh, -bw / 2, t + et, -bh / 2))                                   # 母座本体
    u = u.union(cyl(s["boot_d"] / 2, s["boot_L"], 0, t + et + bl, 0, "Y"))                   # 线尾
    return u.cut(box(pw, pd, ph, -pw / 2, -0.01, -ph / 2))                                   # 插口

def iec_c14_inlet():
    """后面板 IEC C14 三合一电源座 AC-14-F12（插座 + 双保险丝 + 双极船型开关，左右耳固定）。
    C（商品图纸）：法兰 49.4x66、厚约 2，本体 27x59，面板后含端子约 35.4；开孔 28x60，耳孔距 40（M3）。
    上为 C14 插口（24.6x16.2）、中为保险丝抽屉、下为开关。原点=开孔中心，法兰在面板外侧（-Y）"""
    SPEC = dict(cut_w=28.0, cut_h=60.0, flange_w=49.4, flange_h=66.0, flange_t=2.0, body_w=27.0, body_h=59.0,
                depth=35.4, ear_dx=40.0, inlet=(24.6, 16.2), inlet_z=18.0)
    s = SPEC
    b = box(s["flange_w"], s["flange_t"], s["flange_h"], -s["flange_w"] / 2, -s["flange_t"], -s["flange_h"] / 2)
    for sx in (-1, 1):
        b = b.cut(cyl(1.75, s["flange_t"] + 0.02, sx * s["ear_dx"] / 2, -s["flange_t"] - 0.01, 0, "Y"))
    b = b.union(box(s["body_w"], s["depth"] - 6, s["body_h"], -s["body_w"] / 2, 0, -s["body_h"] / 2))
    iw, ih = s["inlet"]
    b = b.cut(box(iw, 16, ih, -iw / 2, -s["flange_t"] - 0.01, s["inlet_z"] - ih / 2))     # C14 插口
    b = b.union(box(20, 3, 13, -10, -s["flange_t"] - 3, -s["cut_h"] / 2 + 5))              # 船型开关（下）
    return b.union(box(20, 6, 40, -10, s["depth"] - 6, -22))                               # 接线片
