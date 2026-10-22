#!/bin/bash
# MIS-01 元器件库存（Part-DB）在群晖上的部署 / 升级脚本
# 用法（在 NAS 上）：sudo bash /volume2/docker/partdb/deploy.sh
#   首次：建目录、生成密钥、拉镜像、启动、建库并打印 admin 初始密码
#   之后：改 docker-compose.yml 里的版本号再跑一次 = 升级（自动迁移数据库，旧库先备份）
# 拉不下镜像时先挂代理：sudo bash ~/docker_proxy.sh on   （会重启 Container Manager，容器短暂重启）

set -e
cd "$(dirname "$(readlink -f "$0")")"
[ "$(id -u)" = "0" ] || { echo "需要 root：sudo bash $0"; exit 1; }

export PATH=/usr/local/bin:$PATH
if docker compose version >/dev/null 2>&1; then DC="docker compose"; else DC="docker-compose"; fi
PORT=8088
WWW=33   # 容器里 www-data 的 uid/gid

echo "== 1/5 准备目录"
mkdir -p db uploads public_media backup
chown -R $WWW:$WWW db uploads public_media
chmod 750 db uploads public_media

if [ ! -f secret.env ]; then
    echo "APP_SECRET=$(openssl rand -hex 32)" > secret.env
    chmod 600 secret.env
    echo "   已生成 secret.env（APP_SECRET，别删，删了已登录会话会失效）"
fi

if [ -f db/app.db ]; then
    bk="backup/app.db.$(date +%Y%m%d-%H%M%S)"
    cp -p db/app.db "$bk"
    echo "   已备份数据库 → $bk"
fi

echo "== 2/5 拉镜像"
if ! $DC pull; then
    echo "拉镜像失败。国内访问 Docker Hub 一般要代理：sudo bash ~/docker_proxy.sh on ，再重跑本脚本。"
    exit 1
fi

echo "== 3/5 启动容器"
$DC up -d

echo "== 4/5 等网页起来"
for i in $(seq 1 60); do
    code=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost' "http://127.0.0.1:$PORT/" || true)
    case "$code" in 2*|3*|5*) break ;; esac
    sleep 2
done
echo "   HTTP $code"

echo "== 5/5 建库 / 迁移数据库"
out=$(docker exec --user=www-data partdb php bin/console doctrine:migrations:migrate -n 2>&1) || {
    echo "$out" | tail -30; echo "数据库迁移失败，看上面的报错"; exit 1; }
echo "$out" | grep -E -i 'migrat|error' | tail -5
pw=$(echo "$out" | grep -o 'initial password for the "admin" user is: [^<]*' | sed 's/.*is: //')

echo
echo "完成：浏览器打开 http://192.168.1.6:$PORT/"
if [ -n "$pw" ]; then
    echo "用户名 admin，初始密码：$pw"
    echo "（只显示这一次，登录后马上在右上角用户设置里改掉）"
else
    echo "数据库已存在，沿用原来的账号密码。"
fi
