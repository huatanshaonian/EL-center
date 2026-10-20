"""
MIS-01 —— 新增的电子模块与外设（仪器层 / 输入层）
坐标同 parts.py：PCB / 模块类以板底面左前角为原点，X 长、Y 宽、Z 向上；管子类轴沿 +X。
C=已确认(原厂/可靠资料)  T=暂定(待实物测绘)
"""
import math
import cadquery as cq
from parts import box, cyl
import vendor_parts as V

def j305(L=103.5):
    """J305β 盖革管（用户实测 2026-10-20）：总长 103.5，管身外径 10；两端电极 Ø6.3、长约 6.3（完整圆柱段约 6）；
    两电极之间（去掉电极不完全是圆柱的部分）94。模型：管身 Ø10×94 居中，两端电极 Ø6.3 各露出 (103.5−94)/2；正负极未知。
    原点=一端中心，管轴沿 +X"""
    SPEC = dict(D=10.0, L=L, body_L=94.0, cap_D=6.3)
    s = SPEC
    e = (s["L"] - s["body_L"]) / 2
    b = cyl(s["D"] / 2, s["body_L"], e, 0, 0, "X")
    for x in (0, s["L"] - e):
        b = b.union(cyl(s["cap_D"] / 2, e, x, 0, 0, "X"))
    return b

def geiger_clip_strip(L=134.0, W=12.0, clips=(22.25, 123.25)):
    """盖革管夹子长条板（mis-01-56 方案 2026-10-20）：约 134×12，贴甲板（薄垫片调高），板上两只 Littelfuse 10207101009（C142864）6.3 mm 保险丝夹。
    夹子：沿管轴宽 7、两脚沿管轴相距 7.6、总高 10.9（C）；夹口中心离板面约 6.7（T，估算）。clips = 两只夹子中心的板坐标 x。
    原点 = 板底面左前角，X 沿管轴"""
    b = box(L, W, 1.6)
    for cx in clips:
        c = box(7, 7, 10.9, cx - 3.5, W / 2 - 3.5, 1.6).cut(cyl(3.15, 9, cx - 4.5, W / 2, 1.6 + 6.7, "X"))
        b = b.union(c.cut(box(9, 7.5, 6, cx - 4.5, W / 2 - 3.75, 1.6 + 6.7)))     # 夹口朝上开口
    return b

def geiger_clip_board():
    """（已被 geiger_clip_strip 取代，保留作参考）盖革管夹子小板：20×12，3AG 6.35 保险丝夹夹电极，板上放阳极电阻 / 检测三极管；1 颗 M3 走长槽锁甲板，可沿管轴调位置。
    占位：夹子宽 4.5（J305 每端露出的电极只有约 4.75，常见 3AG 夹宽 6–7 会碰玻壳，选型要注意）、夹口中心离板面 5.9（T，等选定保险丝夹再改）。
    原点=板底面左前角，X 沿管轴；夹子中心在 x 10，长槽在 +X 端"""
    b = box(20, 12, 1.6).union(box(4.5, 7, 5.9 + 3.15, 10 - 2.25, 2.5, 1.6))
    return b.cut(cyl(3.15, 6, 10 - 3, 6, 1.6 + 5.9, "X")).cut(box(7, 3.4, 3, 12.5, 4.3, -1))

