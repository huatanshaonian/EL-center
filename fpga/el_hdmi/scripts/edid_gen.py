"""生成 MIS-01 EL 屏的 128 字节 DVI EDID（只宣告 640×480 一个模式，无 CEA 扩展块 → 信号源按 DVI 输出、无数据岛）。
参考 tang-monitor 的 scripts/edid_gen.py（MIT），字段按 VESA E-EDID 1.3。

两个版本（设计笔记 §5.1 / U12）：
  std  ：640×480@59.94，总 800×525，像素时钟 25.175 MHz（VESA DMT 标准时序）
  27m  ：有效 640×480，总 858×525，像素时钟 27.000 MHz（59.94 Hz）——Orange Pi 4 旧内核
         dw_hdmi-rockchip 只接受 MPLL 表里的像素时钟（从 27 MHz 起）时用这一份
FPGA 只按 DE 取有效像素，两种总时序都能收。

用法：python edid_gen.py <输出目录>   → 生成 edid_640x480.hex、edid_640x480_27m.hex
"""
import os
import sys


def dtd(pclk_10khz, h_act, h_blank, v_act, v_blank, hso, hsw, vso, vsw, img_w_mm, img_h_mm):
    """18 字节详细时序描述符，H/V 同步均为负极性、数字分离同步。"""
    return bytes([
        pclk_10khz & 0xFF, pclk_10khz >> 8,
        h_act & 0xFF, h_blank & 0xFF, ((h_act >> 8) << 4) | (h_blank >> 8),
        v_act & 0xFF, v_blank & 0xFF, ((v_act >> 8) << 4) | (v_blank >> 8),
        hso & 0xFF, hsw & 0xFF, ((vso & 0xF) << 4) | (vsw & 0xF),
        ((hso >> 8) << 6) | ((hsw >> 8) << 4) | ((vso >> 4) << 2) | (vsw >> 4),
        img_w_mm & 0xFF, img_h_mm & 0xFF, ((img_w_mm >> 8) << 4) | (img_h_mm >> 8),
        0x00, 0x00,
        0x18,
    ])


def make_edid(variant):
    e = bytearray(128)
    e[0:8] = bytes([0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00])
    # 厂商代码 "MIS"：M=13 I=9 S=19
    mfr = (13 << 10) | (9 << 5) | 19
    e[8], e[9] = mfr >> 8, mfr & 0xFF
    e[10:12] = (0x6401).to_bytes(2, "little")       # 产品码
    e[12:16] = (1).to_bytes(4, "little")             # 序列号
    e[16], e[17] = 42, 36                            # 2026 年第 42 周
    e[18], e[19] = 1, 3                              # EDID 1.3
    e[20] = 0x80                                     # 数字输入
    e[21], e[22] = 21, 16                            # 屏有效区约 211×158 mm
    e[23] = 120                                      # gamma 2.2
    e[24] = 0x06                                     # RGB，首选时序在 DTD1
    e[25:35] = bytes([0xEE, 0x91, 0xA3, 0x54, 0x4C, 0x99, 0x26, 0x0F, 0x50, 0x54])
    e[35] = 0x20 if variant == "std" else 0x00       # 既定时序 640×480@60（27m 版只给 DTD）
    e[36] = e[37] = 0x00
    for i in range(38, 54, 2):
        e[i], e[i + 1] = 0x01, 0x01                  # 标准时序：不用

    if variant == "std":
        e[54:72] = dtd(2518, 640, 160, 480, 45, 16, 96, 10, 2, 211, 158)
        hmin, hmax, pmax = 31, 32, 3                 # 行频 31–32 kHz，最大像素时钟 30 MHz
    else:
        e[54:72] = dtd(2700, 640, 218, 480, 45, 16, 96, 10, 2, 211, 158)
        hmin, hmax, pmax = 31, 32, 3                 # 27e6/858 = 31.47 kHz
    e[72:90] = bytes([0x00, 0x00, 0x00, 0xFD, 0x00, 59, 61, hmin, hmax, pmax,
                      0x0A, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20])
    name = b"MIS-01 EL\n"
    e[90:108] = bytes([0x00, 0x00, 0x00, 0xFC, 0x00]) + name.ljust(13, b" ")
    e[108:126] = bytes([0x00, 0x00, 0x00, 0x10, 0x00] + [0x00] * 13)
    e[126] = 0x00                                    # 无扩展块（DVI）
    e[127] = (256 - sum(e[0:127])) & 0xFF
    assert sum(e) & 0xFF == 0
    return e


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for variant, fn in (("std", "edid_640x480.hex"), ("27m", "edid_640x480_27m.hex")):
        e = make_edid(variant)
        with open(os.path.join(out, fn), "w", newline="\n") as f:
            f.write("\n".join(f"{b:02x}" for b in e) + "\n")
        print(fn, "checksum ok")


if __name__ == "__main__":
    main()
