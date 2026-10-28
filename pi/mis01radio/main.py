import argparse
import logging
import signal
import sys
import threading

from . import __version__
from .browserhost import BrowserHost
from .controller import Radio
from .espdisp import EspDisplay
from .players import TYPES
from .store import Store
from .web import serve


class App:
    pass


def main():
    ap = argparse.ArgumentParser(description="MIS-01 网络电台服务")
    ap.add_argument("--data", default="/var/lib/mis01radio/radio.json", help="电台表与设置")
    ap.add_argument("--port", type=int, default=8080, help="管理网页端口")
    ap.add_argument("--esp-sock", default="/run/mis01/esp.sock", help="mis01d 的命令套接字")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s", stream=sys.stdout)
    log = logging.getLogger("main")
    log.info("mis01radio %s", __version__)

    app = App()
    app.store = Store(args.data, TYPES)
    app.esp = EspDisplay(args.esp_sock)
    app.browser = BrowserHost(app.store)
    app.radio = Radio(app.store, app.browser, app.esp)
    serve(app, args.port)

    done = threading.Event()

    def on_term(*_):
        done.set()

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)
    threading.Thread(target=app.radio.run, name="radio", daemon=True).start()
    done.wait()
    log.info("退出：停止播放")
    app.radio.stop()
    app.browser.stop()
    return 0
