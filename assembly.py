"""
MIS-01 整机布局装配（布局 E11；Orange Pi 4、FPGA Dock 在电脑层，见 assembly_computers.py）
全局坐标：X 向右(宽)、Y 由前向后(深)、Z 向上；竖直前面板外表面 Y=-2，框架前沿 Y=0。
框架外形 320(W) x 220(D) x 420(H)，2020 型材；底部斜面与键盘座向前探出约 45（见 assembly_panel.py）。
公共尺寸/配色/零件表在 assembly_base.py。
"""
import cadquery as cq
import parts as P
import parts_modules as M
import parts_panel as F
import assembly_panel as AP
import assembly_computers as AC
import assembly_covers as ACV
import vendor_parts as V
from assembly_base import W, D, H, Z_DECK, Z_SHELF, Z_SCREEN, PLATE_T, ITEMS, add, to_min

# ------------------------------------------------------------------ 框架
def frame():
    for i, (x, y) in enumerate(((0, 0), (W - 20, 0), (0, D - 20), (W - 20, D - 20))):
        add(f"2020_post_L{H}_{i+1}", P.profile_2020(H).translate((x, y, 0)), "alu", "frame")
    xr = P.profile_2020(W - 40)
    for tag, y, z in (("FB", 0, 0), ("FT", 0, H - 20), ("RB", D - 20, 0), ("RT", D - 20, H - 20)):
        add(f"2020_Xrail_L{W-40}_{tag}", to_min(xr.rotate((0, 0, 0), (0, 1, 0), 90), 20, y, z), "alu", "frame")
    yr = P.profile_2020(D - 40)
    for tag, z in (("bot", 0), ("deck", Z_DECK - 20), ("shelf", Z_SHELF - 20), ("top", H - 20)):
        for side, x in (("L", 0), ("R", W - 20)):
            add(f"2020_Yrail_L{D-40}_{tag}_{side}", to_min(yr.rotate((0, 0, 0), (1, 0, 0), -90), x, 20, z), "alu", "frame")
    # 甲板/电脑层型材端部角码（其余接头建议用端面攻丝 M5 或隐藏角码）
    br = P.corner_bracket_2020().mirror("XY")            # 水平腿朝上；17 宽在型材上居中，1 mm 定位凸台嵌入槽口
    for z in (Z_DECK - 20, Z_SHELF - 20):
        for x in (0, W - 20):
            add("corner_bracket", to_min(br, x + 1.5, 19, z - 20), "alu", "frame")
            add("corner_bracket", to_min(br.mirror("XZ"), x + 1.5, D - 40, z - 20), "alu", "frame")
    # 底板 / 甲板（前伸到 Y=2 托住管龛，前角避让立柱）/ 电脑层板 / 顶板
    add("base_plate_bakelite", P.plate(W, D, PLATE_T).translate((0, 0, -PLATE_T)), "bakelite", "plates")
    deck = P.plate(W - 4, D - 24, PLATE_T, notches=((0, 0, 18, 18), (W - 4 - 18, 0, 18, 18)))
    add("deck_plate_bakelite", deck.translate((2, 2, Z_DECK)), "bakelite", "plates")
    add("shelf_plate_bakelite", P.plate(W - 4, D - 52, PLATE_T).translate((2, 30, Z_SHELF)), "bakelite", "plates")
    vents = [(40 + i * 20, 60 + j * 20, 8) for i in range(13) for j in range(6)]
    vents += [(x, y, 3.2) for x, y in ((165, 45), (255, 45), (165, 135), (255, 135))]   # 吊 EL 接口板 M3（frame_spec.EXTRA_M3）
    add("top_plate_bakelite_vented", P.plate(W, D, PLATE_T, holes=vents).translate((0, 0, H)), "bakelite", "top")