def esp32s3_dev_kit():
    """微雪 Waveshare ESP32-S3-DEV-KIT（-U 外接天线版，模组 ESP32-S3-WROOM-1U-N16R8），预焊排针朝下。
    C（微雪官方外形尺寸图 2026-01-10）：板 63.30x25.40x1.6；2x22 针 2.54，两排 Y=1.27/24.13（排距 22.86），
    首针 X=5.05（USB 端），1 脚在天线端；4 个 Ø2.0 孔 (1.8,1.8)…(61.49,23.6)；USB-C ×1 宽 8.94、Y 8.24–17.18。
    用户实测：板 63.5x25.5；排针出厂焊好，两排外侧 23.7 / 内侧 22.3（中心距约 23.0，底板按 22.86）；塑料座 2.6，板下针长 7。
    T：WROOM-1U 本体 18x19.2x3.2 在 X 37.78–56.98、Y 3.7–21.7；IPEX 座约 (54.5,18.7)。
    原点=板底面 USB 端左角，X 沿板长朝天线端"""
    SPEC = dict(L=63.30, W=25.40, t=1.6, rows=(1.27, 24.13), n=22, x_pin0=5.05, pitch=2.54, pin_below=7.0, header_t=2.6,
                holes=((1.8, 1.8), (1.8, 23.6), (61.49, 1.8), (61.49, 23.6)), hole_d=2.0,
                usb=(7.4, 8.94, 3.2, 8.24), mod=(37.78, 3.7, 19.2, 18.0, 3.2), ipex=(54.5, 18.7))
    s = SPEC
    b = box(s["L"], s["W"], s["t"])
    for hx, hy in s["holes"]:
        b = b.cut(cyl(s["hole_d"] / 2, s["t"] + 0.02, hx, hy, -0.01, "Z"))
    for y in s["rows"]:
        b = b.union(box(s["n"] * s["pitch"], 2.5, s["header_t"], s["x_pin0"] - s["pitch"] / 2, y - 1.25, -s["header_t"]))   # 塑料座
        for k in range(s["n"]):
            b = b.union(box(0.64, 0.64, s["pin_below"], s["x_pin0"] + k * s["pitch"] - 0.32, y - 0.32, -s["pin_below"]))
    ul, uw, uh, uy = s["usb"]
    b = b.union(box(ul, uw, uh, -0.3, uy, s["t"]))                                            # USB-C
    mx, my, ml, mw, mh = s["mod"]
    b = b.union(box(ml, mw, mh, mx, my, s["t"]))                                              # WROOM-1U
    ix, iy = s["ipex"]
    return b.union(cyl(1.3, 1.25, ix, iy, s["t"] + mh, "Z"))                                  # IPEX 座

def ds3231_module():
    """DS3231 RTC 模块（ZS-042 类）：板 38x22，带弯针总长 45，总高 14（用户实测）；
    纽扣电池座在板底、芯片在板顶、一端 6P 弯针（布局 T）。原点=板底面左前角，X 沿板长朝弯针端"""
    SPEC = dict(L=38.0, W=22.0, t=1.6, L_pins=45.0, H=14.0, bat_d=20.0)
    s = SPEC
    zb = s["H"] - 8.0                                                                        # 板底离包络底 6（电池座）
    m = box(s["L"], s["W"], s["t"], 0, 0, zb)
    m = m.union(cyl(s["bat_d"] / 2, zb, s["L"] / 2 - 4, s["W"] / 2, 0, "Z"))                 # 电池座
    m = m.union(box(10.5, 7.6, 2.5, 8, 4, zb + s["t"])).union(box(5, 4, 1.5, 22, 14, zb + s["t"]))   # DS3231、AT24C32
    m = m.union(box(2.5, 15.24, 2.5, s["L"] - 2.5, (s["W"] - 15.24) / 2, zb + s["t"]))       # 弯针塑料座
    for k in range(6):
        m = m.union(box(s["L_pins"] - s["L"] + 2.5, 0.64, 0.64, s["L"] - 2.5, (s["W"] - 12.7) / 2 + k * 2.54 - 0.32, zb + s["t"] + 0.9))
    return m.union(box(4, 15, s["H"] - zb - s["t"], 1, (s["W"] - 15) / 2, zb + s["t"]))     # 另一端 6P 直针（到总高 14）

def rpi_pico():
    """Raspberry Pi Pico（RP2040）。SRC: datasheets.raspberrypi.com Pico-R3-step.zip，板 51x21x1"""
    p = V.rot(V.rot(V.load("rpi_pico/Pico-R3.step"), "X", 90), "Z", -90)
    return V.to_min(p, 0, 0)

