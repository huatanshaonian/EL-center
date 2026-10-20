"""
MIS-01 装配公共部分：整机尺寸、配色、零件表与放置工具（assembly.py / assembly_panel.py 共用）
全局坐标：X 向右(宽)、Y 由前向后(深)、Z 向上；竖直前面板外表面 Y=-2，框架前沿 Y=0。
"""
W, D, H = 320, 220, 420
Z_DECK = 90          # 管座甲板顶面（型材 70..90，板 90..92）
Z_SHELF = 260        # 电脑层（型材 240..260，板 260..262）
Z_SCREEN = 178       # EL 屏底边
PLATE_T = 4          # 层板厚度：橘红色电木板 4 mm（2026-10-20，原 2 mm 铝板）

C = dict(
    alu=(0.78, 0.79, 0.80, 1), dark=(0.16, 0.16, 0.17, 1), panel=(0.22, 0.22, 0.23, 1),
    glass_el=(0.25, 0.18, 0.08, 1), pcb_g=(0.05, 0.35, 0.15, 1), pcb_b=(0.08, 0.08, 0.1, 1),
    nixie=(1.0, 0.55, 0.15, 0.55), vfd=(0.35, 0.95, 0.8, 0.55), geiger=(0.6, 0.6, 0.62, 1),
    psu=(0.72, 0.74, 0.76, 1), module=(0.15, 0.15, 0.15, 1), acrylic=(0.75, 0.9, 1.0, 0.25),
    brass=(0.80, 0.65, 0.30, 1), chip=(0.07, 0.07, 0.07, 1), knob=(0.12, 0.12, 0.12, 1), opi=(0.05, 0.2, 0.5, 1),
    chin=(0.34, 0.34, 0.36, 1), guard=(0.70, 0.15, 0.12, 1), lamp=(1.0, 0.82, 0.48, 1), meter=(0.91, 0.89, 0.82, 1),
    eye=(0.30, 1.0, 0.45, 0.55), kbd=(0.10, 0.10, 0.11, 1), bakelite=(0.72, 0.30, 0.10, 1),
)

ITEMS = []   # (name, shape, color, group)

def place(shape, x=0, y=0, z=0, rot=()):
    for axis, ang in rot:
        ax = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[axis]
        shape = shape.rotate((0, 0, 0), ax, ang)
    return shape.translate((x, y, z))

def to_min(shape, x, y, z):
    """把形体包围盒最小角移到 (x,y,z)"""
    bb = shape.val().BoundingBox()
    return shape.translate((x - bb.xmin, y - bb.ymin, z - bb.zmin))

def add(name, shape, color, group):
    ITEMS.append((name, shape, C[color] if isinstance(color, str) else color, group))