# ------------------------------------------------------------------ EL 屏
def screen():
    sx0 = (W - 267) / 2
    add("Sharp_LJ64K052", P.lj64k052().translate((sx0, 3, Z_SCREEN)), "glass_el", "core")
    # 托架：贴屏背面，用屏的 Ø3.5 孔（257×208）锁 M3；托架上沿顶到前上横梁下面（Z=400）
    z0 = Z_SCREEN - 2
    brk = P.el_bracket(back_y=3 + 23.5, h=224.0, holes_z=(Z_SCREEN + 6 - z0, Z_SCREEN + 214 - z0), hole_x=sx0 + 5 - 20)
    add("EL_bracket_L", brk.translate((20, 0, z0)), "alu", "mech")
    add("EL_bracket_R", brk.mirror("YZ").translate((W - 20, 0, z0)), "alu", "mech")

# ------------------------------------------------------------------ 管龛（甲板上）：IN-14 一排，IV-18 横在其正下方
TUBE_X = [35, 57, 84, 106, 133, 155]          # 6 支 IN-14 管心，HH:MM:SS 分组（管龛窗 x 22..170）
Y_TUBE = 27                                    # IN-14 管轴距框架前沿（引线向下伸到 108.8，须在 IV-18 后面）
Y_IV18 = 12                                    # IV-18 管轴（玻壳前沿 y 2.5，让开面板背面 2 mm 亚克力）
Z_DRV = Z_DECK + PLATE_T + 10                  # 辉光驱动板底面：M3×10 铜柱立在甲板上
Z_IN14_PCB = Z_DRV + 1.6 + 11                  # IN-14 小板底面 116.6：2×7 排母 8.5 + 排针塑料座 2.5 插在驱动板上（IV-18 顶 114；管顶 174.7，EL 托架下沿 176）
DRV = (20, 40, 150, 80)                        # 辉光驱动板 x0, y0, 长, 宽（NIXIE-DRV D1，板原点 = 全局 (20, 40)）
DRV_STEP = "el_driver/NIXIE-DRV_D1/制板文件_驱动板/NIXIE-DRV_D1.1.step"        # 约 26 MB，不进 git
IN14_STEP = "el_driver/NIXIE-DRV_D1/制板文件_IN14小板/IN14-SOCK_D1.step"    # 板原点 = 全局 (管心 x − 10.5, 15)；STEP 里代替管子的 1×13 排针不装
ESP_BASE = (40, 120, 110, 50)                  # ESP32-S3 底板 ESP-BASE D1 x0, y0, 长, 宽（mis-01-56 2026-10-21 画完，原 90×50 放不下竖插 DS3231 加宽）：驱动板后面，M3×6 铜柱，四孔 (45/145, 125/165) 都在孔阵上
SMA_DECK = (120.0, 187.0)                       # 甲板上 SMA 天线座孔 Ø6.5（全局 x, y）：上方到电脑层板 z 260 全空，天线竖放顶到约 z 256
ESP_STEP = "el_driver/ESP-BASE_D1/制板文件/ESP-BASE_D1.step"   # 约 32 MB，不进 git；原点 = 板左前角，板底 z 0；含插座，不含开发板和 DS3231
HVUNI_STEP = "el_driver/HV-UNI_D1/制板文件/HV-UNI_D1.step"   # 通用高压小板 80×40（mis-01-56），不进 git
EYE_STEP = "el_driver/EYE-6E2_D1/制板文件/EYE-6E2_D1.1.step"     # 不进 git
HVUNI_STACK = 11                               # 排针插宿主板排母，叠高 11，四角 M3×11 铜柱
EYE_STANDOFF = 6                               # 6E2 板铜柱 M3×6：管座顶面 z 111.6，管顶 173.6（托架下沿 176）
IV18_STEM_X = 141                              # IV-18 芯柱端面（引线端）X。2026-10-21 调头：引线端在右（第 1 位紧挨引线），排气尖在左到 x≈26；数字区中心约 x 86
IV18_ENDPLATE_X = 143                          # 竖立端板 IV18-END D1（垂直管轴，厚 1.6，黑色阻焊）：22 根引线不弯直接穿孔焊接，剪后伸出 ≤2 mm（到 x≈146.6）；外形 y 3–36.5、z 96.6–114
IV18_STEP = "el_driver/IV18_D1/制板文件/IV18_D1.step"            # 主板 130×37，约 28 MB，不进 git；板原点 = 全局 (22, 3)，板底 z 0
IV18_END_STEP = "el_driver/IV18_D1/制板文件/IV18-END_D1.step"    # 端板导出时平放（板厚沿 Z），全局 = (143 + Z, X, 96.6 + Y)，循环换轴不是镜像；不进 git
Z_IV18_PCB = Z_DECK + PLATE_T + 1                        # IV-18 主板底面 95（1 mm 尼龙垫片，板底不能有凸出焊点），管心 Z=106.6
EYE_Y = 31                                     # 6E2 管轴 Y：管座前耳孔在 y≈18，6E2 板前沿 ≥ y 13，才能从 J305（y ≤ 11.6 @ 板高）上方让开（2026-10-20 由 27 后移）
EYE_ROT = 18                                   # 6E2 管座绕 Z 转角：荧光屏正对 7 脚、正对 -Y（前面板）时，缺口在 +X 往后偏 18°（北京 6E2，用户确认缺口在右）
GM_SHIM = 3.0                                  # 夹子长条板垫高 3 mm（2026-10-21 由 1.5 改：板底有 400 V 焊盘，1.5 余量太小；板底引脚仍剪到 1 mm 内）。2026-10-23 M3×3 尼龙柱买不到，改 M3×12 尼龙螺丝 + 板下 1 颗尼龙螺母（2.4）+ 1 片尼龙垫片垫高，甲板下再 1 颗螺母
SBM_Y, SBM_X0 = 8, 186                         # 盖革管 J305 管轴 y 与左端 x（变量名沿用 SBM_）
SBM_Z = Z_DECK + PLATE_T + GM_SHIM + 1.6 + 6.7  # 管轴 z 105.3 = 甲板面 + 尼龙柱 + 板厚 + 夹口中心高 6.7（估）；管顶 110.3 < 盖革窗上沿 113
GM_L = 103.5                                   # J305 总长（用户实测）
GEIGER_BOARD = (180, 110, 60, 70)              # 盖革主板 x0, y0, 长, 宽：6E2 板后面，四孔 (185/235, 115/175)：前两孔在甲板孔阵，后两孔 y175 超出孔阵（y 35–165）要自己钻；M3×6 铜柱（2026-10-20 由 y 50 后移给 6E2 板让位，60×40 → 60×60 → 60×70：放不下全部元件）。左后角压住甲板后走线孔右端约 4×4 mm
EYE_BOARD = (210, 15, 90, 90)                  # 6E2 板 x0, y0, 长, 宽：前沿 y 15 让开 J305 和右夹子小板，后沿 y 105 让开右后走线孔（y ≥ 120），右沿 x 300；M3×6 铜柱，四角孔都要自己钻
GEIGER_STEP = "el_driver/GEIGER_D1/制板文件_主板/GEIGER-MAIN_D1.step"   # 约 34 MB，不进 git
GEIGER_CLIP_STEP = "el_driver/GEIGER_D1/制板文件_夹子板/GEIGER-CLIP_D1.step"   # 约 9 MB，不进 git；原点 = 全局 (153, 2)
PCB3_STEP = "el_driver/PWR-DIST_D1/制板文件/PWR-DIST_D1.1.step"   # 约 59 MB，不进 git
PAM_XY = (150.0, 30.0)                          # PAM8403 模块左前角（底板前部，喇叭线往左右前角走）；右侧两孔 (171, 33)(171, 42.5)
PCB3_XY = (80, 160)                            # 倒挂后板的左边 x、后边 y（板占 x 80–230、y 60–160）
PCB3_STANDOFF = 10
SPK_Y, SPK_Z = {"L": 47.5, "R": 49.5}, 45.0       # 5151 腔体喇叭出声面中心 y、z：本体 51×51 正对两根 Y 梁之间 z 20–70 的空档（L y 22–73、R y 24–75）；
                                                 # 耳孔 z 10.5 / 79.5 对下层、甲板层 Y 梁内侧槽中心 z 10 / 80。L 往前离立柱 2，R 往前离灯按钮 2.8
