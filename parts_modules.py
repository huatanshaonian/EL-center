"""
MIS-01 —— 新增的电子模块与外设（仪器层 / 输入层）
坐标同 parts.py：PCB / 模块类以板底面左前角为原点，X 长、Y 宽、Z 向上；管子类轴沿 +X。
C=已确认(原厂/可靠资料)  T=暂定(待实物测绘)
"""
import math
import cadquery as cq
from parts import box, cyl
import vendor_parts as V

def sbm20():
    """SBM-20 盖革管：Ø11 x 108（C，常见资料），两端金属帽（T）。原点=一端中心，管轴沿 +X"""
    SPEC = dict(D=11.0, L=108.0, cap_L=8.0, cap_D=10.0)
    s = SPEC
    b = cyl(s["D"] / 2, s["L"] - 2 * s["cap_L"], s["cap_L"], 0, 0, "X")
    for x in (0, s["L"] - s["cap_L"]):
        b = b.union(cyl(s["cap_D"] / 2, s["cap_L"], x, 0, 0, "X"))
    return b

def esp32_devkitc():
    """ESP32-DevKitC（38 脚）：板 54.4x27.9（T，按 V4 资料），模组用 KiCad 的 ESP32-WROOM-32E 实体，排针朝下"""
    SPEC = dict(L=54.4, W=27.9, t=1.6, row=25.4, n=19, pitch=2.54, pin_below=8.5, ant_overhang=6.0)
    s = SPEC
    b = box(s["L"], s["W"], s["t"])
    x0 = (s["L"] - (s["n"] - 1) * s["pitch"]) / 2
    for y in ((s["W"] - s["row"]) / 2, (s["W"] + s["row"]) / 2):
        b = b.union(box((s["n"]) * s["pitch"], 2.5, 2.5, x0 - s["pitch"] / 2, y - 1.25, -2.5))
        for k in range(s["n"]):
            b = b.union(box(0.64, 0.64, s["pin_below"], x0 + k * s["pitch"] - 0.32, y - 0.32, -s["pin_below"]))
    b = b.union(box(7.5, 5.5, 2.6, -1.0, s["W"] / 2 - 2.75, s["t"]))                       # micro-USB
    mod = V.rot(V.load("kicad_extra/ESP32-WROOM-32E.step"), "Z", -90)                      # 天线端朝 +X
    mod = mod.translate((s["L"] - 12.75 + s["ant_overhang"], s["W"] / 2, s["t"]))
    return V.compound(b, mod)

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
    """6E2（EM84 类）侧视条形调谐指示管：玻壳 Ø22.2（C，EM84 资料最大值）x 66（T），顶部圆顶 + 排气尖（T）
    9 脚小型管（noval）：针圆 Ø11.89（C），10 等分缺 1 位，针 Ø1 x 6（T）；荧光条在侧面中部约 z 20..50（T）
    原点=玻壳底部中心，Z 向上，针向 -Z"""
    SPEC = dict(D=22.2, L=66.0, dome_r=7.0, tip=(3.0, 4.0), pcd=11.89, pin_d=1.0, pin_L=6.0)
    s = SPEC
    g = cyl(s["D"] / 2, s["L"]).edges(">Z").fillet(s["dome_r"])
    g = g.union(cyl(s["tip"][0], s["tip"][1], 0, 0, s["L"] - 1))
    for k in range(9):
        a = math.radians(36 * k)
        g = g.union(cyl(s["pin_d"] / 2, s["pin_L"], s["pcd"] / 2 * math.cos(a), s["pcd"] / 2 * math.sin(a), -s["pin_L"]))
    return g

def noval_socket():
    """9 脚小型管座（noval / B9A，PCB 安装）占位：Ø22 x 10、中心孔 Ø4、焊针 4.5（全部 T）
    原点=管座顶面中心（管底贴此面），本体向 -Z"""
    SPEC = dict(D=22.0, H=10.0, hole_d=4.0, pcd=11.89, pin_L=4.5)
    s = SPEC
    k = cyl(s["D"] / 2, s["H"], 0, 0, -s["H"]).cut(cyl(s["hole_d"] / 2, s["H"] + 2, 0, 0, -s["H"] - 1))
    for i in range(9):
        a = math.radians(36 * i)
        k = k.union(box(0.8, 0.8, s["pin_L"], s["pcd"] / 2 * math.cos(a) - 0.4, s["pcd"] / 2 * math.sin(a) - 0.4, -s["H"] - s["pin_L"]))
    return k
