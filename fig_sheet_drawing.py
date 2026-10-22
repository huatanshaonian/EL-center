"""钣金件询价包：每个零件 STEP + 同名 2D PDF → 外壳加工/钣金询价/，再打成 钣金询价.zip
嘉立创钣金询价要 3D（STEP，必须）+ 2D（dwg / dxf / pdf），同一零件文件名一致，可以整包上传。
零件和形状来自 export_enclosure.parts()（和下单文件同源）；视图用 drawing2d 隐藏线投影，标总体尺寸和工艺要求。
运行：.venv/Scripts/python.exe fig_sheet_drawing.py"""
import os
import zipfile
import cadquery as cq
from matplotlib.backends.backend_pdf import PdfPages
import export_enclosure as EE
import assembly_panel as AP
from drawing2d import Sheet, place

OUT = os.path.join("外壳加工", "钣金询价")
MAT = "5052 铝板 2.0 mm"
COMMON = [
    "技术要求",
    "1. 材料 5052-H32 铝板，厚 2.0；以 3D STEP 为准（折好弯的成品形状），本图只标总体尺寸和工艺要求。",
    "2. 折弯内 R1.7（模型已按此建）；孔：M4 用 Ø4.5、M3 用 Ø3.4，喇叭网 / 通风孔按 STEP。",
    "3. 表面：拉丝（纹路沿水平方向）+ 透明阳极氧化；另请报“拉丝 + 透明清漆”的价格作比较。",
    "4. 接地点：图中标出的 M4 孔背面 Ø12 圆内不做阳极 / 不涂层（遮蔽），保证导电。",
    "5. 去毛刺，锐边倒钝；拉丝面朝外，避免划伤。",
]


def front_shell(pdf, shp):
    s = Sheet(pdf, "MIS-01 前壳（前面板 + 斜面）", material=MAT)
    f = s.view(shp, "front", *place(shp, "front", 0.5, 40, 60), 0.5, "正视图 1:2（从前往后看）")
    s.overall(shp, "front", f, txt_w="324", txt_h="402.7")
    r = s.view(shp, "right", *place(shp, "right", 0.5, 215, 60), 0.5, "右视图 1:2（折弯剖面）", label_below=False)
    s.overall(shp, "right", r, txt_w="47.3", txt_h=False)
    s.leader(r((322, -24, 50)), (245, 90), "斜面展开长 83，与竖直面夹角 33°")
    s.leader(r((322, -24, 70)), (245, 104), "斜面两侧各 1 道 90° 翻边（往里，高 14）")
    y, z = AP.slant_pt(AP.FLANGE_SCREW_U[0], AP.FLANGE_SCREW_T)
    s.leader(r((322, y, z)), (245, 118), "翻边上 4 颗 M3 压铆螺母（每边 2，CLS-M3-1，孔 Ø4.2，从外侧压入）")
    s.notes(255, 280, COMMON + [
        "6. 开孔：EL 屏视窗、管龛窗、6E2 窗、盖革窗、表头 Ø50 + 2×M3；",
        "   斜面上按钮 / 指示灯 Ø16.2 ×9、钮子 Ø6.2 ×3、旋转开关 Ø10.1 + 2×Ø4.2、",
        "   编码器 Ø7.2 ×3、推子槽 62×2 ×2、USB 方孔 ×2、键盘座 M3 沉头孔 ×3。",
        "7. 询价版：部分开孔尺寸待面板件实测后微调（不影响报价）。",
        "8. 接地点：前面板右侧 M4 孔（x 310, z 140 附近）背面遮蔽。",
    ], step=5.5)
    s.title_block("1:2")
    s.save()


def chin_tray(pdf, shp):
    s = Sheet(pdf, "MIS-01 下巴托（底板 + 两侧板）", material=MAT)
    t = s.view(shp, "top", *place(shp, "top", 0.5, 40, 205), 0.5, "俯视图 1:2（图上方 = 后）")
    s.overall(shp, "top", t, txt_w="324", txt_h="145.4")
    f = s.view(shp, "front", *place(shp, "front", 0.5, 40, 130), 0.5, "正视图 1:2（从前往后看）")
    s.overall(shp, "front", f, txt_h="91.5")
    l = s.view(shp, "left", *place(shp, "left", 0.5, 240, 130), 0.5, "左视图 1:2（左侧板外侧，喇叭网）", label_below=False)
    s.overall(shp, "left", l)
    s.notes(40, 105, COMMON + [
        "6. 三道 90° 折弯：两侧板往上折、后边翻边往上折 18。",
        "7. 每块侧板：M4 ×6（锁型材）、M3 ×2（锁前壳翻边压铆螺母）、M3 ×2（锁键盘座两端）、喇叭网 Ø3 六角排孔。",
        "8. 后翻边 M4 ×3；中间孔背面 Ø12 遮蔽（接地点）。",
    ], step=5.5)
    s.title_block("1:2")
    s.save()


def flat(pdf, shp, title, view, sc, xy, notes, scale):
    """平板件：一个视图放在 xy（左下角），技术要求放右上"""
    s = Sheet(pdf, title, material=MAT, qty=notes.pop(0))
    f = s.view(shp, view, *place(shp, view, sc, *xy), sc, f"视图 {scale}")
    s.overall(shp, view, f)
    s.notes(230, 280, COMMON + notes, step=5.5)
    s.title_block(scale)
    s.save()


def main():
    os.makedirs(OUT, exist_ok=True)
    shapes = {name: shp for name, shp, *_ in EE.parts()}
    jobs = {
        "前壳_front_shell": lambda pdf, s: front_shell(pdf, s),
        "下巴托_chin_tray": lambda pdf, s: chin_tray(pdf, s),
        "IEC小板_iec_plate": lambda pdf, s: flat(pdf, s, "MIS-01 IEC 小板", "back", 1.0, (60, 120), [
            "1", "6. IEC C14 三合一插座开孔 28×60 + 2×M3（孔距 40）；SMA 天线座 Ø6.5 ×2；M4 ×3 锁型材。",
            "7. 右下 M4 孔背面 Ø12 遮蔽（接地点，必须接 PE）。"], "1:1"),
        "全高侧板_side_cover_x2": lambda pdf, s: flat(pdf, s, "MIS-01 全高侧板（左右同件）", "left", 0.5, (60, 70), [
            "2", "6. 左右两块是同一零件，做 2 件；M4 ×8 锁型材，带通风长孔。可选件，可单独报价。",
            "7. 一个 M4 孔背面 Ø12 遮蔽（接地点）。"], "1:2"),
        "背板_rear_cover": lambda pdf, s: flat(pdf, s, "MIS-01 背板", "back", 0.5, (40, 75), [
            "1", "6. 右下角缺口让出 IEC 小板；Ø56 通风孔 ×2；M4 ×7 锁型材。可选件，可单独报价。",
            "7. 一个 M4 孔背面 Ø12 遮蔽（接地点）。"], "1:2"),
    }
    files = []
    for name, job in jobs.items():
        shp = shapes[name]
        cq.exporters.export(shp, os.path.join(OUT, name + ".step"))
        with PdfPages(os.path.join(OUT, name + ".pdf")) as pdf:
            job(pdf, shp)
        files += [name + ".step", name + ".pdf"]
        print("ok", name, flush=True)
    with zipfile.ZipFile(os.path.join(OUT, "钣金询价.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for fn in files:
            z.write(os.path.join(OUT, fn), fn)
    print("saved", OUT)


if __name__ == "__main__":
    main()
