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
STANDOFF = 6                             # M2.5 铜柱（Pi、Dock 板底都有元件/焊脚）
Z_PCB = Z_PLATE_TOP + STANDOFF           # 两块板板底 z 270
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
AD_Z = HDMI_Z - PLUG_ZC                  # 小板板底世界 z 274.6
FPC_YC, FPC_H = 17, 4.4                  # 立式座中心 y、高（STEP 里座子 z 1.6–6.0；规格书写 5.65，以实物为准）
FFC_LEN, FFC_W = 200, 10.6               # 20 cm 同向排线（C11107）


def _pi_and_dock():
    pi = P.orangepi4().rotate((0, 0, 0), (0, 0, 1), 180).translate((PI_XR, PI_YR, Z_PCB))
    add("OrangePi_4", pi, "opi", "computer")
    for hx, hy in ((2.86, 2.61), (87.97, 2.61), (2.86, 53.06), (87.97, 53.06)):
        add("standoff_M2.5x6_Pi", P.standoff_m3(STANDOFF).translate((PI_XR - hx, PI_YR - hy, Z_PLATE_TOP)), "brass", "computer")
    add("Tang20K_Dock", P.tang20k_dock().translate((DOCK_X0, DOCK_Y0, Z_PCB)), "pcb_g", "computer")
    for hx, hy in ((4, 4), (91, 4), (4, 69), (91, 69)):
        add("standoff_M2.5x6_Dock", P.standoff_m3(STANDOFF).translate((DOCK_X0 + hx, DOCK_Y0 + hy, Z_PLATE_TOP)), "brass", "computer")


def ffc_arch(x0, x1, z0, length=FFC_LEN, w=FFC_W, t=0.3, y=AD_Y + FPC_YC):
    """排线：两端从 FPC 座顶 z0 竖直向上，顶上半圆连通（XZ 平面），返回 (形体, 竖直段高, 拱顶 z)"""
    r = (x1 - x0) / 2
    h = (length - 2 * 4 - math.pi * r) / 2          # 两头各插进座里约 4
    xc, zc = (x0 + x1) / 2, z0 + h
    up = P.box(t, w, h, x0 - t / 2, y - w / 2, z0).union(P.box(t, w, h, x1 - t / 2, y - w / 2, z0))
    ring = (cq.Workplane("XZ").center(xc, zc).circle(r + t / 2).circle(r - t / 2).extrude(w / 2, both=True)
            .translate((0, y, 0)))
    ring = ring.intersect(P.box(2 * r + 2, w + 2, r + 2, xc - r - 1, y - w / 2 - 1, zc))
    return up.union(ring), h, zc + r


def build():
    _pi_and_dock()
    for tag, x in (("Pi", PI_HDMI_X), ("Dock", DOCK_HDMI_X)):
        add(f"HDMI-{tag.upper()}_D1", V.load_abs(AD_STEP[tag]).translate((x, AD_Y, AD_Z)), "pcb_b", "computer")
    ffc, _, _ = ffc_arch(PI_HDMI_X, DOCK_HDMI_X, AD_Z + 1.6 + FPC_H)
    add("FFC_20P_200mm", ffc, (0.85, 0.7, 0.35, 1), "computer")
