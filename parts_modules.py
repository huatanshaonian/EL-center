"""
MIS-01 —— 新增的电子模块与外设（仪器层 / 输入层）
坐标同 parts.py：PCB / 模块类以板底面左前角为原点，X 长、Y 宽、Z 向上；管子类轴沿 +X。
C=已确认(原厂/可靠资料)  T=暂定(待实物测绘)
"""
import math
import cadquery as cq
from parts import box, cyl
import vendor_parts as V

def j305(L=111.0):
    """J305β 盖革管：Ø11 x 111（T，卖家/ESPHome 资料，到手实测），两端金属帽（T）。原点=一端中心，管轴沿 +X"""
    SPEC = dict(D=11.0, L=L, cap_L=8.0, cap_D=10.0)
    s = SPEC
    b = cyl(s["D"] / 2, s["L"] - 2 * s["cap_L"], s["cap_L"], 0, 0, "X")
    for x in (0, s["L"] - s["cap_L"]):
        b = b.union(cyl(s["cap_D"] / 2, s["cap_L"], x, 0, 0, "X"))
    return b

def esp32s3_dev_kit():
    """微雪 Waveshare ESP32-S3-DEV-KIT（-U 外接天线版，模组 ESP32-S3-WROOM-1U-N16R8），预焊排针朝下。
    C（微雪官方外形尺寸图 2026-01-10）：板 63.30x25.40x1.6；2x22 针 2.54，两排 Y=1.27/24.13（排距 22.86），
    首针 X=5.05（USB 端），1 脚在天线端；4 个 Ø2.0 孔 (1.8,1.8)…(61.49,23.6)；USB-C ×1 宽 8.94、Y 8.24–17.18。
    T：WROOM-1U 本体 18x19.2x3.2 在 X 37.78–56.98、Y 3.7–21.7；IPEX 座约 (54.5,18.7)；板下排针约 8.5。
    原点=板底面 USB 端左角，X 沿板长朝天线端"""
    SPEC = dict(L=63.30, W=25.40, t=1.6, rows=(1.27, 24.13), n=22, x_pin0=5.05, pitch=2.54, pin_below=8.5,
                holes=((1.8, 1.8), (1.8, 23.6), (61.49, 1.8), (61.49, 23.6)), hole_d=2.0,
                usb=(7.4, 8.94, 3.2, 8.24), mod=(37.78, 3.7, 19.2, 18.0, 3.2), ipex=(54.5, 18.7))
    s = SPEC
    b = box(s["L"], s["W"], s["t"])
    for hx, hy in s["holes"]:
        b = b.cut(cyl(s["hole_d"] / 2, s["t"] + 0.02, hx, hy, -0.01, "Z"))
    for y in s["rows"]:
        b = b.union(box(s["n"] * s["pitch"], 2.5, 2.5, s["x_pin0"] - s["pitch"] / 2, y - 1.25, -2.5))   # 塑料座
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
    """Ø12 直插蜂鸣器。SRC: KiCad packages3D Buzzer_12x9.5RM7.6"""
    return V.load("kicad_extra/Buzzer_12x9.5RM7.6.step")

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
    """6E2（EM84 类）侧视条形调谐指示管：玻壳 Ø22.2（C，EM84 资料最大值），总高 62（含排气尖、不含插针，用户实测 2026-10-20），顶部圆顶 + 排气尖（T）
    9 脚小型管（noval）：针圆 Ø11.89（C），10 等分缺 1 位，针 Ø1 x 6（T）；荧光条在侧面中部约 z 20..50（T）
    原点=玻壳底部中心，Z 向上，针向 -Z"""
    SPEC = dict(D=22.2, L=59.0, dome_r=7.0, tip=(3.0, 4.0), pcd=11.89, pin_d=1.0, pin_L=6.0)
    s = SPEC
    g = cyl(s["D"] / 2, s["L"]).edges(">Z").fillet(s["dome_r"])
    g = g.union(cyl(s["tip"][0], s["tip"][1], 0, 0, s["L"] - 1))
    for k in range(9):
        a = math.radians(36 * k)
        g = g.union(cyl(s["pin_d"] / 2, s["pin_L"], s["pcd"] / 2 * math.cos(a), s["pcd"] / 2 * math.sin(a), -s["pin_L"]))
    return g

def noval_socket():
    """9 脚小型管座（noval / B9A，PCB 安装）占位：Ø22 x 10、中心孔 Ø4、焊片按剪短后 3.6 画（板厚 1.6 + 板下 ≤2）（全部 T）
    原点=管座顶面中心（管底贴此面），本体向 -Z"""
    SPEC = dict(D=22.0, H=10.0, hole_d=4.0, pcd=11.89, pin_L=3.6)   # 焊片焊完剪短：板下 ≤2
    s = SPEC
    k = cyl(s["D"] / 2, s["H"], 0, 0, -s["H"]).cut(cyl(s["hole_d"] / 2, s["H"] + 2, 0, 0, -s["H"] - 1))
    for i in range(9):
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
