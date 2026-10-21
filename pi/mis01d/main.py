"""mis01d 主程序：把各部分接起来。systemd 服务 mis01d.service 运行 python3 -m mis01d。"""
import argparse
import logging
import signal
import sys
import threading
import time

from . import VERSION, cfgsync, config, timesync
from .esplink import EspError, EspLink
from .fpga import Fpga
from .power import Power

log = logging.getLogger("mis01d")


class Daemon:
    def __init__(self, cfg):
        self.cfg = cfg
        self.fpga = Fpga(cfg.fpga_port, cfg.fpga_baud)
        self.link = EspLink(cfg.esp_port, on_report=self.on_report, on_connect=self.on_connect,
                            retry_s=cfg.esp_retry_s)
        if cfg.dry_run:
            from .gpio import FakeLine
            line = FakeLine()
        else:
            from .gpio import InputLine
            line = InputLine(cfg.shdn_chip, cfg.shdn_line, pull_up=True)
        self.line = line
        self.power = Power(line, cfg.shdn_debounce_ms, cfg.dry_run)
        self.ctl = None
        self._stop = threading.Event()
        self._last_time_sync = 0.0

    # ESP 连上（含 ESP 重启后重新枚举）：对时、核对配置
    def on_connect(self, link):
        try:
            r = link.q("VER")
            log.info("ESP %s", r)
            # 钮子在 Pi 开机途中就关了：!SHUTDOWN 发在我们连上之前、22 脚也一直低（看门狗不认），
            # 连上时查一次，ESP 已在 SHUT 就照样关机，免得 60 s 后被硬断电
            st = link.q("?")
            if " PWR=SHUT" in " " + st[3:]:
                self.power.request_poweroff("连上时 ESP 已在 SHUT（主机钮子已关）")
        except EspError as e:
            log.warning("VER/? 失败：%s", e)
        if timesync.sync(link):
            self._last_time_sync = time.monotonic()
        if self.cfg.esp_cfg:
            try:
                ch = cfgsync.sync(link, self.cfg.esp_cfg, self.cfg.state_path)
                if ch:
                    log.info("已更新 ESP 配置：%s", ", ".join(ch))
            except EspError as e:
                log.warning("配置核对失败：%s", e)

    def on_report(self, line):
        if line.startswith("!SHUTDOWN"):
            self.power.request_poweroff("ESP 上报 !SHUTDOWN（主机钮子关）")

    def run(self):
        log.info("mis01d %s 启动", VERSION)
        if self.cfg.fpga_on_at_start and not self.cfg.dry_run:
            self.fpga.power_on()
        self.power.start()
        self.link.start()
        try:
            from .ctlsock import CtlServer
            self.ctl = CtlServer(self.cfg.sock_path, self.link, self.cfg.sock_group)
            self.ctl.start()
        except (ImportError, OSError, AttributeError) as e:
            log.warning("命令套接字不可用：%s", e)
        period = self.cfg.time_sync_h * 3600
        while not self._stop.wait(5.0):
            now = time.monotonic()
            if self.link.connected and now - self._last_time_sync >= period:
                if timesync.sync(self.link):
                    self._last_time_sync = now
        self._shutdown()

    def stop(self, *_):
        self._stop.set()

    def _shutdown(self):
        if self.power.powering_off():
            log.warning("系统关机：FPGA R0 → ESP SHUTDOWN")
            if not self.cfg.dry_run:
                self.fpga.power_off()
            try:
                log.info("ESP SHUTDOWN → %s", self.link.q("SHUTDOWN", 2.0))
            except EspError as e:
                log.warning("ESP SHUTDOWN 失败：%s", e)
        else:
            log.info("服务停止（非关机），不动 FPGA 和 ESP")
        if self.ctl:
            self.ctl.stop()
        self.power.stop()
        self.link.stop()
        self.line.close()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mis01d")
    ap.add_argument("--conf", default="/etc/mis01/mis01.conf")
    ap.add_argument("--port", help="覆盖配置里的 ESP 口（调试用）")
    ap.add_argument("--dry-run", action="store_true", help="不碰 GPIO、FPGA，不真的关机")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s", stream=sys.stdout)
    cfg = config.load(a.conf)
    if a.port:
        cfg.esp_port = a.port
    if a.dry_run:
        cfg.dry_run = True
    d = Daemon(cfg)
    signal.signal(signal.SIGTERM, d.stop)
    signal.signal(signal.SIGINT, d.stop)
    d.run()
    return 0
