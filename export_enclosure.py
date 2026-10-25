"""外壳加工文件 → 外壳加工/（不进 git）
嘉立创钣金要折好弯的 3D STEP（自己展开，不收展开图），2D 图只作参考；平板件另给 DXF（板中面截面）。
每个零件：<名>.step、<名>.png（等轴图 + 标注），平板件加 <名>.dxf；另写 下单说明.txt（材料、表面处理、数量、压铆、接地点）。
运行：.venv/Scripts/python.exe -u export_enclosure.py
"""
import os
import cadquery as cq
import render as R
import assembly as A
import assembly_panel as AP
import assembly_shell as SH
import assembly_covers as ACV
import parts_dock as PD
from assembly_base import W, H, D, C, ITEMS

OUT = "外壳加工"


def _dxf(shape, name, to_xy):
    """平板件：先转到 XY 平面（to_xy），在板厚中间截一刀导出 DXF"""
    flat = to_xy(shape)
    bb = flat.val().BoundingBox()
    sec = flat.section((bb.zmin + bb.zmax) / 2)
    cq.exporters.export(sec, os.path.join(OUT, name + ".dxf"), exportType="DXF")


def _png(shape, name, title, labels, az=30, el=25, col=C["panel"]):
    R.render([(name, shape, col, "")], os.path.join(OUT, name + ".png"), az=az, el=el, title=title, size=(11, 9), labels=labels)


def parts():
    ITEMS.clear(); AP.front_panel(); AP.slant(); ITEMS.clear()          # 只为填 AP.FEATURES（前面板 / 斜面开孔）
    out = []
    fs = SH.front_shell()
    flange_pts = []
    for u in AP.FLANGE_SCREW_U:
        y, z = AP.slant_pt(u, AP.FLANGE_SCREW_T)
        flange_pts += [((1, y, z), "M3 压铆螺母孔 Ø4.2"), ((W - 1, y, z), "M3 压铆螺母孔 Ø4.2")]
    out.append(("前壳_front_shell", fs, "前壳：2 mm 5052，折 33°（内 R1.7）+ 斜面两侧 90° 翻边",
                flange_pts[:2] + [((W - 10, 0, 140), "接地点：此 M4 孔背面 Ø12 不涂层")], -35, 20, None))
    ct = SH.chin_tray()
    out.append(("下巴托_chin_tray", ct, "下巴托：2 mm 5052，底板 + 两侧板（90°）+ 后翻边（90°），内 R1.7",
                [((-2, 35, 80), "M4 ×6 / 侧（锁型材）"), ((-2, 50, 35), "喇叭网 Ø3"), ((W / 2, -1, 10), "M4 ×3；中间孔背面 Ø12 不涂层（接地）")], -35, 25, None))
    out.append(("IEC小板_iec_plate", A.iec_plate(), "IEC 小板：2 mm 5052 平板 110×110",
                [((276, D, 54), "IEC C14 开孔 28×60"), ((310, D, 10), "M4 ×3；右下孔背面 Ø12 不涂层（接地）")], 150, 15,
                lambda s: s.rotate((0, 0, 0), (1, 0, 0), 90)))
    out.append(("全高侧板_side_cover_x2", ACV.side_cover(), "全高侧板（可选，左右同一零件 ×2）：2 mm 5052 平板",
                [((0, 210, 350), "M4 ×8"), ((0, 150, 45), "通风长孔")], 90, 10, lambda s: s.rotate((0, 0, 0), (0, 1, 0), 90)))
    out.append(("背板_rear_cover", ACV.rear_cover(A.IEC_PLATE), "背板（可选）：2 mm 5052 平板，右下角让出 IEC 小板",
                [((100, D, 340), "Ø56 通风孔 ×2"), ((10, D, 210), "M4 ×7")], 180, 10, lambda s: s.rotate((0, 0, 0), (1, 0, 0), 90)))
    out.append(("键盘座_keyboard_dock", PD.keyboard_dock(), "键盘座：嘉立创 3D 打印尼龙 MJF（黑），长 320",
                [((0, 0, 0), "槽面（键盘连接条吸在这里）"), ((PD.SPEC["tongue_x"][0], 2, PD.SPEC["H"] + 4), "舌片 Ø4 ×3（压 M3 热熔铜螺母）"),
                 ((PD.SPEC["L"] / 2, 5, 8), "两端 Ø4 ×2 / 端（深 7，压 M3 热熔铜螺母）"),
                 ((-PD.SPEC["cover_screw_x"], PD.SPEC["D"], PD.SPEC["cover_screw_z"][1]), "背面 Ø1.7 ×4（M2 自攻，锁背盖）")], 210, 30, None))
    out.append(("键盘座背盖_dock_cover", PD.keyboard_dock_cover(), f"键盘座背盖：尼龙 MJF 打印 {PD.SPEC['cover_t']:g} mm",
                [((0, PD.SPEC["D"], 4), "排线出线口"), ((PD.SPEC["cover_screw_x"], PD.SPEC["D"], PD.SPEC["cover_screw_z"][1]), "M2 过孔 Ø2.4 ×4")], 30, 30, None))
    return out