NID_SOCKET = 8.5                               # NID100 插拔式：排母塑高（0 = 直接焊在板上）


def hv_uni(name, x, y, rot, z_host):
    """通用高压小板：板坐标原点（左下角）转 rot 度后放到 (x, y)，板底面 = 宿主板顶面 + 叠高；四角 M3 铜柱"""
    def place(shp):
        return shp.rotate((0, 0, 0), (0, 0, 1), rot).translate((x, y, z_host))
    add(name, place(V.load_abs(HVUNI_STEP).translate((0, 0, HVUNI_STACK))), "pcb_g", "tubes")
    for hx, hy in ((5, 5), (75, 5), (5, 35), (75, 35)):
        add(f"standoff_M3x{HVUNI_STACK}_HV", place(P.standoff_m3(HVUNI_STACK).translate((hx, hy, 0))), "brass", "tubes")


def tubes():
    sock = V.load_abs_within(IN14_STEP, 0, 21)                                     # IN14-SOCK D1（mis-01-56），去掉代替管子的排针
    for k, x in enumerate(TUBE_X):
        add(f"IN14_socket_PCB_{k+1}", sock.translate((x - 10.5, Y_TUBE - 12, Z_IN14_PCB)), "pcb_g", "tubes")
        add(f"IN-14_{k+1}", P.in14().translate((x, Y_TUBE, Z_IN14_PCB + 1.6 + 4)), "nixie", "tubes")
    # 辉光驱动板 NIXIE-DRV D1（K155ID1×6 + 74AHCT595×4 + 高压小板插座）：6 块 IN-14 小板用 2×7 排针插在它前沿，每块再用 1 颗 M3 锁住
    x0, y0, l, w = DRV
    add("NIXIE-DRV_board", V.load_abs(DRV_STEP).translate((x0, y0, Z_DRV)), "pcb_g", "tubes")
    for xx, yy in ((x0 + 5, y0 + w - 5), (x0 + l - 5, y0 + w - 5), (70.5, y0 + 5), (119.5, y0 + 5)):   # 后两角 + 前沿两个分组空隙
        add("standoff_M3x10", P.standoff_m3(10).translate((xx, yy, Z_DECK + PLATE_T)), "brass", "tubes")
    # 170 V 高压小板插在驱动板后右（避开前沿 IN-14 小板），板占 x 85–165、y 77–117
    hv_uni("HV-UNI_170V", 85, 77, 0, Z_DRV + 1.6)
    # IV-18 主板 IV18 D1（mis-01-56）：130×37（x 22–152、y 3–40）用 1 mm 尼龙垫片坐在甲板上，孔 (45,35)(135,35) 在孔阵、(148,8) 自钻；
    # 管子贴在主板上（玻壳底比板面高 0.5），两端硅胶垫 + 扎带（x≈37、128）；引线端穿竖立端板 IV18-END D1，端板下沿两面焊盘和主板 T 形焊、两个榫插主板槽
    add("IV18_board", V.load_abs(IV18_STEP).translate((22, 3, Z_IV18_PCB)), "pcb_g", "tubes")
    end = V.load_abs(IV18_END_STEP).rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 0, 1), 90)   # 循环换轴 (X,Y,Z) → (Z,X,Y)
    add("IV18_endplate", end.translate((IV18_ENDPLATE_X, 0, Z_IV18_PCB + 1.6)), "pcb_b", "tubes")
    add("IV-18", P.iv18().rotate((0, 0, 0), (0, 0, 1), 180).translate((IV18_STEM_X, Y_IV18, Z_IV18_PCB + 11.6)), "vfd", "tubes")
    # XL6009 模块（IV-18 栅/阳极 35 V，实测 43×25×13）：长边沿 Y，甲板 x 178–203、y 55–98，M3×5 尼龙柱、对角两孔 (181,61)(200,92) 自钻；上方 z118 起是表头本体（2026-10-21 由 x 243–283、y 166–196 挪来，离 IV-18 板近）
    xl = M.xl6009_module().rotate((0, 0, 0), (0, 0, 1), 90)
    add("IV18_PSU_XL6009", to_min(xl, 178, 55, Z_DECK + PLATE_T + 5), "module", "tubes")
    # 6E2 ×2：管座在甲板上，管子竖立在前面板竖窗后
    for k, x in enumerate(AP.EYE_X):
        z = Z_DECK + PLATE_T + EYE_STANDOFF + 1.6 + 10                                   # 6E2 板还没画，只按铜柱 + 板厚抬高管座
        rz = lambda s: s.rotate((0, 0, 0), (0, 0, 1), EYE_ROT).translate((x, EYE_Y, z))
        add(f"Noval_socket_{k+1}", rz(M.noval_socket()), "dark", "tubes")
        add(f"6E2_{k+1}", rz(M.tube_6e2()), "eye", "tubes")
    # 6E2 板（EYE-6E2 D1，mis-01-56 导出的整板 STEP，原点 = 板左下角 = 全局 (210, 15)）
    ex, ey, el, ew = EYE_BOARD
    ze = Z_DECK + PLATE_T + EYE_STANDOFF
    add("EYE-6E2_board", V.load_abs(EYE_STEP).translate((ex, ey, ze)), "pcb_g", "tubes")
    for dx, dy in ((5, 5), (el - 5, 5), (5, ew - 5), (el - 5, ew - 5)):
        add("standoff_M3x6_EYE", P.standoff_m3(EYE_STANDOFF).translate((ex + dx, ey + dy, Z_DECK + PLATE_T)), "brass", "tubes")
    # 250 V 高压小板横放在 6E2 板上、两支管子后面（不转向，HV 输出在右端靠近管子），板占 x 215–295、y 50–90
    hv_uni("HV-UNI_250V", 215, 50, 0, ze + 1.6)

