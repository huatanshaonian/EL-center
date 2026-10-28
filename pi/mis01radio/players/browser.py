"""只能在网页上播放的电台（如 BR24 在德国以外要登录）：Pi 上的 Chromium 打开网页播放。

先在管理网页的“远程画面”里登录一次（配置目录固定，登录状态保留）。
打开网页后反复执行“播放 JS”，直到页面上有音频在播（或 check_js 返回真）。
"""
import logging
import time

from ..cdp import CdpError
from .base import Player

log = logging.getLogger("browser-player")

# playing = 有音频在出声；started = 已经点过播放（在加载）——这时不再点，免得把播放键又点成暂停
STATE_JS = ("(() => { const m = [...document.querySelectorAll('audio,video')];"
            " return [m.some(e => !e.paused && !e.ended && e.readyState > 2), m.some(e => !e.paused && !e.ended)]; })()")
RETRY_S = 8


class BrowserPlayer(Player):
    TYPE = "browser"
    LABEL = "网页（Pi 上的浏览器）"
    FIELDS = [
        {"key": "page_url", "label": "网页地址", "required": True, "hint": "电台的直播网页"},
        {"key": "play_js", "label": "播放 JS", "multiline": True,
         "hint": "打开网页后执行，用来点播放键，例 document.querySelector('[aria-label=\"Livestream abspielen\"]')?.click()。"
                 "留空就在远程画面里自己点"},
        {"key": "check_js", "label": "判断在播的 JS", "multiline": True,
         "hint": "返回真表示在播。留空 = 页面上有 audio/video 元素在播（网站用 WebAudio 时要自己写）"},
    ]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.station = None
        self.opened = 0.0
        self.last_try = 0.0
        self.tries = 0
        self.playing = False

    def start(self, station):
        self.station = station
        self.tries = 0
        self.playing = False
        self.ctx.browser.navigate(station["page_url"])
        self.opened = time.time()
        self.last_try = self.opened - RETRY_S + 3     # 网页打开 3 s 后第一次点播放

    def stop(self):
        if self.station:
            try:                            # 浏览器不关（下一台可能也是网页），只是离开电台页
                if self.ctx.browser.running():
                    self.ctx.browser.navigate("about:blank")
            except CdpError:
                pass
        self.station = None

    def poll(self):
        b = self.ctx.browser
        if not b.running():
            return {"state": "dead", "title": "", "detail": "浏览器退出了"}
        st = self.station
        try:
            ok, started = b.evaluate(STATE_JS)
            if st.get("check_js"):
                ok = bool(b.evaluate(st["check_js"]))
                started = started or ok
        except (CdpError, TypeError, ValueError) as e:
            return {"state": "starting", "title": "", "detail": str(e)}
        if ok:
            if not self.playing:
                log.info("网页在播：%s", st["name"])
            self.playing = True
            return {"state": "playing", "title": "", "detail": ""}
        self.playing = False
        now = time.time()
        if started:
            self.last_try = now             # 在加载：等它，从现在起重新计时
        elif st.get("play_js") and now - self.last_try > RETRY_S and now - self.opened > 3:
            self.last_try = now
            self.tries += 1
            try:
                b.evaluate(st["play_js"])
            except CdpError as e:
                log.info("播放 JS 出错（第 %d 次）：%s", self.tries, e)
        if self.tries >= 5 or now - self.opened > 45 or (not st.get("play_js") and now - self.opened > 15):
            return {"state": "stalled", "title": "",
                    "detail": "网页打开了但没在播：在远程画面里看看（要不要登录、点播放键）"}
        return {"state": "starting", "title": "", "detail": "打开网页中"}
