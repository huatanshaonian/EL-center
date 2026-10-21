"""FPGA（EL 屏控制，fpga/el_hdmi/使用说明.txt 第 5 节）：/dev/ttyS4 115200 8N1，一行一条，回 OK/ERR。"""
import logging
import re
import time

import serial

log = logging.getLogger("fpga")


class Fpga:
    def __init__(self, port, baud=115200):
        self.port = port
        self.baud = baud

    def _cmd(self, ser, line, timeout=1.0):
        ser.reset_input_buffer()
        ser.write((line + "\r\n").encode("ascii"))
        end = time.time() + timeout
        while time.time() < end:
            r = ser.readline().decode("ascii", "replace").strip()
            if r:
                return r
        return None

    def send(self, line, timeout=1.0):
        try:
            with serial.Serial(self.port, self.baud, timeout=0.2) as ser:
                r = self._cmd(ser, line, timeout)
        except (serial.SerialException, OSError) as e:
            log.warning("FPGA 串口 %s 打不开：%s", self.port, e)
            return None
        log.info("FPGA %s → %s", line, r)
        return r

    def power_on(self):
        return self.send("R1")

    def power_off(self, wait_s=3.0):
        """R0：先关 VD 再停扫描（约 1 s）。等到 ? 里 ST=0 或超时。"""
        try:
            with serial.Serial(self.port, self.baud, timeout=0.2) as ser:
                r = self._cmd(ser, "R0")
                log.info("FPGA R0 → %s", r)
                end = time.time() + wait_s
                while time.time() < end:
                    st = self._cmd(ser, "?", 0.5) or ""
                    m = re.search(r"\bST=(\d)", st)
                    if m and m.group(1) == "0":
                        log.info("FPGA 已关（%s）", st)
                        return True
                    time.sleep(0.2)
        except (serial.SerialException, OSError) as e:
            log.warning("FPGA 串口 %s 打不开：%s", self.port, e)
            return False
        log.warning("FPGA %g s 内没回到 ST=0", wait_s)
        return False