NOTE = """MIS-01 外壳加工下单说明（{date}，由 export_enclosure.py 生成）

通用：嘉立创钣金（jlccnc / 嘉立创下单助手 → 钣金），材料 5052 铝，厚 2.0 mm；上传 .step（折好弯的 3D），.png 只作参考。
      2 mm 板外 R 3.7（内 R 1.7），模型已按此建；孔径 M4 Ø4.5、M3 Ø3.4、压铆 M3 Ø4.2。
      表面处理二选一：阳极氧化（黑 / 银，质感好）或喷塑（哑光）。要丝印字的话另出丝印图（还没出）。
      **接地点**：每个零件标了一个 M4 孔，孔背面 Ø12 圆内不要涂层（下单备注写“此处遮蔽”，做不了就装的时候刮掉）。

1. 前壳_front_shell.step ×1：前面板 324×332 + 斜面 320×{slant:g}，折 33°；斜面两侧往里 90° 翻边。
   压铆：两侧翻边各 2 个 M3 压铆螺母（CLS-M3-1 或同等，孔 Ø4.2），从翻边外侧（贴下巴托侧板那面）压入，共 4 个。
2. 下巴托_chin_tray.step ×1：底板 + 两侧板 + 后翻边，三道 90° 折弯。两侧板各 6 个 M4、2 个 M3（锁斜面翻边）、2 个 M3（锁键盘座两端）、喇叭网 Ø3；
   底板 4 个 Ø2.4（M2×5 铜柱，装键盘转接小板 KBD-ADAPT）；后翻边右段降低（让开最下排按钮焊片），以 STEP 为准。
3. IEC小板_iec_plate.step / .dxf ×1：110×110 平板。
4. 全高侧板_side_cover_x2.step / .dxf ×2（可选，左右是同一个零件）：222×428 平板，带通风长孔。
5. 背板_rear_cover.step / .dxf ×1（可选）：320×420 平板，右下角缺口让 IEC 小板。
6. 键盘座_keyboard_dock.step ×1：嘉立创 3D 打印，尼龙 MJF（PA12，染黑），一整件打（长 320）。
   孔：舌片 3 个、两端各 2 个 Ø4.0（两端孔深 7），装配时用烙铁压 M3×4 热熔铜螺母；两端块背面各 2 个 Ø1.7（M2 自攻，锁背盖）。
   上传 .stl（嘉立创建议 STL）。要 CNC 询价的话用 键盘座_CNC询价/ 里的同名 STEP + PDF（POM，7 个孔直接攻 M3），由 fig_dock_drawing.py 生成。嘉立创要求壁厚 > 1.2、最薄处 ≥ 0.8：本件槽底板 0.8、磁铁开孔横筋 0.8 正好在下限。
7. 键盘座背盖_dock_cover.step / .stl ×1：和键盘座一起尼龙 MJF 打印，{cover_t:g} mm 薄片，全长 320；4 颗 M2×6 自攻锁到两端块；
   下沿中间出线口 {slot_w:g} 宽，01AY247 排线从这里出来接下巴托底板上的 KBD-ADAPT。
8. 喇叭不用支架：5151 腔体喇叭耳朵朝上下，M3 螺丝 + 2020 用 M3 锤头螺母直接锁上下两根 Y 梁内侧槽。
"""


def main():
    import datetime
    os.makedirs(OUT, exist_ok=True)
    for name, shp, title, labels, az, el, to_xy in parts():
        cq.exporters.export(shp, os.path.join(OUT, name + ".step"))
        if "键盘座" in name:                      # 3D 打印件：嘉立创 3D 打印建议传 STL（细分到 0.02 mm，圆孔不出棱）
            cq.exporters.export(shp, os.path.join(OUT, name + ".stl"), tolerance=0.02, angularTolerance=0.1)
        if to_xy:
            _dxf(shp, name, to_xy)
        col = C["dark"] if "键盘座" in name else C["panel"]
        _png(shp, name, title, labels, az, el, (0.55, 0.57, 0.6, 1) if col == C["panel"] else col)
        bb = shp.val().BoundingBox()
        print(f"{name}: {bb.xlen:.1f}×{bb.ylen:.1f}×{bb.zlen:.1f}  solids={len(shp.solids().vals())}", flush=True)
    with open(os.path.join(OUT, "下单说明.txt"), "w", encoding="utf-8") as f:
        f.write(NOTE.format(date=datetime.date.today().isoformat(), slant=AP.SLANT_L, cover_t=PD.SPEC["cover_t"],
                            slot_w=PD.SPEC["cable_slot"][0]))
    print("saved", OUT)


if __name__ == "__main__":
    main()
