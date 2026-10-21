"""ESP32-S3 协议链路（规格第 6 节）：一行一条命令，恰好回一行 OK/ERR；"!" 主动上报、"#" 日志可插在任意位置。

断线自动重连；连上后在单独线程里调 on_connect（可以在里面发命令）。
"""
import logging
import queue
import threading
import time

import serial

log = logging.getLogger("esp")


class EspError(Exception):
    pass


class EspLink:
    def __init__(self, port, on_report=None, on_connect=None, retry_s=2.0):
        self.port = port
        self.on_report = on_report
        self.on_connect = on_connect
        self.retry_s = retry_s
        self._ser = None
        self._resp = queue.Queue()
        self._extra = []              # 命令执行期间收到的 "#" 行（如 LOG? 的内容）
        self._cmd_lock = threading.Lock()
        self._stop = threading.Event()
        self._connected = threading.Event()
        self._thread = None

    # ---------------- 生命周期 ----------------
    def start(self):
        self._thread = threading.Thread(target=self._run, name="esp-link", daemon=True)
        self._thread.start()

    def stop(self):
        # 先让读线程自己退出（read 超时 0.2 s），再关口；从别的线程直接关口会让读线程抛异常
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(1.0)
        self._close()

    @property
    def connected(self):
        return self._connected.is_set()

    def wait_connected(self, timeout):
        return self._connected.wait(timeout)

    # ---------------- 命令 ----------------
    def command(self, line, timeout=2.0):
        """发一条命令，返回 (应答行, 期间收到的 # 行列表)。没连上或超时抛 EspError。"""
        if "\n" in line or "\r" in line:
            raise EspError("命令里不能有换行")
        with self._cmd_lock:
            ser = self._ser
            if ser is None or not self.connected:
                raise EspError("ESP 未连接")
            while not self._resp.empty():
                self._resp.get_nowait()
            self._extra = []
            try:
                ser.write((line + "\n").encode("utf-8"))
            except (serial.SerialException, OSError) as e:
                self._close()
                raise EspError("写失败：%s" % e)
            try:
                r = self._resp.get(timeout=timeout)
            except queue.Empty:
                raise EspError("等应答超时：%s" % line)
            return r, list(self._extra)

    def q(self, line, timeout=2.0):
        """只要应答行。"""
        return self.command(line, timeout)[0]

    # ---------------- 内部 ----------------
    def _close(self):
        self._connected.clear()
        ser, self._ser = self._ser, None
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass

    def _run(self):
        while not self._stop.is_set():
            try:
                ser = serial.Serial(self.port, 115200, timeout=0.2)
                ser.dtr = True        # DTR 有效 = Pi 在线（ESP 据此保持 HOST 模式、发 !BOOT）
                ser.reset_input_buffer()
            except (serial.SerialException, OSError) as e:
                log.debug("打不开 %s：%s", self.port, e)
                self._stop.wait(self.retry_s)
                continue
            self._ser = ser
            self._connected.set()
            log.info("ESP 已连接 %s", self.port)
            if self.on_connect:
                threading.Thread(target=self._safe_on_connect, name="esp-onconnect", daemon=True).start()
            self._read_loop(ser)
            self._close()
            if not self._stop.is_set():
                log.warning("ESP 断开，%g s 后重连", self.retry_s)
                self._stop.wait(self.retry_s)

    def _safe_on_connect(self):
        try:
            self.on_connect(self)
        except Exception:
            log.exception("连接后处理出错")

    def _read_loop(self, ser):
        buf = b""
        while not self._stop.is_set():
            try:
                chunk = ser.read(256)
            except Exception as e:      # 拔线：SerialException/OSError；口被关：pyserial 可能抛 TypeError 等
                if not self._stop.is_set():
                    log.warning("读失败：%s", e)
                return
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                self._handle(raw.decode("utf-8", "replace").strip())

    def _handle(self, line):
        if not line:
            return
        if line.startswith("!"):
            log.info("上报 %s", line)
            if self.on_report:
                try:
                    self.on_report(line)
                except Exception:
                    log.exception("处理上报出错：%s", line)
        elif line.startswith("#"):
            self._extra.append(line)
            log.debug("%s", line)
        elif line.startswith("OK") or line.startswith("ERR"):
            self._resp.put(line)
        else:
            log.debug("未知行：%s", line)


def quote(v):
    """CFG/SHOW 的值带空格时加双引号（协议 6.2）。值里不允许双引号。"""
    if '"' in v:
        raise ValueError("值里不能有双引号")
    return '"%s"' % v if (" " in v or v == "") else v


def wait_ok(link, line, timeout=2.0, tries=3):
    """发命令直到回 OK（断线重连期间重试几次）。"""
    last = None
    for _ in range(tries):
        try:
            r = link.q(line, timeout)
            if r.startswith("OK"):
                return r
            last = r
        except EspError as e:
            last = str(e)
        time.sleep(0.3)
    raise EspError("%s 失败：%s" % (line, last))