def xl6009_module():
    """XL6009 可调升压模块（蓝色小板，43x21，T）：电感、两只电解、多圈电位器"""
    SPEC = dict(L=43.0, W=21.0, t=1.6, H=14.0)
    s = SPEC
    b = box(s["L"], s["W"], s["t"])
    for x, y in ((2.5, 2.5), (s["L"] - 2.5, s["W"] - 2.5)):
        b = b.cut(cyl(1.5, 3, x, y, -1))
    b = b.union(box(12, 12, 7, 15.5, 4.5, s["t"]))                                         # 电感
    for x in (7, s["L"] - 7):
        b = b.union(cyl(4, s["H"] - s["t"] - 2, x, s["W"] / 2, s["t"]))                    # 电解
    b = b.union(box(9.5, 4.8, 10, 28, 1, s["t"]))                                          # 3296 电位器
    return b.union(box(10, 9, 4.5, 28, 8.5, s["t"]))                                       # TO-263

def max6921_soic28():
    """MAX6921（SOIC-28W，若买到的是 PLCC 封装需换模型）。SRC: KiCad packages3D SOIC-28W_7.5x17.9mm_P1.27mm"""
    return V.load("kicad_extra/SOIC-28W_7.5x17.9mm_P1.27mm.step")

def buzzer_12mm():
    """Ø12 直插蜂鸣器。SRC: KiCad packages3D Buzzer_12x9.5RM7.6（盖革板自带蜂鸣器型号定了再换）"""
    return V.load("kicad_extra/Buzzer_12x9.5RM7.6.step")

def electret_mic_czn15e():
    """CZN-15E 驻极体麦克风（用户已有）：外壳 Ø9.7 × 6.7（T，按常见 Ø10×7 规格，到手实测），正面拾音孔 Ø2，背面两根引线 Ø0.6 × 8、间距 2.5（T）
    原点 = 背面中心，拾音面朝 +Z"""
    SPEC = dict(D=9.7, H=6.7, hole_d=2.0, lead_d=0.6, lead_L=8.0, lead_dx=2.5)
    s = SPEC
    m = cyl(s["D"] / 2, s["H"]).cut(cyl(s["hole_d"] / 2, 1.0, 0, 0, s["H"] - 0.5))
    for sx in (-1, 1):
        m = m.union(cyl(s["lead_d"] / 2, s["lead_L"], sx * s["lead_dx"] / 2, 0, -s["lead_L"]))
    return m

def usb_a_socket():
    """USB-A 母座（板装卧式）。SRC: KiCad packages3D USB_A_Molex_67643_Horizontal"""
    return V.load("kicad_extra/USB_A_Molex_67643_Horizontal.step")

def geiger_board():
    """盖革板（自设计占位，60x40，T）：555 升压 + 脉冲整形，四角 M3 孔"""
    L, W, t = 60.0, 40.0, 1.6
    b = box(L, W, t)
    for x, y in ((3.5, 3.5), (L - 3.5, 3.5), (3.5, W - 3.5), (L - 3.5, W - 3.5)):
        b = b.cut(cyl(1.6, 3, x, y, -1))
    b = b.union(box(9.8, 6.4, 3.5, 10, 8, t))                 # 555 (DIP-8)
    b = b.union(cyl(5, 10, 32, 12, t))                        # 电感
    b = b.union(box(7.5, 3.5, 9, 42, 9, t))                   # 高压瓷片电容
    return b.union(box(10.2, 8, 10, L - 14, W - 12, t))       # 管子接线端子

def x1_tablet_keyboard():
    """ThinkPad X1 Tablet 三代磁吸键盘：平放在桌面，顶边为磁吸连接带。宽 300（用户量得），其余按 13 寸机身估（T）"""
    SPEC = dict(W=300.0, D=226.0, t=5.0, hinge=12.0)
    s = SPEC
    k = box(s["W"], s["D"] - s["hinge"], s["t"]).edges("|Z").fillet(6)
    k = k.union(box(s["W"] - 20, s["hinge"], 2.5, 10, s["D"] - s["hinge"], 0))            # 连接带（触点在其后沿）
    k = k.cut(box(s["W"] - 16, 105, 0.8, 8, 95, s["t"] - 0.8))                            # 键区
    return k.cut(box(100, 55, 0.4, (s["W"] - 100) / 2, 22, s["t"] - 0.4))                 # 触摸板

