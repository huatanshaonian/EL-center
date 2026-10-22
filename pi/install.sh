#!/bin/sh
# MIS-01 Pi 侧安装（在 Orange Pi 上，从本目录运行）：sudo sh install.sh
# 做的事：装依赖 → 拷程序到 /opt/mis01 → 配置文件 → udev 规则 → 设备树补丁（PI_RUN 拉高、开 uart4）→ systemd 服务。
# 设备树补丁要重启才生效；重启后运行 sudo sh check.sh 检查。
set -e
[ "$(id -u)" = 0 ] || { echo "请用 sudo 运行：sudo sh install.sh"; exit 1; }
D=$(cd "$(dirname "$0")" && pwd)
ENV=/boot/armbianEnv.txt

echo "== 1/6 依赖（pyserial、libgpiod Python 绑定）"
apt-get install -y python3-serial python3-libgpiod

echo "== 2/6 程序 → /opt/mis01，命令行工具 → /usr/local/bin/mis01ctl"
install -d /opt/mis01
rm -rf /opt/mis01/mis01d
cp -r "$D/mis01d" /opt/mis01/
find /opt/mis01 -name __pycache__ -prune -exec rm -rf {} +
install -m 755 "$D/mis01ctl" /usr/local/bin/mis01ctl

echo "== 3/6 配置 /etc/mis01/mis01.conf（已有就不覆盖）"
install -d -m 755 /etc/mis01
if [ -f /etc/mis01/mis01.conf ]; then
    echo "   已存在，保留。新样例在 /etc/mis01/mis01.conf.example"
else
    install -m 600 "$D/mis01.conf.example" /etc/mis01/mis01.conf
fi
install -m 644 "$D/mis01.conf.example" /etc/mis01/mis01.conf.example

echo "== 4/6 udev：/dev/mis01-esp（协议口）、/dev/mis01-esp-log（日志口）"
install -m 644 "$D/udev/99-mis01.rules" /etc/udev/rules.d/99-mis01.rules
udevadm control --reload
udevadm trigger --subsystem-match=tty

echo "== 5/6 设备树：PI_RUN gpio-hog、uart4（先备份 $ENV）"
cp "$ENV" "$ENV.bak-mis01-$(date +%Y%m%d%H%M%S)"
# 每次都重新编译（改过 overlay 后重跑 install.sh 即更新）
install -d /boot/overlay-user
dtc -@ -q -I dts -O dtb -o /boot/overlay-user/mis01-pi-run.dtbo "$D/overlay/mis01-pi-run.dts"
if grep -q "^user_overlays=.*mis01-pi-run" "$ENV"; then
    echo "   mis01-pi-run 已在 user_overlays 里（dtbo 已更新）"
elif grep -q "^user_overlays=" "$ENV"; then
    sed -i 's/^user_overlays=\(.*\)$/user_overlays=\1 mis01-pi-run/' "$ENV"
else
    echo "user_overlays=mis01-pi-run" >> "$ENV"
fi
if grep -q "^overlays=.*rk3399-uart4" "$ENV"; then
    echo "   uart4 已开"
elif grep -q "^overlays=" "$ENV"; then
    sed -i 's/^overlays=\(.*\)$/overlays=\1 rk3399-uart4/' "$ENV"
else
    echo "overlays=rk3399-uart4" >> "$ENV"
fi
grep -E "^(overlays|user_overlays)=" "$ENV"

echo "== 6/6 systemd 服务 mis01d"
install -m 644 "$D/systemd/mis01d.service" /etc/systemd/system/mis01d.service
systemctl daemon-reload
systemctl enable mis01d
systemctl restart mis01d
sleep 2
systemctl --no-pager -n 15 status mis01d || true

echo
echo "安装完成。设备树补丁要重启才生效：sudo reboot，重启后运行 sudo sh check.sh"
