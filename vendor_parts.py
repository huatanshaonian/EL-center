"""
MIS-01 —— 厂家 / 开源库 STEP 模型的加载与对齐
原始文件放在 step/vendor/<来源>/ 下（不改动），这里只做“读入 → 旋转平移到 parts.py 的局部坐标约定”。
每个函数的 SRC 注释记录模型来源；对齐量都是对下载到的文件实测得到的，换了文件版本需要重新核对。
"""
import os
import cadquery as cq

VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "step", "vendor")
_cache = {}

def load(rel):
    """读入 step/vendor 下的 STEP，返回只含一个 Compound 的 Workplane（保持原始坐标）"""
    if rel not in _cache:
        s = cq.importers.importStep(os.path.join(VENDOR, rel))
        bodies = s.solids().vals() or s.shells().vals()      # 个别厂家文件只有曲面壳
        _cache[rel] = cq.Workplane("XY").newObject([cq.Compound.makeCompound(bodies)])
    return _cache[rel]

def compound(*shapes):
    """把若干 Workplane 合成一个 Compound（不做布尔运算）"""
    return cq.Workplane("XY").newObject([cq.Compound.makeCompound([v for s in shapes for v in s.vals()])])

def rot(shape, axis, ang):
    ax = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[axis]
    return shape.rotate((0, 0, 0), ax, ang)

def to_min(shape, x=None, y=None, z=None):
    """把包围盒最小角移到给定坐标；为 None 的轴不动"""
    bb = shape.val().BoundingBox()
    return shape.translate((0 if x is None else x - bb.xmin,
                            0 if y is None else y - bb.ymin,
                            0 if z is None else z - bb.zmin))

# ---------------------------------------------------------------- 1. 核心器件
def tang20k_core():
    """Tang Primer 20K 核心板。SRC: Sipeed 下载站 08_Dimensions/CoreModule/3D (3690)
    板 67.6x30x1.0，底面 Z=0（背面元件到 Z=-1.65），金手指在 Y=0 边"""
    return load("sipeed_tang20k/Tang_Primer_20K_3690_STEP/STEP/Tang_Primer_20K_3690.step").translate((33.8, 15.0, 0))

def tang20k_dock():
    """Tang Primer 20K Dock（模型内已含插好的核心板）。SRC: Sipeed 下载站 08_Dimensions/Dock/3D_Model (3713)
    板 95x73x1.6，4xM2.5 孔距 87x65；转 180° 使 HDMI/RJ45/Type-C 一侧朝 +Y（RJ45 伸出板边 2.7）"""
    d = load("sipeed_tang20k/Tang_Primer_20K_Dock_3713_STEP/Tang_Primer_20K_Dock_3713.step")
    return rot(d, "Z", 180).translate((95.0, 73.0, 0))

def in14():
    """IN-14 辉光管：玻壳 Ø18x52.5（含顶尖），引线伸出 12.8。SRC: github danpham/nixie_clock NX-SZP-IN14-v01.STEP
    原点=玻壳底部中心，Z 向上，引线向 -Z"""
    return rot(load("in14/danpham_NX-SZP-IN14-v01.STEP"), "X", 90).translate((0, 0, 26.25))

def iv18():
    """IV-18 VFD：玻壳 Ø19x108 + 排气尖到 115，引脚根 4.2。SRC: github pondahai/VFD_IV_18 IV-18.step
    原点=引线端玻壳中心，管轴沿 +X"""
    return rot(load("iv18/pondahai_IV-18.step"), "Y", -90)

def dip16():
    """DIP-16 W7.62。SRC: KiCad packages3D Package_DIP.3dshapes/DIP-16_W7.62mm.step
    KiCad 原点在 1 脚、管体沿 -Y；转到长边沿 X，两排脚在 Y=0 / 7.62，Z=0 为 PCB 面"""
    return rot(load("kicad/DIP-16_W7.62mm.step"), "Z", 90).translate((0.76, 0, 0))

