"""Pi 已 NTP 同步时给 ESP 发 TIME（本地时间，规格 6.6）。"""
import datetime
import logging
import subprocess

from .esplink import EspError

log = logging.getLogger("time")


def pi_ntp_synced():
    try:
        r = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() == "yes"
    except (OSError, subprocess.SubprocessError):
        return False


def sync(link, force=False):
    """返回 True = 已对时。Pi 自己没同步时不发（免得把错的时间写进 RTC），除非 force。"""
    if not force and not pi_ntp_synced():
        log.info("Pi 尚未 NTP 同步，暂不给 ESP 对时")
        return False
    now = datetime.datetime.now().replace(microsecond=0)
    try:
        r = link.q("TIME " + now.isoformat())
    except EspError as e:
        log.warning("对时失败：%s", e)
        return False
    log.info("ESP 对时 %s → %s", now.isoformat(), r)
    return r.startswith("OK")
