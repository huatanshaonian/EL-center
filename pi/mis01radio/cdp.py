"""Chrome DevTools 协议的最小客户端（只用标准库：自己做 WebSocket 握手和分帧）。"""
import base64
import json
import os
import socket
import struct
import threading
import urllib.parse
import urllib.request


class CdpError(Exception):
    pass


def http_json(port, path, timeout=3):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=timeout) as r:
        return json.loads(r.read().decode())


class WebSocket:
    def __init__(self, url, timeout=10):
        u = urllib.parse.urlparse(url)
        self.sock = socket.create_connection((u.hostname, u.port or 80), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = ("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n") % (u.path or "/", u.hostname, u.port or 80, key)
        self.sock.sendall(req.encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise CdpError("握手时连接断开")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise CdpError("握手失败：%r" % head[:80])
        self._buf = head.split(b"\r\n\r\n", 1)[1]
        self.sock.settimeout(None)
        self._wlock = threading.Lock()

    def _read(self, n):
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise CdpError("连接断开")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def recv(self):
        """读一条完整消息（处理分片），返回 str；收到关闭帧抛 CdpError。"""
        parts = []
        while True:
            b0, b1 = self._read(2)
            op, fin, n = b0 & 0x0F, b0 & 0x80, b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            mask = self._read(4) if b1 & 0x80 else None
            data = self._read(n)
            if mask:
                data = bytes(c ^ mask[i % 4] for i, c in enumerate(data))
            if op == 8:
                raise CdpError("对方关闭连接")
            if op == 9:                       # ping → pong
                self._send(10, data)
                continue
            if op in (0, 1, 2):
                parts.append(data)
                if fin:
                    return b"".join(parts).decode("utf-8", "replace")

    def _send(self, op, data):
        mask = os.urandom(4)
        n = len(data)
        if n < 126:
            head = struct.pack(">BB", 0x80 | op, 0x80 | n)
        elif n < 65536:
            head = struct.pack(">BBH", 0x80 | op, 0x80 | 126, n)
        else:
            head = struct.pack(">BBQ", 0x80 | op, 0x80 | 127, n)
        body = bytes(c ^ mask[i % 4] for i, c in enumerate(data))
        with self._wlock:
            self.sock.sendall(head + mask + body)

    def send_text(self, s):
        self._send(1, s.encode())

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class CdpSession:
    """连到一个页面目标；call() 同步等结果，事件丢掉。"""

    def __init__(self, ws_url):
        self.ws = WebSocket(ws_url)
        self._id = 0
        self._lock = threading.Lock()
        self._waiting = {}
        self.alive = True
        threading.Thread(target=self._reader, name="cdp-reader", daemon=True).start()

    def _reader(self):
        try:
            while True:
                msg = json.loads(self.ws.recv())
                ev = self._waiting.pop(msg.get("id"), None)
                if ev:
                    ev[1] = msg
                    ev[0].set()
        except (CdpError, OSError, ValueError):
            pass
        self.alive = False
        for ev in list(self._waiting.values()):
            ev[0].set()

    def call(self, method, timeout=15, **params):
        if not self.alive:
            raise CdpError("页面连接已断")
        with self._lock:
            self._id += 1
            mid = self._id
        ev = [threading.Event(), None]
        self._waiting[mid] = ev
        self.ws.send_text(json.dumps({"id": mid, "method": method, "params": params}))
        if not ev[0].wait(timeout):
            self._waiting.pop(mid, None)
            raise CdpError("%s 超时" % method)
        msg = ev[1]
        if msg is None:
            raise CdpError("页面连接已断")
        if "error" in msg:
            raise CdpError("%s：%s" % (method, msg["error"].get("message")))
        return msg.get("result", {})

    def evaluate(self, js, timeout=15):
        r = self.call("Runtime.evaluate", timeout=timeout, expression=js, returnByValue=True, awaitPromise=True,
                      userGesture=True)
        if "exceptionDetails" in r:
            raise CdpError("JS 出错：%s" % r["exceptionDetails"].get("text", ""))
        return r.get("result", {}).get("value")

    def close(self):
        self.alive = False
        self.ws.close()
