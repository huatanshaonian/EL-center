"""播放控制：同一时间放一台；进程掉了自动重开（退避）；放的时候让 IV-18 显示电台文字。"""
import logging
import threading
import time

from . import audio
from .players import TYPES

log = logging.getLogger("radio")

TICK_S = 1.5
BACKOFF = (3, 10, 30, 60)


class Radio:
    def __init__(self, store, browser, esp):
        self.store = store
        self.browser = browser
        self.esp = esp
        self.lock = threading.RLock()
        self.player = None
        self.station = None
        self.status = {"state": "stopped", "title": "", "detail": ""}
        self.fails = 0
        self.retry_at = 0.0
        self.vol_pending = False
        self.card = None
        self.apply_audio()

    # ---- 声音设置
    def apply_audio(self):
        s = self.store.settings
        self.card = audio.pick_card(s.get("alsa_card"))
        audio.write_asoundrc(self.card, s.get("alsa_dmix", True))
        self.vol_pending = True

    def set_volume(self, v, show=True):
        v = max(0, min(100, int(v)))
        self.store.update_settings({"volume": v})
        self.vol_pending = not audio.set_volume(self.card, v)
        if show:
            self.esp.flash("UOL%4d" % v, self.store.settings.get("vfd_volume_s", 2))
        return v

    # ---- 播放
    def play(self, sid):
        st = self.store.get(sid)
        if not st:
            return "没有电台 %s" % sid
        with self.lock:
            self._stop_player()
            self.station = st
            self.fails = 0
            self.store.update_settings({"last_id": sid})
            self.esp.set_station(st["vfd"])
            self._start()
        return None

    def _start(self):
        st = self.station
        cls = TYPES.get(st["type"])
        self.status = {"state": "starting", "title": "", "detail": "启动中"}
        try:
            if not isinstance(self.player, cls):
                self.player = cls(self)
            self.player.start(st)
            self.vol_pending = True
        except Exception as e:          # noqa: BLE001 —— 任何启动失败都按掉线处理，走退避重试
            log.warning("启动 %s 失败：%s", st["name"], e)
            self._failed(str(e))

    def _failed(self, why):
        delay = BACKOFF[min(self.fails, len(BACKOFF) - 1)]
        self.fails += 1
        self.retry_at = time.time() + delay
        self.status = {"state": "retry", "title": "", "detail": "%s；%d 秒后重试" % (why, delay)}

    def _stop_player(self):
        if self.player:
            try:
                self.player.stop()
            except Exception as e:      # noqa: BLE001
                log.warning("停止播放器出错：%s", e)

    def stop(self):
        with self.lock:
            self._stop_player()
            self.station = None
            self.status = {"state": "stopped", "title": "", "detail": ""}
        self.esp.clear()

    def step(self, d):
        lst = self.store.enabled()
        if not lst:
            return "没有启用的电台"
        ids = [s["id"] for s in lst]
        cur = self.station["id"] if self.station else None
        i = (ids.index(cur) + d) % len(ids) if cur in ids else (0 if d > 0 else len(ids) - 1)
        return self.play(ids[i])

    def restart_if_current(self, sid):
        """网页上改了正在放的电台：按新设置重开。"""
        if self.station and self.station["id"] == sid:
            self.play(sid)

    def snapshot(self):
        st = self.station
        return {"station": st["id"] if st else "", "name": st["name"] if st else "", "vfd": st["vfd"] if st else "",
                **self.status, "volume": self.store.settings["volume"], "browser": self.browser.running()}

    # ---- 后台循环
    def run(self):
        s = self.store.settings
        if s.get("resume") and s.get("last_id") and self.store.get(s["last_id"]):
            log.info("接着放上次的电台 %s", s["last_id"])
            self.play(s["last_id"])
        while True:
            time.sleep(TICK_S)
            try:
                self._tick()
            except Exception:           # noqa: BLE001 —— 循环不能死
                log.exception("控制循环出错")

    def _tick(self):
        with self.lock:
            if self.station and self.player:
                if self.status["state"] == "retry":
                    if time.time() >= self.retry_at:
                        log.info("重开 %s（第 %d 次）", self.station["name"], self.fails)
                        self._start()
                else:
                    st = self.player.poll()
                    if st["state"] == "dead":
                        log.warning("%s：%s", self.station["name"], st["detail"])
                        self._stop_player()
                        self._failed(st["detail"])
                    else:
                        if st["state"] == "playing":
                            self.fails = 0
                        self.status = st
                if self.vol_pending:
                    self.vol_pending = not audio.set_volume(self.card, self.store.settings["volume"])
            in_browser = bool(self.station and self.station["type"] == "browser")
        self.browser.idle_check(in_browser)