# ---------------------------------------------------------------- 2. 电源
def lrs150_24():
    """明纬 LRS-150（各电压共用外壳）。SRC: meanwell.com LRS-150-3D.zip
    159x97x30，底板在 Z=0，端子台在 +X 端"""
    return to_min(load("meanwell_LRS-150/LRS-150(230808).stp"), 0, 0, 0)

def _nid(rel):
    """NID 系列原模型平放（PCB 在 XY，针沿 -Y）；立起来：长沿 X、厚沿 Y、针沿 -Z，针根在 Z=0"""
    return to_min(rot(load(rel), "X", 90), y=0)

def nid100_05():
    """明纬 NID100。SRC: meanwell.com NID100-3D.zip（51.2x12x27.1 + 针 4.5）"""
    return _nid("meanwell_NID100/NID100.stp")

def nid65_12():
    """明纬 NID65。SRC: meanwell.com NID65-3D.zip（50.9x9.7x26 + 针 4.5）"""
    return _nid("meanwell_NID65/NID65-20241008.stp")

# ---------------------------------------------------------------- 3. 机械
def corner_bracket_2020():
    """2020 角码 17 宽、两腿各 20，带 1 mm 定位凸台。SRC: FreeCAD-library Mechanical Parts/Mountings/Corner
    竖腿贴 Y=0（凸台伸到 Y=-1），横腿贴 Z=0（凸台伸到 Z=-1），在 20 宽内居中（X 1.5..18.5）"""
    return rot(load("freecad_library/2020_corner_bracket-Corner.step"), "Z", 180).translate((18.5, 0, 0))

def tnut_m4_slot6():
    """2020 槽 6 滑入式 M4 T 螺母。SRC: FreeCAD-library Mechanical Parts/Fasteners/T-nuts"""
    return to_min(load("freecad_library/TNut_2020_Slot6_Sliding_M4.step"), z=0)

def ec11():
    """Alps EC11E 立式带开关，轴长 20（自本体顶面）。SRC: tech.alpsalpine.com EC11E15244G1 的 3D CAD (EC11E-05SW)
    原点=面板安装面（本体顶面）中心，轴沿 -Y；旋钮厂家模型不含，仍为参数化 Ø18x15"""
    e = load("ec11/EC11E-05SW.STEP").translate((-0.21, -0.07, -16.29))
    knob = cq.Workplane("XZ").circle(9).extrude(15).mirror("XZ").translate((0, -22, 0)).edges("<Y").fillet(1.5)
    return compound(rot(e, "X", 90), knob)

def pushbutton_16():
    """Ø16 金属按钮（带灯环、螺母）。SRC: Adafruit_CAD_Parts "916 metal button"
    原点=面板前表面中心，头部在 -Y（高 1.5），螺母按 2 mm 面板位于 Y=2..5.3，端子到 Y=35.7"""
    return rot(load("pushbutton_16/916_Metal_Button.step"), "X", 90)

def sma_bulkhead():
    """SMA 后装穿墙母座。SRC: coax-connectors.com 30-266-D3-HA（厂家文件是曲面模型，不是实体）
    原点=面板背面中心，螺纹/垫圈/螺母朝 -Y，焊杯端朝 +Y；法兰肩位置按模型里首个垫圈起点 Z=7.3 估计"""
    return rot(load("sma_bulkhead/30-266-D3-HA.step").translate((0, 0, -7.3)), "X", 90)

def fan(size=60, t=15):
    """轴流风扇，框体 Y=0..t、X/Z 居中（引线等凸出框体约 2 mm）。SRC: sameskydevices.com CFM-6015V-147-342 / CFM-4010V-070-273"""
    rel = {(60, 15): "fan_6015/Same_Sky_CFM-6015V-147-342.step", (40, 10): "fan_4010/Same_Sky_CFM-4010V-070-273.step"}[(size, t)]
    return load(rel)