# ------------------------------------------------------------------ 盖革：J305 横在前面板盖革窗后；自制盖革板（参考 MightyOhm），位置待定
def geiger():
    add("J305", M.j305(GM_L).translate((SBM_X0, SBM_Y, SBM_Z)), "geiger", "geiger")
    # 夹子长条板 GEIGER-CLIP D1，L 形（长条 x 153–299、y 2–14，左端加宽到 x 153–186、y 2–40；垫高 GM_SHIM 3 mm（3 个孔各用 1 颗尼龙螺母 + 垫片垫，管子正下方板底建议再垫一条 3 mm 绝缘条）；左孔 (165,35)/(175,35) 在孔阵上，y 38–40 边上元件高 ≤ 6，上面是辉光驱动板）：
    # J305 夹子中心 = 管端往里 1.25（夹子内边对齐电极圆柱段内端），即 x 187.25 / 288.25；HAC2311S 那组已删。
    # 检测电路（全直插）在左端加宽处，x 153–164、y 18–36 元件顶 ≤ z108（上面是 IN-14 第 6 只的引脚）；4.7 MΩ 贴片阳极电阻在管下 x 268–282；
    # 右端 x 290–299 只有高压焊线盘和 M3 尼龙螺丝孔（296.5, 10.8，自钻）；XH-3 插座 J4 约在 (170, 28)
    # 已换成 mis-01-56 导出的整板 STEP（占位版本见 parts_modules.geiger_clip_strip）
    add("GEIGER-CLIP_board", V.load_abs(GEIGER_CLIP_STEP).translate((153, 2, Z_DECK + PLATE_T + GM_SHIM)), "pcb_g", "geiger")
    # 盖革主板 GEIGER-MAIN D1（mis-01-56 导出的整板 STEP，原点 = 板左前角 = 全局 (180, 110)，板底 z100）
    gx, gy, gl, gw = GEIGER_BOARD
    add("GEIGER-MAIN_board", V.load_abs(GEIGER_STEP).translate((gx, gy, Z_DECK + PLATE_T + 6)), "pcb_g", "geiger")
    for dx, dy in ((5, 5), (gl - 5, 5), (5, gw - 5), (gl - 5, gw - 5)):
        add("standoff_M3x6", P.standoff_m3(6).translate((gx + dx, gy + dy, Z_DECK + PLATE_T)), "brass", "geiger")

