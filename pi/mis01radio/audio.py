"""声音输出：Pi 耳机口（ES8316）→ PAM8403 → 两只喇叭。

服务启动时在本用户的 ~/.asoundrc 里定义 ALSA 设备 "mis01"：softvol（音量控件 "MIS01 Radio"）→ dmix → 耳机口声卡。
mpv 和 Chromium 都输出到 "mis01"，音量统一用 amixer 调这个控件，与播放器无关。
"""
import logging
import os
import re
import subprocess

log = logging.getLogger("audio")

PCM = "mis01"
CONTROL = "MIS01 Radio"


def list_cards():
    """[(编号, 短名, 描述)]，来自 /proc/asound/cards。"""
    out = []
    try:
        with open("/proc/asound/cards") as f:
            for line in f:
                m = re.match(r"\s*(\d+)\s+\[(\S+)\s*\]:\s*(.*)", line)
                if m:
                    out.append((int(m.group(1)), m.group(2), m.group(3).strip()))
    except OSError:
        pass
    return out


def pick_card(setting):
    cards = list_cards()
    if setting and setting != "auto":
        return setting
    for _, name, desc in cards:
        if "es8316" in (name + desc).lower():
            return name
    for _, name, desc in cards:          # 没找到耳机口：取第一块不是 HDMI 的
        if "hdmi" not in (name + desc).lower():
            return name
    return cards[0][1] if cards else "0"


def write_asoundrc(card, dmix=True):
    slave = '"dmix:CARD=%s,DEV=0"' % card if dmix else '"hw:CARD=%s,DEV=0"' % card
    text = """# 由 mis01radio 自动生成，改设置请到管理网页（重启服务时会覆盖）
pcm.%s {
    type softvol
    slave.pcm "%s_out"
    control { name "%s"; card %s }
    min_dB -45.0
    max_dB 0.0
    resolution 101
}
pcm.%s_out {
    type plug
    slave.pcm %s
}
""" % (PCM, PCM, CONTROL, card, PCM, slave)
    path = os.path.expanduser("~/.asoundrc")
    try:
        with open(path, "w") as f:
            f.write(text)
        log.info("ALSA 输出：声卡 %s（%s）", card, "dmix" if dmix else "独占")
    except OSError as e:
        log.error("写 %s 失败：%s", path, e)


def set_volume(card, percent):
    """softvol 控件要设备被打开过一次才出现：失败返回 False，播放器启动后再调一次。"""
    v = max(0, min(100, int(percent)))
    try:
        r = subprocess.run(["amixer", "-q", "-c", str(card), "sset", CONTROL, "%d%%" % v],
                           capture_output=True, timeout=5)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
