"""
MIS-01 电脑层（层板顶面 z 264）：Orange Pi 4、Tang Primer 20K Dock、HDMI 软排线两头小板（HDMI-PI / HDMI-DOCK D1）和排线。
**暂定布置（2026-10-21，待用户确认）**：两块板 HDMI 所在的边都朝后，口面都在 y 172.7，离后面板内侧（y 220）47 mm。
不贴层板后沿（y 198）放，是因为同一条边上还有直头的 DC 插头（Pi 4.0×1.7、Dock 5.5×2.1）和 Pi 耳机插头，要 40 mm 以上才弯得过来。
Pi 在左：网口/USB 朝左（−X），HDMI 长边朝后；Dock 在右，按厂家模型方向（HDMI/网口/DC 一侧朝 +Y）。
两块 HDMI 小板（mis-01-56，STEP 原点 = 板前沿中点，+Y 背离插头，顶层 +Z，只需平移）：C711355 夹板式公头水平插入（−Y），
梯形宽边在顶层一侧，与 Dock 插座宽边朝上一致；立式 20P 座 C11073 在板上 (0, 17)，长边沿 Y，排线竖直出座后在 XZ 平面里拱过去（不用折痕）。
插入深度按 Dock 3713 STEP：插座口面 y 73.7，壳内到 y 66.9 是插座本体，插头能进 6.8 mm；Pi 插座没有模型，按同样深度。
"""
import math
import cadquery as cq
import parts as P
import vendor_parts as V
from assembly_base import Z_SHELF, PLATE_T, add, place

Z_PLATE_TOP = Z_SHELF + PLATE_T          # 264
STANDOFF = 6                             # Dock：M2.5×6 铜柱（板底有焊脚）
Z_PCB = Z_PLATE_TOP + STANDOFF           # Dock 板底 z 270
PI_STANDOFF = 25                         # Pi：M2.5×25 铜柱。用户的 Pi 4 排针在板子背面朝下（2026-10-22），下面要插杜邦：
                                         # 排针塑料座 2.5 + 插头 14 → 插头下沿离板底 16.5，再留约 8 让线弯过去
Z_PCB_PI = Z_PLATE_TOP + PI_STANDOFF     # Pi 板底 z 289（比 Dock 高 19）
Y_PORT = 172.7                           # 两个 HDMI 口面
HDMI_Z = Z_PCB + 5.375                   # 插口中心高 275.4（Dock STEP 口面截面：外壳 z 2.75–8.0，宽边朝上；Pi 按同规格估计）

# Orange Pi 4：模型原点（FPC 端 × HDMI 长边）放在 (PI_XR, PI_YR)，绕 Z 转 180°
PI_RJ45_X = 70                           # 网口端板边 x（USB 插头向左还要约 45）
PI_XR = PI_RJ45_X + 91                   # 161
PI_YR = Y_PORT - 2.85                    # HDMI 长边板边 y 169.85
PI_HDMI_X = PI_XR - (17.13 + 32.13) / 2  # 136.37

# Dock：板左前角放在 (DOCK_X0, DOCK_Y0)
DOCK_X0 = 170
DOCK_Y0 = Y_PORT - 73.7                  # 99.0
DOCK_HDMI_X = DOCK_X0 + 32.4             # 202.4

# HDMI 小板 STEP（约 7 / 12 MB，不进 git）
AD_DIR = "el_driver/HDMI_FPC_D1/制板文件/"
AD_STEP = {"Pi": AD_DIR + "HDMI-PI_D1.step", "Dock": AD_DIR + "HDMI-DOCK_D1.step"}
PLUG_TIP, PLUG_ZC = -12.42, 0.73         # 小板坐标里插头壳前端 y、壳中心 z（壳 z −1.5..2.96）
INSERT = 6.8                             # 插入深度
AD_Y = Y_PORT - INSERT - PLUG_TIP        # 小板原点（板前沿）世界 y 178.3
AD_Z = HDMI_Z - PLUG_ZC                  # Dock 端小板板底世界 z 274.6
AD_ZS = {"Pi": AD_Z + Z_PCB_PI - Z_PCB, "Dock": AD_Z}   # Pi 端跟着 Pi 抬高 19
FPC_YC, FPC_H = 17, 4.4                  # 立式座中心 y、高（STEP 里座子 z 1.6–6.0；规格书写 5.65，以实物为准）
FFC_LEN, FFC_W = 200, 10.6               # 20 cm 同向排线（C11107）


def _pi_and_dock():
    pi = P.orangepi4().rotate((0, 0, 0), (0, 0, 1), 180).translate((PI_XR, PI_YR, Z_PCB_PI))
    add("OrangePi_4", pi, "opi", "computer")
    for hx, hy in ((2.86, 2.61), (87.97, 2.61), (2.86, 53.06), (87.97, 53.06)):
        add("standoff_M2.5x25_Pi", P.standoff_m3(PI_STANDOFF).translate((PI_XR - hx, PI_YR - hy, Z_PLATE_TOP)), "brass", "computer")
    # 板底 26 针排针、3 针调试串口下插着的杜邦插头（占位：塑料座 2.5 下面 14 长）
    for tag, (hx0, hx1, hy0, hy1) in (("header", P.ORANGEPI4_HEADER), ("uart", P.ORANGEPI4_UART)):
        add(f"Dupont_on_Pi_{tag}", P.box(hx1 - hx0, hy1 - hy0 + 1, 14, PI_XR - hx1, PI_YR - hy1 - 0.5, Z_PCB_PI - 2.5 - 14), "dark", "computer")
    add("Tang20K_Dock", P.tang20k_dock().translate((DOCK_X0, DOCK_Y0, Z_PCB)), "pcb_g", "computer")
    for hx, hy in ((4, 4), (91, 4), (4, 69), (91, 69)):
        add("standoff_M2.5x6_Dock", P.standoff_m3(STANDOFF).translate((DOCK_X0 + hx, DOCK_Y0 + hy, Z_PLATE_TOP)), "brass", "computer")