# ------------------------------------------------------------------ ESP32-S3 底板 ESP-BASE D1（mis-01-56 画）
def esp_base():
    """底板平放在驱动板后面；开发板 USB-C 朝左、端面 x 42（弯头线从电脑层左走线孔上去接 Pi），天线端 U.FL 朝右；
    DS3231（ZS-042）用 6P 弯针竖插在 J_RTC（中心 (125, 142)，排母沿 x），模块板面在 xz 面内、两侧各留 11 mm"""
    x0, y0, l, w = ESP_BASE
    zb = Z_DECK + PLATE_T + 6
    top = zb + 1.6
    add("ESP-BASE_board", V.load_abs(ESP_STEP).translate((x0, y0, zb)), "pcb_b", "esp")
    for dx, dy in ((5, 5), (l - 5, 5), (5, w - 5), (l - 5, w - 5)):
        add("standoff_M3x6_ESP", P.standoff_m3(6).translate((x0 + dx, y0 + dy, Z_DECK + PLATE_T)), "brass", "esp")
    # 开发板：前排针 y 133.57 = ky + 1.27；首针 x 45.81 = kx + 5.05；塑料座 2.6 坐在 8.5 排母顶上
    add("ESP32-S3_DEV-KIT", M.esp32s3_dev_kit().translate((42.02, 132.3, top + 8.5 + 2.6)), "pcb_g", "esp")
    # DS3231：模块 X(朝弯针) → −Z，Y(针排) → +X，Z(板厚) → −Y；弯针中心 (45, 11, 8.82) 落到 (125, 142)，针尖插到排母内 6 mm
    rtc = M.ds3231_module().rotate((0, 0, 0), (0, 1, 0), 90).rotate((0, 0, 0), (0, 0, 1), -90)
    add("DS3231_module", rtc.translate((125 - 11, 142 + 8.82, top + 2.5 + 45)), "pcb_b", "esp")
    # 天线：开发板自带 IPEX→SMA 穿墙线（20 cm），SMA 座装在甲板后部 Ø6.5 孔里，螺纹朝上、棒状天线（15 cm，可折弯）竖在上面；
    # 线从开发板 U.FL 经后走线孔（x 135–185、y 176–190）下到甲板底，再从下面接 SMA 座（2026-10-26 由 IEC 小板挪来）
    sx, sy = SMA_DECK
    add("SMA_bulkhead_deck", V.sma_bulkhead().rotate((0, 0, 0), (1, 0, 0), -90).translate((sx, sy, Z_DECK)), "brass", "esp")
    add("WiFi_antenna_15cm", P.cyl(5, 150, sx, sy, Z_DECK + PLATE_T + 8), "dark", "esp")

