"""整机架构框图 → png/11_architecture.png（信号与控制）、png/12_power_tree.png（电源树）
运行：.venv/Scripts/python.exe fig_architecture.py（在项目目录下）"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import render as R

F = R.FONT
COL = dict(host="#bbdefb", inp="#c8e6c9", inst="#ffe0b2", el="#e0e0e0", pwr="#fff59d", hv="#ffcdd2",
           dev="#ffffff", todo="#f3e5f5")


def box(ax, x, y, w, h, text, c="dev", fs=10, bold=False, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8", fc=COL.get(c, c),
                                ec="#333", lw=1.4 if bold else 0.8, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontproperties=F, fontsize=fs,
            fontweight="bold" if bold else "normal")
    return (x, y, w, h)


def edge(b, side):
    x, y, w, h = b
    return {"l": (x, y + h / 2), "r": (x + w, y + h / 2), "t": (x + w / 2, y + h), "b": (x + w / 2, y)}[side]


def arrow(ax, p0, p1, label="", both=False, col="#333", off=(0, 0.9), fs=8, ls="-"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="<|-|>" if both else "-|>", mutation_scale=11, lw=1.0,
                                 color=col, ls=ls, shrinkA=2, shrinkB=2))
    if label:
        ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], label, ha="center", va="bottom",
                fontproperties=F, fontsize=fs, color=col, bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.85))


def group(ax, x, y, w, h, title, c):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5", fc=COL[c], ec="#666",
                                lw=1.0, alpha=0.45))
    ax.text(x + 0.8, y + h - 0.6, title, ha="left", va="top", fontproperties=F, fontsize=12, fontweight="bold")


def signal_diagram(fname="png/11_architecture.png"):
    fig, ax = plt.subplots(figsize=(20, 13), dpi=110)
    ax.set_xlim(0, 120); ax.set_ylim(0, 78); ax.axis("off")

    # 主机
    group(ax, 41, 30, 30, 22, "主机层", "host")
    opi = box(ax, 46, 38, 20, 8, "Orange Pi 4\n（Armbian）\n未安装，位置待定", "host", 11, True)
    hub = box(ax, 46, 31.5, 12, 4.5, "一分四 USB2.0\nHub 模块（买现成）", "dev", 8.5)
    arrow(ax, edge(hub, "t"), (52, 38), "USB2 口 2", both=True, off=(2.8, -0.6))

    # EL（不展开）
    group(ax, 41, 58, 30, 18, "EL 显示子系统（单独开发，这里不展开）", "el")
    fpga = box(ax, 44, 62, 11, 7, "Tang Primer 20K\nDock（FPGA）\n未安装", "el", 9)
    elif_ = box(ax, 57, 62, 6, 7, "EL-IF\n(PCB-1)", "el", 9)
    scr = box(ax, 65, 62, 5, 7, "EL 屏\nLJ64K052", "el", 8)
    arrow(ax, edge(opi, "t"), edge(fpga, "b"), "HDMI", off=(-2.5, -1))
    arrow(ax, edge(fpga, "r"), edge(elif_, "l")); arrow(ax, edge(elif_, "r"), edge(scr, "l"))
    arrow(ax, (64, 46), edge(elif_, "b"), "UART4", off=(2.2, -1))

    # 输入层
    group(ax, 1, 14, 36, 50, "输入层（斜面 / 底座条）", "inp")
    pico = box(ax, 20, 36, 14, 8, "Raspberry Pi Pico\n（USB HID）\n在斜面电路板上", "inp", 11, True)
    ins = [("带灯方键 24×18 ×6\n按键 6 入 + 灯 6 出（ULN2803）", 56), ("EC11 编码器 ×2\nA / B / 按压，6 入", 49),
           ("60 mm 推子 ×2\n2 路 ADC", 43), ("模式开关（按 6 档接）\n分压链 → 1 路 ADC", 37)]
    for t, y in ins:
        b = box(ax, 3, y, 14, 5, t, "dev", 8.5)
        arrow(ax, edge(b, "r"), (20, 40 + (y - 46) * 0.12))
    kb = box(ax, 3, 24, 14, 6, "X1 Tablet 磁吸键盘\n（底座条 POGO 触点，USB）", "dev", 8.5)
    usb = box(ax, 3, 16, 14, 5.5, "前面 USB2 口\n（面板延长线）", "dev", 9)
    arrow(ax, edge(pico, "r"), (46, 33.8), "USB（经 Hub）", both=True, off=(0, 0.3))
    u3 = box(ax, 20, 16, 14, 5.5, "前面 USB3 口\n（面板延长线，直连 Pi）", "dev", 8.5)
    arrow(ax, edge(u3, "r"), (50, 38), both=True)
    arrow(ax, edge(kb, "r"), (46, 33.2), both=True)
    arrow(ax, edge(usb, "r"), (46, 32.6), both=True)

    # 仪器层
    group(ax, 75, 2, 44, 74, "仪器层", "inst")
    esp = box(ax, 77, 36, 12, 9, "ESP32-S3\n（WROOM-1U\nN16R8）", "inst", 11, True)
    arrow(ax, edge(opi, "r"), edge(esp, "l"), "USB + 关机握手（2 根 GPIO）", both=True, off=(0, 0.5))
    subs = [
        ("辉光钟：IN-14 ×6（HH:MM:SS）\n3×74HCT595 → 6×K155ID1 → 阴极；阳极 170 V（自制通用高压小板）", 66, "hv"),
        ("IV-18 荧光管\nMAX6921 驱动（DIN / CLK 与 595 共用）\n栅/阳极约 35 V（XL6009），灯丝交流方波 + 偏置", 58, "dev"),
        ("6E2 猫眼（侧视条形）×2\nPWM 调栅压控制光条；阳极约 250 V（自制通用高压小板）\n阴极 12 V、栅极 0–12 V；灯丝 2×6.3 V 串联取 HV-B 12 V", 50, "hv"),
        ("指针表头 85C1 0–1 mA\nPWM 串电阻直推", 43.5, "dev"),
        ("盖革计数：J305 + 自制盖革板（5 V 输入，板上升压约 400 V）\n脉冲 → ESP32 计数；蜂鸣器咔哒声", 35.5, "hv"),
        ("环境光 BH1750、RTC DS3231（I2C）\n人体感应 LD2410B（OUT / UART）", 27.5, "dev"),
        ("电源管理（直接用 ESP 引脚，配合 PCB-3 电源板）\n读开关状态、PFAIL；Pi 运行期间拉高“保持”；软关机握手", 19.5, "todo"),
        ("HV_EN → PCB-3 高压受控电源\n（与“高压”开关同时打开才有电）", 12, "dev"),
    ]
    for i, (t, _, c) in enumerate(subs):
        b = box(ax, 92, 67 - i * 7.7, 26, 5.6, t, c, 8.6)
        arrow(ax, edge(esp, "r"), edge(b, "l"))

    # 音频 / 散热
    amp = box(ax, 59, 21, 9, 4.5, "PAM8403 功放", "dev", 9)
    spk = box(ax, 59, 12, 9, 5, "40 mm 喇叭\n（朝左侧面）", "dev", 9)
    fan = box(ax, 45, 12, 11, 9, "散热\nOrange Pi：散热片 + 40×10 风扇\n（Pi 旁小板，18 脚启停）", "dev", 9)
    arrow(ax, (63.5, 38), edge(amp, "t"), "音频", off=(2.5, -1))
    arrow(ax, edge(amp, "b"), edge(spk, "t"))

    ax.text(60, 0.6, "图例：粗框 = 控制器；红底 = 带高压的模块；灰色 = EL 子系统（单独开发）。箭头方向为控制/数据方向，双向箭头为总线。",
            ha="center", fontproperties=F, fontsize=10)
    fig.suptitle("MIS-01 整机架构：信号与控制（2026-10-20，按接线方案 v1.0）", fontproperties=F, fontsize=17)
    fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname)


def power_diagram(fname="png/12_power_tree.png"):
    fig, ax = plt.subplots(figsize=(20, 11), dpi=110)
    ax.set_xlim(0, 120); ax.set_ylim(0, 66); ax.axis("off")
    iec = box(ax, 1, 50, 13, 8, "IEC C14 电源座\n（保险 + 开关）\n市电 220 V", "hv", 9.5)
    lrs = box(ax, 18, 50, 14, 8, "明纬 LRS-200-24\n24 V 8.8 A", "pwr", 10, True)
    arrow(ax, edge(iec, "r"), edge(lrs, "l"), "AC")
    pcb3 = box(ax, 36, 46, 16, 16, "PCB-3 电源板\n24 V 母线、分路保险\nPFAIL 掉电预警\n主机电子保险 A / B\nEL 主机同步开关\n高压受控电源", "pwr", 10, True)
    arrow(ax, edge(lrs, "r"), (36, 54), "24 V")

    n12 = box(ax, 58, 52, 16, 7, "NID100-12\n12 V 7.5 A", "pwr", 10, True)
    n5 = box(ax, 58, 30, 16, 7, "NID100-5\n5 V 11 A", "pwr", 10, True)
    b24 = box(ax, 58, 8, 16, 7, "24 V 直接分路", "pwr", 10, True)
    for b in (n12, n5, b24):
        arrow(ax, edge(pcb3, "r"), edge(b, "l"))

    loads12 = ["主机同步 → EL 屏 VD（经 EL-IF）、FPGA Dock", "键灯、绿灯",
               "高压受控电源 HV-A → 通用高压小板 → 170 V *", "高压受控电源 HV-B → 通用高压小板 → 约 250 V；6E2 灯丝"]
    loads5 = ["电子保险 A（开关 或 ESP32 保持）→ Orange Pi 4", "电子保险 B（同一使能）→ USB Hub 模块、PAM8403", "主机同步 → EL 屏 VL（经 EL-IF）",
              "常电：ESP32-S3、LD2410B、IV-18 灯丝", "高压受控电源 → 自制盖革板（板上升压约 400 V）"]
    loads24 = ["开关 → XL6009 → 35 V → IV-18 栅/阳极", "备用输出（24 / 12 / 5 V 各 2 路，带保险）"]
    for loads, b in ((loads12, n12), (loads5, n5), (loads24, b24)):
        x, y, w, h = b
        y0 = y + h + 2.2 - 0.3
        for i, t in enumerate(loads):
            yy = y0 - i * 3.6
            hv = "高压" in t or "XL6009" in t
            bb = box(ax, 80, yy - 1.4, 36, 2.8, t, "hv" if hv else "dev", 9)
            arrow(ax, edge(b, "r"), edge(bb, "l"))

    # 三个钮子开关
    sw = box(ax, 1, 14, 34, 24,
             "斜面 3 个保护盖钮子开关（触点都接到 PCB-3 电源板）\n\n"
             "主机：电子保险 A/B、EL 同步开关使能 = 开关 或 ESP32 保持\n开 → 立即上电；关 → ESP32 保持住，Pi 软关机后再断（60 s 兜底）\n"
             "高压：受控电源使能 = 开关 与 HV_EN（ESP32 不在时默认关）\n"
             "屏幕：经 PCB-3 转 J_PF 送到 EL 接口板，硬件关 VD + 通知 FPGA\n\n"
             "指示灯接在各自被控电源的输出上：绿 = Pi 5 V，红 = 高压受控电源，黄 = +12V_EL\n"
             "ESP32 常电：关掉主机后辉光钟照样走", "todo", 9.5)
    ax.text(1, 6, "* 辉光管 170 V、6E2 250 V 都用自制通用高压小板（UC3843AN，12 V 输入），盖革板自产约 400 V；电源板只控制它们的低压输入。\n"
                  "  EL 屏两路电源的软启动与上电顺序见 EL 设计笔记第 10 节，这里只画分配关系。",
            fontproperties=F, fontsize=9.5, va="bottom")
    fig.suptitle("MIS-01 电源树（2026-10-20，按接线方案 v1.0）", fontproperties=F, fontsize=17)
    fig.tight_layout(rect=(0, 0, 1, 0.96)); fig.savefig(fname, facecolor="white"); plt.close(fig)
    print("saved", fname)


if __name__ == "__main__":
    signal_diagram()
    power_diagram()
