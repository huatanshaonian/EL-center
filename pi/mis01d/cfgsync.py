"""按配置文件 [esp_cfg] 节核对 ESP 的 CFG 键，不一致就写入并 CFG SAVE（规格第 4 节、6.9）。

密码类键（WIFI_PASS、WEB_PASS）读回是 "***"（不回显），只能比较"有没有"；所以记下上次写入的密码摘要（state.json），
配置里的密码变了才重写。日志里密码一律显示 ***。

也可以单独在电脑上用（ESP 插电脑 USB）：
    python -m mis01d.cfgsync --port COM8 --conf mis01.conf
"""
import argparse
import hashlib
import json
import logging
import os
import sys

from .esplink import EspError, quote

log = logging.getLogger("cfg")

SECRET_KEYS = ("WIFI_PASS", "WEB_PASS")


def _digest(v):
    return hashlib.sha256(v.encode("utf-8")).hexdigest()[:16]


def _load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_state(path, st):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f)
        os.replace(tmp, path)
    except OSError as e:
        log.warning("写状态文件失败：%s", e)


def sync(link, wanted, state_path):
    """返回改了的键列表。出错抛 EspError。"""
    st = _load_state(state_path)
    changed = []
    for key, val in wanted.items():
        r = link.q("CFG? " + key)
        if not r.startswith("OK "):
            log.warning("ESP 不认识 CFG 键 %s（%s），跳过", key, r)
            continue
        cur = r[3:].split("=", 1)[1] if "=" in r else ""
        if key in SECRET_KEYS:
            same = (cur == "***") == (val != "") and st.get(key.lower()) == _digest(val)
        else:
            same = cur == val
        if same:
            continue
        r = link.q("CFG %s %s" % (key, quote(val)))
        if not r.startswith("OK"):
            log.error("CFG %s 写入失败：%s", key, r)
            continue
        changed.append(key)
        if key in SECRET_KEYS:
            st[key.lower()] = _digest(val)
        log.info("CFG %s：%s → %s", key, cur, "***" if key in SECRET_KEYS else val)
    if changed:
        r = link.q("CFG SAVE")
        if not r.startswith("OK"):
            raise EspError("CFG SAVE 失败：%s" % r)
        _save_state(state_path, st)
    return changed


def main(argv=None):
    from . import config
    from .esplink import EspLink
    ap = argparse.ArgumentParser(description="把配置文件 [esp_cfg] 节写进 ESP")
    ap.add_argument("--port", required=True, help="ESP 原生 USB 口，如 COM8 或 /dev/mis01-esp")
    ap.add_argument("--conf", required=True)
    ap.add_argument("--state", default="espcfg_state.json")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    c = config.load(a.conf)
    if not c.esp_cfg:
        print("配置文件里 [esp_cfg] 节是空的")
        return 1
    link = EspLink(a.port)
    link.start()
    if not link.wait_connected(5):
        print("连不上 ESP：%s" % a.port)
        return 1
    try:
        ch = sync(link, c.esp_cfg, a.state)
        print("已更新：%s" % (", ".join(ch) if ch else "无（都一致）"))
    finally:
        link.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