# ------------------------------------------------------------------ 下舱：电源、配电、喇叭
def lower():
    # LRS-200-24 靠后放，端子在右端（靠近 IEC 插座）；机内可用空间见 free_space.py
    px, py, pl, pw = 22.5, 82.5, 215, 115                                # 底面 4-M4 落在底板孔阵 (55/205, 115/165)（规格书 Case 207）
    add("MeanWell_LRS-200-24", M.lrs200_24().translate((px, py, 0)), "psu", "power")
    # PCB-3 电源板（PWR-DIST D1，150×100，mis-01-56 导出的 STEP）：元件朝下倒挂在甲板下，M3×10 铜柱，四孔落在甲板孔阵上；
    # 绕 X 转 180°，+x 的 J_24V 仍朝 LRS 输出端；NID100 原来直焊时最低 z 51、离 LRS 顶 21（2026-10-20 用户确认）；改插拔式后见 pcb3_nid_modules
    z = Z_DECK - PCB3_STANDOFF
    add("PCB-3_PWR-DIST", V.load_abs(PCB3_STEP).rotate((0, 0, 0), (1, 0, 0), 180).translate((PCB3_XY[0], PCB3_XY[1], z)), "pcb_g", "power")
    for dx, dy in ((5, 5), (145, 5), (5, 95), (145, 95)):
        add("standoff_M3x10_PCB3", P.standoff_m3(PCB3_STANDOFF).translate((PCB3_XY[0] + dx, PCB3_XY[1] - dy, z)), "brass", "power")
    pcb3_nid_modules(z - 1.6)
    # 市电端子防护罩（亚克力 3 mm 罩帽，罩住电源右端端子，用电源侧面 M3 孔经角片固定）
    t, hx, hy, hl, hw, hh = 3, px + pl - 24, py - 2, 46, pw + 4, 40
    hood = (P.box(hl, hw, t, hx, hy, hh - t)                                   # 顶
            .union(P.box(t, hw, hh, hx + hl - t, hy, 0))                        # 外侧壁
            .union(P.box(hl - 24, t, hh, hx + 24, hy, 0)).union(P.box(hl - 24, t, hh, hx + 24, hy + hw - t, 0))
            .union(P.box(24, t, 10 - t, hx, hy, 30)).union(P.box(24, t, 10 - t, hx, hy + hw - t, 30)))
    add("Mains_hood_acrylic", hood, "acrylic", "covers")
    # 喇叭：两只 4 Ω 腔体喇叭 5151 款（2026-10-23 由 3070 改，音腔大约 4 倍；立体声，PAM8403 两路），在底层左右前角，
    # 出声面贴 Y 梁内侧面（x 20 / 300）朝外，声音穿过下层与甲板层 Y 梁之间的空当、从下巴托侧板的喇叭网出去。
    # 不用支架：耳朵朝上下，M3 螺丝 + 2020 用 M3 锤头螺母锁进上下两根 Y 梁的内侧槽（孔距 69，槽心距 70，槽宽 6 能吃下）
    spk = M.cavity_speaker_5151()
    for tag, x, mir in (("L", 20, False), ("R", W - 20, True)):
        sp = spk.mirror("YZ") if mir else spk
        add(f"Speaker_cavity_5151_{tag}", sp.translate((x, SPK_Y[tag], SPK_Z)), "dark", "power")
    add("PAM8403_module", M.pam8403_module().translate(PAM_XY + (3,)), "pcb_g", "power")   # 功放模块 24×15.5，右侧两孔 M3×3 尼龙柱，底板自钻


