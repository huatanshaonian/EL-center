"""Pi 上的 Chromium：网页电台用它播放，管理网页的“远程画面”也操作它（在里面登录电台网站）。

只开一个浏览器、一个标签页；配置目录固定（~/chromium），登录状态一直保留。
"""
import base64
import logging
import os
import shutil
import signal
import subprocess
import threading
import time

from . import audio
from .cdp import CdpError, CdpSession, http_json

log = logging.getLogger("browser")

PORT = 9223           # 只绑 127.0.0.1
W, H = 1280, 800


def find_chromium():
    for name in ("chromium", "chromium-browser", "google-chrome"):
        p = shutil.which(name)
        if p:
            return p
    return None


class BrowserHost:
    def __init__(self, store):
        self.store = store
        self.proc = None
        self.page = None
        self.lock = threading.RLock()
        self.last_view = 0.0       # 远程画面最后一次被看的时间
        self.profile = os.path.expanduser("~/chromium")

    # ---- 进程
    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def _cmd(self):
        exe = find_chromium()
        if not exe:
            raise CdpError("没装 Chromium（sudo apt install chromium）")
        s = self.store.settings
        args = [exe, "--user-data-dir=" + self.profile, "--remote-debugging-port=%d" % PORT,
                "--remote-debugging-address=127.0.0.1", "--no-first-run", "--no-default-browser-check",
                "--autoplay-policy=no-user-gesture-required", "--window-size=%d,%d" % (W, H),
                "--alsa-output-device=" + audio.PCM, "--disable-features=Translate,MediaRouter",
                "--password-store=basic", "--lang=zh-CN"]
        if s.get("proxy"):
            args.append("--proxy-server=" + s["proxy"])
        if s.get("browser_mode") == "xvfb" and shutil.which("xvfb-run"):
            return ["xvfb-run", "-a", "-s", "-screen 0 %dx%dx24" % (W, H)] + args + ["about:blank"]
        return args + ["--headless=new", "about:blank"]

    def ensure(self):
        """浏览器没开就开，返回页面会话。"""
        with self.lock:
            if self.running() and self.page and self.page.alive:
                return self.page
            if not self.running():
                self._start()
            self.page = self._connect()
            return self.page

    def _start(self):
        cmd = self._cmd()
        log.info("启动浏览器：%s", " ".join(cmd[:3]))
        # 自己的进程组：关的时候连同 xvfb、渲染进程一起关
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     start_new_session=True)

    def _connect(self):
        t0 = time.time()
        while time.time() - t0 < 30:
            if not self.running():
                raise CdpError("浏览器启动后退出了（看 journalctl -u mis01radio）")
            try:
                pages = [t for t in http_json(PORT, "/json/list") if t.get("type") == "page"]
                if pages:
                    return CdpSession(pages[0]["webSocketDebuggerUrl"])
                http_json(PORT, "/json/new?about:blank")
            except (OSError, ValueError, CdpError):
                pass
            time.sleep(0.5)
        raise CdpError("连不上浏览器调试口")

    def stop(self):
        with self.lock:
            if self.page:
                self.page.close()
                self.page = None
            if self.running():
                log.info("关浏览器")
                try:
                    os.killpg(self.proc.pid, signal.SIGTERM)
                    self.proc.wait(8)
                except (OSError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(self.proc.pid, signal.SIGKILL)
                    except OSError:
                        pass
            self.proc = None

    def idle_check(self, playing_in_browser):
        """控制循环定时调用：没在放网页电台、远程画面也很久没看了，就关掉浏览器省资源。"""
        idle = self.store.settings.get("browser_idle_min", 10) * 60
        if self.running() and not playing_in_browser and time.time() - self.last_view > idle:
            self.stop()

    # ---- 页面操作
    def navigate(self, url):
        p = self.ensure()
        p.call("Page.navigate", url=url)

    def evaluate(self, js):
        return self.ensure().evaluate(js)

    def screenshot(self):
        self.last_view = time.time()
        p = self.ensure()
        r = p.call("Page.captureScreenshot", format="jpeg", quality=55)
        return base64.b64decode(r["data"])

    def info(self):
        if not (self.running() and self.page and self.page.alive):
            return {"running": self.running(), "url": "", "title": ""}
        try:
            v = self.page.evaluate("[location.href, document.title]", timeout=3)
            return {"running": True, "url": v[0], "title": v[1]}
        except CdpError:
            return {"running": True, "url": "", "title": ""}

    def click(self, xr, yr):
        self.last_view = time.time()
        p = self.ensure()
        x, y = xr * W, yr * H
        p.call("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
        for t in ("mousePressed", "mouseReleased"):
            p.call("Input.dispatchMouseEvent", type=t, x=x, y=y, button="left", clickCount=1)

    def scroll(self, dy):
        self.last_view = time.time()
        self.ensure().call("Input.dispatchMouseEvent", type="mouseWheel", x=W / 2, y=H / 2, deltaX=0, deltaY=dy)

    def type_text(self, text):
        self.last_view = time.time()
        self.ensure().call("Input.insertText", text=text)

    KEYS = {"Enter": (13, "\r"), "Tab": (9, "\t"), "Backspace": (8, ""), "Escape": (27, ""),
            "ArrowUp": (38, ""), "ArrowDown": (40, ""), "ArrowLeft": (37, ""), "ArrowRight": (39, "")}

    def key(self, name):
        if name not in self.KEYS:
            raise CdpError("不支持的键 %s" % name)
        self.last_view = time.time()
        code, text = self.KEYS[name]
        p = self.ensure()
        down = dict(type="keyDown", key=name, code=name, windowsVirtualKeyCode=code, nativeVirtualKeyCode=code)
        if text:
            down["text"] = text
        p.call("Input.dispatchKeyEvent", **down)
        p.call("Input.dispatchKeyEvent", type="keyUp", key=name, code=name, windowsVirtualKeyCode=code,
               nativeVirtualKeyCode=code)

    def back(self):
        self.last_view = time.time()
        self.ensure().evaluate("history.back()")
