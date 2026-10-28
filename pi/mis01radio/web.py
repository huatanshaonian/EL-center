"""管理网页与接口（标准库 http.server）。设了密码时局域网访问要 Basic 认证（用户名随意），本机（mis01ctl）不用。"""
import base64
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import audio, vfdtext
from .cdp import CdpError
from .players import TYPES
from .store import check_password

log = logging.getLogger("web")

WWW = os.path.join(os.path.dirname(__file__), "www")


class Handler(BaseHTTPRequestHandler):
    app = None              # main 里设：有 store、radio、browser
    server_version = "mis01radio"

    def log_message(self, fmt, *args):
        pass

    # ---- 基础
    def _authed(self):
        stored = self.app.store.settings.get("password_hash")
        if not stored or self.client_address[0] in ("127.0.0.1", "::1"):
            return True
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic "):
            try:
                pw = base64.b64decode(h[6:]).decode("utf-8", "replace").partition(":")[2]
            except ValueError:
                return False
            return check_password(stored, pw)
        return False

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 65536:
            raise ValueError("请求太大")
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def _guard(self):
        if self._authed():
            return True
        self._send(401, {"error": "要密码"}, extra={"WWW-Authenticate": 'Basic realm="MIS-01 radio"'})
        return False

    # ---- GET
    def do_GET(self):
        if not self._guard():
            return
        path = self.path.split("?", 1)[0]
        a = self.app
        if path in ("/", "/index.html"):
            with open(os.path.join(WWW, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path == "/api/state":
            return self._send(200, {"status": a.radio.snapshot(), "stations": a.store.stations,
                                    "settings": a.store.public_settings(),
                                    "types": [t.describe() for t in TYPES.values()],
                                    "cards": [{"id": n, "desc": d} for _, n, d in audio.list_cards()],
                                    "card_in_use": a.radio.card})
        if path == "/api/status":
            return self._send(200, a.radio.snapshot())
        if path == "/api/browser/shot":
            try:
                return self._send(200, a.browser.screenshot(), "image/jpeg")
            except CdpError as e:
                return self._send(503, {"error": str(e)})
        if path == "/api/browser/info":
            return self._send(200, a.browser.info())
        self._send(404, {"error": "没有这个地址"})

    # ---- POST：统一回 {"ok": true} 或 {"error": "..."}
    def do_POST(self):
        if not self._guard():
            return
        try:
            d = self._json_body()
            err = self._post(self.path.split("?", 1)[0], d)
        except (ValueError, KeyError, TypeError) as e:
            err = "参数不对：%s" % e
        except CdpError as e:
            err = str(e)
        if err == 404:
            return self._send(404, {"error": "没有这个地址"})
        self._send(200 if not err else 400, {"ok": True, "status": self.app.radio.snapshot()} if not err else {"error": err})

    def _post(self, path, d):
        a = self.app
        r, s, b = a.radio, a.store, a.browser
        if path == "/api/play":
            return r.play(d["id"])
        if path == "/api/stop":
            return r.stop()
        if path == "/api/next":
            return r.step(1)
        if path == "/api/prev":
            return r.step(-1)
        if path == "/api/volume":
            v = int(d["volume"]) if "volume" in d else s.settings["volume"] + int(d.get("delta", 0))
            r.set_volume(v)
            return None
        if path == "/api/station/save":
            err = s.upsert(d["station"], d.get("old_id") or None)
            if not err:
                r.restart_if_current(d.get("old_id") or d["station"]["id"])
            return err
        if path == "/api/station/delete":
            if r.station and r.station["id"] == d["id"]:
                r.stop()
            s.delete(d["id"])
            return None
        if path == "/api/station/order":
            s.reorder(list(d["ids"]))
            return None
        if path == "/api/vfd/check":
            return vfdtext.check(str(d.get("text", "")))
        if path == "/api/vfd/preview":          # 在 IV-18 上试显示几秒
            err = vfdtext.check(str(d.get("text", "")))
            if not err:
                a.esp.flash(d["text"], 4)
            return err
        if path == "/api/settings":
            old = dict(s.settings)
            s.update_settings(d)
            if (old["alsa_card"], old["alsa_dmix"]) != (s.settings["alsa_card"], s.settings["alsa_dmix"]):
                r.apply_audio()
                if r.station:
                    r.play(r.station["id"])
            if (old["proxy"], old["browser_mode"]) != (s.settings["proxy"], s.settings["browser_mode"]):
                b.stop()                        # 下次用到时按新设置重开
                if r.station:
                    r.play(r.station["id"])
            return None
        if path == "/api/password":
            s.set_password(str(d.get("password", "")))
            return None
        # 远程画面
        if path == "/api/browser/open":
            url = str(d.get("url") or "").strip()
            if url:
                b.navigate(url if "://" in url else "https://" + url)
            else:
                b.ensure()
            b.last_view = time.time()
            return None
        if path == "/api/browser/click":
            b.click(float(d["x"]), float(d["y"]))
            return None
        if path == "/api/browser/type":
            b.type_text(str(d["text"]))
            return None
        if path == "/api/browser/key":
            b.key(str(d["key"]))
            return None
        if path == "/api/browser/scroll":
            b.scroll(float(d["dy"]))
            return None
        if path == "/api/browser/back":
            b.back()
            return None
        if path == "/api/browser/close":
            if r.station and r.station["type"] == "browser":
                r.stop()
            b.stop()
            return None
        return 404


def serve(app, port):
    Handler.app = app
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, name="web", daemon=True).start()
    log.info("管理网页 http://<Pi>:%d", port)
    return srv
