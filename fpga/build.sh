#!/usr/bin/env bash
# MIS-01 FPGA 编译（开源工具链 yosys + nextpnr-himbaechel + apicula），在 WSL 里运行：
#   bash build.sh el_hdmi          # 完整程序（HDMI → EL）
#   bash build.sh el_test          # 测试时序程序
#   EDID=edid/edid_640x480_27m.hex bash build.sh el_hdmi   # 换 27 MHz 版 EDID
# 产物：<工程>/build/<顶层>.fs，用高云 Programmer 的 SRAM Program 烧录。
# 工具链路径默认 ~/tools/oss-cad-suite/bin，可用 TOOLS=... 覆盖。
set -euo pipefail

PROJ="${1:?用法: bash build.sh el_hdmi|el_test}"
TOOLS="${TOOLS:-$HOME/tools/oss-cad-suite/bin}"
DEVICE="GW2A-LV18PG256C8/I7"
FAMILY="GW2A-18"
HERE="$(cd "$(dirname "$0")" && pwd)"
COM="$HERE/common/rtl"

case "$PROJ" in
    el_hdmi)
        DIR="$HERE/el_hdmi"
        TOP="el_hdmi_top"
        CST="$DIR/constraints/el_hdmi.cst"
        SRCS=("$DIR"/rtl/el_hdmi_top.v "$DIR"/rtl/hdmi/*.v "$DIR"/rtl/video/*.v "$DIR"/rtl/ctrl/*.v "$COM"/*.v)
        EDID="${EDID:-edid/edid_640x480.hex}"
        PARAMS="chparam -set EDID_FILE \"$EDID\" $TOP;"
        ;;
    el_test)
        DIR="$HERE/el_test"
        TOP="el_test_top"
        CST="$DIR/src/el_test.cst"
        SRCS=("$DIR"/src/el_test_top.v "$COM"/el_pll.v "$COM"/reset_gen.v "$COM"/input_sync.v "$COM"/key_press.v
              "$COM"/el_scan_timing.v "$COM"/el_pattern.v "$COM"/el_power_seq.v "$COM"/led_status.v)
        PARAMS=""
        ;;
    *) echo "未知工程: $PROJ"; exit 1 ;;
esac

cd "$DIR"
mkdir -p build
rm -f build/"$TOP".json build/"$TOP"_pnr.json build/"$TOP".fs

echo "== yosys 综合 =="
"$TOOLS"/yosys -q -l build/"$TOP"_yosys.log \
    -p "read_verilog ${SRCS[*]}; $PARAMS synth_gowin -top $TOP -json build/$TOP.json"

echo "== nextpnr 布局布线 =="
"$TOOLS"/nextpnr-himbaechel -l build/"$TOP"_nextpnr.log \
    --json build/"$TOP".json --write build/"$TOP"_pnr.json \
    --device "$DEVICE" --vopt family="$FAMILY" --vopt cst="$CST"

echo "== gowin_pack 生成比特流 =="
"$TOOLS"/gowin_pack -d "$FAMILY" -o build/"$TOP".fs build/"$TOP"_pnr.json

echo
echo "完成：$DIR/build/$TOP.fs"
grep -E "Max frequency|BSRAM|SDPB|LUT4|DFF|rPLL|IDES|Info: Device utilisation" -A0 build/"$TOP"_nextpnr.log | tail -30 || true
