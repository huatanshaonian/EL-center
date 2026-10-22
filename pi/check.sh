#!/bin/sh
# 安装并重启后检查：sudo sh check.sh
[ "$(id -u)" = 0 ] || { echo "请用 sudo 运行：sudo sh check.sh"; exit 1; }

echo "== GPIO：line 22 应为 output、MIS01_PI_RUN、used；line 24 应为 input、consumer mis01d"
gpioinfo gpiochip1 | grep -E "line +(22|24):"

echo "== 22 脚上拉：pinmux 里 pin 56 应归 mis01-pullups；服务日志应有 PI_SHDN_REQ 当前电平 1"
grep -E "^pin 56 " /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins 2>/dev/null || grep -rh "^pin 56 " /sys/kernel/debug/pinctrl/*/pinmux-pins 2>/dev/null
ls -d /sys/bus/platform/devices/mis01-pullups 2>&1
journalctl -u mis01d -b --no-pager | grep "PI_SHDN_REQ" | tail -3

echo "== 串口"
ls -l /dev/mis01-esp /dev/mis01-esp-log /dev/ttyS4 2>&1

echo "== 设备树"
grep -E "^(overlays|user_overlays)=" /boot/armbianEnv.txt
printf "uart4 状态："; tr -d '\0' < /proc/device-tree/serial@ff370000/status; echo

echo "== 服务"
systemctl is-active mis01d
journalctl -u mis01d -b --no-pager -n 25
