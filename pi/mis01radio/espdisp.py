"""经 mis01d 的套接字让 ESP 在 IV-18 上显示电台（规格 6.8 VFD RADIO）。

放电台时每 30 s 重发 VFD RADIO "<文字>" T=90：mis01d 或 ESP 重启、USB 重连后自动恢复；
本服务停了 90 s 后 ESP 自己去掉电台项。
"""
import logging
import socket
import threading

log = logging.getLogger("esp")

REFRESH_S = 30
TIMEOUT_S = 90


class EspDisplay:
    def __init__(self, sock_path):
        self.sock_path = sock_path
        self._text = None
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._last_err = None
        threading.Thread(target=self._loop, name="esp-refresh", daemon=True).start()

    def _send(self, line):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(6)
                s.connect(self.sock_path)
                s.sendall((line + "\n").encode())
                r = s.makefile("rb").readline().decode("utf-8", "replace").strip()
        except OSError as e:
            r = "ERR SOCK %s" % e
        if r.startswith("OK"):
            if self._last_err:
                log.info("ESP 显示恢复")
            self._last_err = None
        elif r != self._last_err:
            log.warning("%s → %s", line, r)
            self._last_err = r
        return r

    def set_station(self, text):
        with self._lock:
            self._text = text
        self._wake.set()

    def clear(self):
        with self._lock:            # 和刷新线程互斥：不会出现 OFF 之后又补发一条旧的 RADIO
            self._text = None
            self._send("VFD RADIO OFF")

    def flash(self, text, seconds):
        self._send('VFD SHOW "%s" T=%d' % (text, max(1, seconds)))

    def _loop(self):
        while True:
            with self._lock:
                if self._text is not None:
                    self._send('VFD RADIO "%s" T=%d' % (self._text, TIMEOUT_S))
            self._wake.wait(REFRESH_S)
            self._wake.clear()