def pcb3_nid_modules(z_face):
    """PCB-3 上的 NID100-12（U_N12，板本地 y 63）、NID100-5（U_N5，y 37）：板子倒挂，模块针朝上插在排母里往下伸。
    1 脚焊盘板本地 x 41.87（坐标文件），针排在 y 上；模型 1 脚在 (1.3, 5.0)，针根 z 0。
    2026-10-22 用户要改插拔式（mis-01-56 改板中）：板上焊 2.54 单排排母（塑高 NID_SOCKET），模块再低 NID_SOCKET。"""
    nid = V.nid100_05().rotate((0, 0, 0), (1, 0, 0), 180)                         # 针朝上
    z_root = z_face - NID_SOCKET
    for name, ly in (("NID100-12_U_N12", 63), ("NID100-5_U_N5", 37)):
        gx, gy = PCB3_XY[0] + 41.87, PCB3_XY[1] - ly                               # 倒挂后板本地 y → 全局 160 − y
        add(name, nid.translate((gx - 1.3, gy + 5.0, z_root)), "psu", "power")
        if NID_SOCKET:
            add("socket_2.54_1x13_" + name.split("_", 1)[1], P.box(48.2 + 2.54, 2.5, NID_SOCKET, gx - 1.27, gy - 1.25, z_root), "dark", "power")