def tube_6e2():
    """6E2（北京产，= EM87）侧视条形调谐指示管：玻壳 Ø22.2（T，按 EM8x 系列资料最大值，未实测），总高 62（含排气尖、不含插针，用户实测 2026-10-20），顶部圆顶 + 排气尖（T）
    冷态电阻（用户实测）：4–5 脚灯丝 2.98 Ω；2、6、8 脚管内相连（都带阳极 250 V）
    9 脚小型管（noval）：针圆 Ø11.89（C），10 等分缺 1 位，针 Ø1 x 6（T）；荧光条长约 39，上端离玻壳底面 48.3，即约 z 9.3..48.3（用户实测）
    原点=玻壳底部中心，Z 向上，针向 -Z；缺口（空针位）在 +X，底视图从缺口起顺时针为 1–9 脚（俯视即逆时针），荧光屏正对 7 脚"""
    SPEC = dict(D=22.2, L=59.0, dome_r=7.0, tip=(3.0, 4.0), pcd=11.89, pin_d=1.0, pin_L=6.0)
    s = SPEC
    g = cyl(s["D"] / 2, s["L"]).edges(">Z").fillet(s["dome_r"])
    g = g.union(cyl(s["tip"][0], s["tip"][1], 0, 0, s["L"] - 1))
    for k in range(1, 10):                                     # k 号脚：俯视从 +X 缺口逆时针 36°·k
        a = math.radians(36 * k)
        g = g.union(cyl(s["pin_d"] / 2, s["pin_L"], s["pcd"] / 2 * math.cos(a), s["pcd"] / 2 * math.sin(a), -s["pin_L"]))
    return g

def noval_socket():
    """9 脚小型管座（用户已有的杏仁形带耳款）：本体按 Ø21.6 x 10；两耳沿 Y（与缺口 +X 垂直），耳到耳 34，耳孔 Ø3.6 孔距 28（实测）；
    耳厚 1、耳宽 8、耳在本体底面（T）；焊片按剪短后 3.6 画（板厚 1.6 + 板下 ≤2）
    原点=管座顶面中心（管底贴此面），本体向 -Z"""
    SPEC = dict(D=21.6, H=10.0, hole_d=4.0, pcd=11.89, pin_L=3.6, ear=(34.0, 8.0, 1.0), ear_hole=(28.0, 3.6))   # 焊片焊完剪短：板下 ≤2
    s = SPEC
    k = cyl(s["D"] / 2, s["H"], 0, 0, -s["H"]).cut(cyl(s["hole_d"] / 2, s["H"] + 2, 0, 0, -s["H"] - 1))
    el, ew, et = s["ear"]
    k = k.union(box(ew, el, et, -ew / 2, -el / 2, -s["H"]).edges("|Z").fillet(ew / 2 - 0.01))
    for sy in (-1, 1):
        k = k.cut(cyl(s["ear_hole"][1] / 2, et + 2, 0, sy * s["ear_hole"][0] / 2, -s["H"] - 1))
    for i in range(1, 10):                                     # 缺口在 +X，与 tube_6e2 一致
        a = math.radians(36 * i)
        k = k.union(box(0.8, 0.8, s["pin_L"], s["pcd"] / 2 * math.cos(a) - 0.4, s["pcd"] / 2 * math.sin(a) - 0.4, -s["H"] - s["pin_L"]))
    return k

def lrs200_24():
    """明纬 LRS-200-24 开关电源（参数化包络）：外形 215x115x30（C，规格书），端子台在 +X 端顶面凹槽里（位置/尺寸 T）
    原点 = 底面左前角，X 长、Y 宽、Z 向上"""
    SPEC = dict(L=215.0, W=115.0, H=30.0, term=(16.0, 100.0, 12.0))
    s = SPEC
    L, W, H = s["L"], s["W"], s["H"]
    tx, ty, tz = s["term"]
    b = box(L, W, H).cut(box(tx, ty, tz + 1, L - tx - 2, (W - ty) / 2, H - tz))        # 端子凹槽
    b = b.union(box(tx - 4, ty - 6, tz - 2, L - tx, (W - ty) / 2 + 3, H - tz))           # 端子台
    for k in range(10):                                                                  # 散热孔示意（顶面）
        b = b.cut(box(2.0, W - 30, 1.0, 30 + k * 14, 15, H - 0.5))
    return b
