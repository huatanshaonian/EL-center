"""关机握手（规格 F1、第 4 节）。

触发关机的两路，先到先执行：
  1. PI_SHDN_REQ（40 针 22 脚）持续低 ≥ 500 ms（ESP 在主机钮子关时拉低，开漏、Pi 侧内部上拉）；
  2. ESP 主动上报 !SHUTDOWN。
关机（poweroff/halt）时服务停止前：FPGA 发 R0 → ESP 发 SHUTDOWN。reboot 不发。
PI_RUN（16 脚）不在这里管：由设备树 gpio-hog 拉高到断电（overlay/mis01-pi-run.dts）。
"""
import logging
import subprocess
import threading
import time

log = logging.getLogger("power")


class Power:
    def __init__(self, line, debounce_ms=500, dry_run=False):
        self.line = line
        self.debounce_ms = debounce_ms
        self.dry_run = dry_run
        self._requested = threading.Event()
        self._stop = threading.Event()

    def start(self):
        lvl = self.line.get()
        log.info("PI_SHDN_REQ 当前电平 %d（无人拉低时应为 1）", lvl)
        threading.Thread(target=self._watch, name="shdn-watch", daemon=True).start()

    def stop(self):
        self._stop.set()

    def _watch(self):
        # 必须先见过一次高，之后的低才算关机请求：GPIO1_D0 上电默认内部下拉（原理图 _d），
        # 万一上拉没设上，线会一直读低——不能因此一启动就把 Pi 关掉。
        low_since = None
        armed = False
        warned = False
        t0 = time.monotonic()
        while not self._stop.is_set():
            try:
                v = self.line.get()
            except Exception as e:
                log.error("读 PI_SHDN_REQ 失败：%s", e)
                self._stop.wait(1.0)
                continue
            now = time.monotonic()
            if not armed:
                if v == 1:
                    armed = True
                    log.info("PI_SHDN_REQ 已读到高，开始监视")
                elif not warned and now - t0 > 5:
                    warned = True
                    log.error("PI_SHDN_REQ 启动后一直为低：上拉没生效或 ESP 正在拉低。暂不据此关机，只认 !SHUTDOWN")
                self._stop.wait(0.02)
                continue
            if v == 0:
                if low_since is None:
                    low_since = now
                elif (now - low_since) * 1000 >= self.debounce_ms:
                    self.request_poweroff("PI_SHDN_REQ 持续低 %d ms" % self.debounce_ms)
                    low_since = None
                    self._stop.wait(5.0)
            else:
                low_since = None
            self._stop.wait(0.02)

    def request_poweroff(self, why):
        if self._requested.is_set():
            return
        self._requested.set()
        log.warning("关机：%s", why)
        if self.dry_run:
            log.warning("dry_run：不执行 systemctl poweroff")
            return
        subprocess.Popen(["systemctl", "poweroff"])

    def powering_off(self):
        """服务停止时判断是不是在关机（而不是重启或只重启本服务）。"""
        if self._requested.is_set():
            return True
        try:
            r = subprocess.run(["systemctl", "list-jobs", "--no-legend"],
                               capture_output=True, text=True, timeout=3)
        except (OSError, subprocess.SubprocessError):
            return False
        jobs = r.stdout
        if "reboot.target" in jobs or "kexec.target" in jobs:
            return False
        return "poweroff.target" in jobs or "halt.target" in jobs
