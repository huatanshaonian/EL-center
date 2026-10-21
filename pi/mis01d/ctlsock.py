"""本机其他程序给 ESP 发命令的入口：Unix 套接字，一行一条命令，回一行应答（多行结果如 LOG? 先回 # 行）。

例：echo "EYE B 600 T=1" | socat - UNIX-CONNECT:/run/mis01/esp.sock，或用 mis01ctl。
"""
import grp
import logging
import os
import socket
import threading

from .esplink import EspError

log = logging.getLogger("sock")


class CtlServer:
    def __init__(self, path, link, group="dialout"):
        self.path = path
        self.link = link
        self.group = group
        self._srv = None

    def start(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(self.path)
        try:
            os.chown(self.path, -1, grp.getgrnam(self.group).gr_gid)
            os.chmod(self.path, 0o660)
        except (KeyError, PermissionError) as e:
            log.warning("套接字权限设置失败：%s", e)
        s.listen(8)
        self._srv = s
        threading.Thread(target=self._accept, name="ctl-accept", daemon=True).start()
        log.info("命令套接字 %s", self.path)

    def stop(self):
        if self._srv:
            try:
                self._srv.close()
                os.unlink(self.path)
            except OSError:
                pass

    def _accept(self):
        while True:
            try:
                c, _ = self._srv.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(c,), daemon=True).start()

    def _serve(self, c):
        with c, c.makefile("rwb", buffering=0) as f:
            for raw in f:
                line = raw.decode("utf-8", "replace").strip()
                if not line:
                    continue
                try:
                    r, extra = self.link.command(line, timeout=5.0)
                    out = extra + [r]
                except EspError as e:
                    out = ["ERR LINK %s" % e]
                try:
                    f.write(("\n".join(out) + "\n").encode("utf-8"))
                except OSError:
                    return
