#!/usr/bin/env python3
"""给 apicula 生成的 .fs 补上高云格式的 // 注释头。

高云 Programmer 烧录时要读 .fs 开头的注释头（UserCode、CheckSum 等）。
apicula 的 gowin_pack 不写这段，Programmer 照样发送数据，但芯片加载不完成
（状态寄存器只剩擦除位 0x20、UserCode=0），最后报 "Error found!"。
补上注释头后加载正常（状态 0x6020，DONE 置位）。配置数据一位不改。

用法：python3 fs_header.py <file.fs> [--device GW2A-18 --version C
                              --part GW2A-LV18PG256C8/I7 --package GW2A-18C-PBGA256]
原地改写；已有注释头会先去掉再重写，可重复运行。输出用 CRLF 换行，与高云一致。
"""
import argparse
import datetime
import sys

CHECKSUM_CMD = "00001010"  # 0x0A：写校验和命令，低 16 位是校验和


def find_checksum(lines):
    for line in reversed(lines):
        if len(line) == 64 and line.startswith(CHECKSUM_CMD):
            return int(line[-16:], 2)
    raise ValueError("没找到 0x0A 校验和命令行，这不像 GW1N/GW2A 的 .fs")


def build_header(args, checksum):
    now = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
    return [
        "//File Title: Bitstream file",
        "//Tool Version: apicula gowin_pack + MIS-01 fs_header.py",
        f"//Device: {args.device}",
        f"//Device Version: {args.version}",
        f"//Part Number: {args.part}",
        f"//Device-package: {args.package}",
        "//BackgroundProgramming: OFF",
        f"//CheckSum: 0x{checksum:04X}",
        f"//UserCode: 0x0000{checksum:04X}",
        "//LoadingRate: 2.500MHz",
        "//CRCCheck: ON",
        "//Compress: OFF",
        "//Encryption: OFF",
        "//SecurityBit: ON",
        "//SecureMode: OFF",
        "//JTAGAsRegularIO: OFF",
        "//MultiBootSPIAddr: 0x00000000",
        f"//Created Time: {now}",
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fs")
    ap.add_argument("--device", default="GW2A-18")
    ap.add_argument("--version", default="C")
    ap.add_argument("--part", default="GW2A-LV18PG256C8/I7")
    ap.add_argument("--package", default="GW2A-18C-PBGA256")
    args = ap.parse_args()

    with open(args.fs, "rb") as f:
        text = f.read().decode("ascii").replace("\r", "")
    lines = [l for l in text.split("\n") if l and not l.startswith("//")]
    checksum = find_checksum(lines)
    out = build_header(args, checksum) + lines
    with open(args.fs, "wb") as f:
        f.write(("\r\n".join(out) + "\r\n").encode("ascii"))
    print(f"fs_header: {args.fs} 已加注释头，CheckSum=0x{checksum:04X}")


if __name__ == "__main__":
    sys.exit(main())
