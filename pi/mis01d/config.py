"""读 /etc/mis01/mis01.conf（INI 格式）。缺的项用默认值。"""
import configparser
from dataclasses import dataclass, field


@dataclass
class Config:
    # ESP 原生 USB 口（udev 建的固定名字，见 udev/99-mis01.rules）
    esp_port: str = "/dev/mis01-esp"
    esp_retry_s: float = 2.0
    # FPGA（EL 屏控制）串口
    fpga_port: str = "/dev/ttyS4"
    fpga_baud: int = 115200
    fpga_on_at_start: bool = True
    # 40 针 22 脚 PI_SHDN_REQ = GPIO1_D0 = gpiochip1 第 24 线
    shdn_chip: str = "gpiochip1"
    shdn_line: int = 24
    shdn_debounce_ms: int = 500
    # Pi 已 NTP 同步时，ESP 连上发一次 TIME，之后每隔这么久再发
    time_sync_h: float = 6.0
    sock_path: str = "/run/mis01/esp.sock"
    sock_group: str = "dialout"
    state_path: str = "/var/lib/mis01/state.json"
    # 调试：不真的关机、不碰 GPIO
    dry_run: bool = False
    # [esp_cfg] 节：要下发给 ESP 的 CFG 键（键名大写，值原样）
    esp_cfg: dict = field(default_factory=dict)


def load(path: str) -> Config:
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str          # 保留键名大小写
    cp.read(path, encoding="utf-8")
    c = Config()
    if cp.has_section("esp"):
        s = cp["esp"]
        c.esp_port = s.get("port", c.esp_port)
        c.esp_retry_s = s.getfloat("retry_s", c.esp_retry_s)
        c.time_sync_h = s.getfloat("time_sync_h", c.time_sync_h)
    if cp.has_section("fpga"):
        s = cp["fpga"]
        c.fpga_port = s.get("port", c.fpga_port)
        c.fpga_baud = s.getint("baud", c.fpga_baud)
        c.fpga_on_at_start = s.getboolean("on_at_start", c.fpga_on_at_start)
    if cp.has_section("gpio"):
        s = cp["gpio"]
        c.shdn_chip = s.get("shdn_chip", c.shdn_chip)
        c.shdn_line = s.getint("shdn_line", c.shdn_line)
        c.shdn_debounce_ms = s.getint("shdn_debounce_ms", c.shdn_debounce_ms)
    if cp.has_section("service"):
        s = cp["service"]
        c.sock_path = s.get("sock_path", c.sock_path)
        c.sock_group = s.get("sock_group", c.sock_group)
        c.state_path = s.get("state_path", c.state_path)
        c.dry_run = s.getboolean("dry_run", c.dry_run)
    if cp.has_section("esp_cfg"):
        c.esp_cfg = {k.upper(): v.strip() for k, v in cp["esp_cfg"].items() if v.strip() != ""}
    return c