def ffc_arch(x0, x1, z0, z1, length=FFC_LEN, w=FFC_W, t=0.3, y=AD_Y + FPC_YC):
    """排线：两端从 FPC 座顶（x0 处 z0、x1 处 z1）竖直向上，顶上半圆连通（XZ 平面），返回 (形体, (两段竖直高), 拱顶 z)"""
    r = (x1 - x0) / 2
    legs = length - 2 * 4 - math.pi * r                # 两头各插进座里约 4
    zc = (legs + z0 + z1) / 2                          # 两段竖直线顶端齐平
    h0, h1 = zc - z0, zc - z1
    assert h0 > 5 and h1 > 5, "排线不够长"
    xc = (x0 + x1) / 2
    up = P.box(t, w, h0, x0 - t / 2, y - w / 2, z0).union(P.box(t, w, h1, x1 - t / 2, y - w / 2, z1))
    ring = (cq.Workplane("XZ").center(xc, zc).circle(r + t / 2).circle(r - t / 2).extrude(w / 2, both=True)
            .translate((0, y, 0)))
    ring = ring.intersect(P.box(2 * r + 2, w + 2, r + 2, xc - r - 1, y - w / 2 - 1, zc))
    return up.union(ring), (h0, h1), zc + r


def build():
    _pi_and_dock()
    for tag, x in (("Pi", PI_HDMI_X), ("Dock", DOCK_HDMI_X)):
        add(f"HDMI-{tag.upper()}_D1", V.load_abs(AD_STEP[tag]).translate((x, AD_Y, AD_ZS[tag])), "pcb_b", "computer")
    ffc, _, _ = ffc_arch(PI_HDMI_X, DOCK_HDMI_X, AD_ZS["Pi"] + 1.6 + FPC_H, AD_ZS["Dock"] + 1.6 + FPC_H)
    add("FFC_20P_200mm", ffc, (0.85, 0.7, 0.35, 1), "computer")
    build_extras()


# ---------------------------------------------------------------- EL 接口板、Hub、Pi 散热（2026-10-22 暂定，待用户确认）
EL_IF_STEP = "el_driver/D1.3/制板文件/EL-IF_D1.3.step"          # EL-IF D1.3，100×100，原点 = 板左下角，元件最高 15.7；不进 git
EL_IF_XY = (160.0, 40.0)                                       # 板占 x 160–260、y 40–140（Dock 前半部上方）
EL_IF_STANDOFF = 10                                            # 吊在顶板下：M3×10 铜柱，元件朝下


def el_if():
    """EL 接口板吊在顶板下面（元件朝下）：离 Dock J5/J6/J14 近（PMOD 线 15 cm），离 EL 屏也近；
    在 HDMI 软排线拱顶（约 z 368）和 Pi 风扇上面，层板上已经放不下 100×100（Pi、Dock 占满）。顶板要按四角孔打 4 个 M3 孔。"""
    from assembly_base import H
    x0, y0 = EL_IF_XY
    zb = H - EL_IF_STANDOFF                                    # 板背面（原底面）z 410
    b = V.load_abs(EL_IF_STEP).rotate((0, 0, 0), (1, 0, 0), 180).translate((x0, y0 + 100, zb))
    add("EL-IF_D1.3", b, "pcb_g", "computer")
    for hx, hy in ((5, 5), (95, 5), (5, 95), (95, 95)):
        add("standoff_M3x10_ELIF", P.standoff_m3(EL_IF_STANDOFF).translate((x0 + hx, y0 + hy, zb)), "brass", "computer")


def usb_hub():
    """一分四 USB2.0 Hub 模块（用户已有，尺寸 T 按常见 70×30×12 估，到货实测）：电脑层前沿、Pi 前面，M3×6 铜柱"""
    add("USB_Hub_4port", P.box(70, 30, 12, 85, 40, Z_PLATE_TOP + 6), "module", "computer")


def pi_cooling():
    """RK3399 散热片 20×20×10（导热胶贴）+ 40×10 风扇（5 V）水平架在散热片上方往下吹；风扇用打印支架架在 Pi 两个安装孔的加长铜柱上（T）"""
    cx, cy = PI_XR - 41.0, PI_YR - 24.0                        # RK3399 中心（Pi 局部约 (41, 24)，Pi 绕 Z 转了 180°）
    z = Z_PCB_PI + 1.6 + 1.5                                   # 芯片顶面
    add("RK3399_heatsink_20x20", P.box(20, 20, 10, cx - 10, cy - 10, z), "alu", "computer")
    fan = V.fan(40, 10).rotate((0, 0, 0), (1, 0, 0), 90).translate((cx, cy, z + 10.5))
    add("Fan_40x10_Pi", fan, "dark", "computer")


def build_extras():
    el_if(); usb_hub(); pi_cooling()
