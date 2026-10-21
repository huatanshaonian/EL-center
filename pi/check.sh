#!/bin/sh
# 安装并重启后检查：sudo sh check.sh
[ "$(id -u)" = 0 ] || { echo "请用 sudo 运行：sudo sh check.sh"; exit 1; }

echo "== GPIO：line 22 应为 output、MIS01_PI_RUN、used；line 24 应为 input、consumer mis01d"
gpioinfo gpiochip1 | grep -E "line +(22|24):"

echo "== 串口"
ls -l /dev/mis01-esp /dev/mis01-esp-log /dev/ttyS4 2>&1

echo "== 设备树"
grep -E "^(overlays|user_overlays)=" /boot/armbianEnv.txt
printf "uart4 状态："; tr -d '\0' < /proc/device-tree/serial@ff370000/status; echo

echo "== 服务"
systemctl is-active mis01d
journalctl -u mis01d -b --no-pager -n 25