# ------------------------------------------------------------------ 电脑层
# Orange Pi 4、Dock、HDMI 软排线两头小板：2026-10-23 用户确认，见 assembly_computers.py。
# EL 接口板、Hub 模块、风扇小板还没放；后面板接口窗等布置定了再开。
def computers():
    AC.build()

# ------------------------------------------------------------------ 后面板
IEC_PLATE = (210.0, 0.0, W - 210.0, 110.0)          # 背面 IEC 小板 x0, z0, 宽, 高（2 mm 铝，嘉立创钣金，接 PE）


IEC_XZ = (276.0, 54.0)                           # AC-14-F12 开孔中心；耳孔 x 256 / 296，螺母让开右后立柱（x ≥ 300）


def iec_plate():
    """背面 IEC 小板（2 mm 铝，嘉立创钣金，接 PE）：IEC C14 开孔 28×60 + 耳孔 M3 ×2、M4 ×3（右后立柱 ×2、后下横梁）；
    原来的 SMA ×2 去掉（2026-10-26：ESP 自带 IPEX→SMA 线只有 20 cm，SMA 改装在甲板上）"""
    x0, z0, pw, ph = IEC_PLATE
    cut = [(IEC_XZ[0] - 14 - x0, IEC_XZ[1] - 30 - z0, 28, 60)]
    holes = [(IEC_XZ[0] + sx * 20 - x0, IEC_XZ[1] - z0, 3.5) for sx in (-1, 1)]
    holes += [(W - 10 - x0, z - z0, 4.5) for z in (10, 100)] + [(220 - x0, 10 - z0, 4.5)]
    return P.panel(pw, ph, 2, cut, holes).translate((x0, D, z0))


def rear():
    """背板不一定装（2026-10-22 用户定，整块背板在 assembly_covers），背面右下角的金属 IEC 小板一定装：IEC C14；
    M4 锁右后立柱（x 310）和后下横梁（z 10），小板要接 PE（整机架构 5.3）"""
    add("IEC_plate_alu", iec_plate(), "panel", "rear")
    add("IEC_C14_AC-14-F12", F.iec_c14_inlet().rotate((0, 0, 0), (0, 0, 1), 180).translate((IEC_XZ[0], D + 2, IEC_XZ[1])), "dark", "rear")

def build():
    ITEMS.clear()
    frame(); screen(); AP.build(); tubes(); geiger(); esp_base(); lower(); computers(); rear()
    ACV.build(IEC_PLATE)                      # 全高侧板、整块背板：纯盖板，不一定装（2026-10-22）
    return ITEMS

if __name__ == "__main__":
    import os, collections
    items = build()
    assy = cq.Assembly(name="MIS-01")
    names = collections.Counter()
    for name, shp, col, grp in items:
        names[name] += 1
        nm = name if names[name] == 1 else f"{name}_{names[name]}"
        assy.add(shp, name=nm, color=cq.Color(*col))
    os.makedirs("step", exist_ok=True)
    assy.export("step/MIS-01_layout_assembly.step")
    print("parts:", len(items))
