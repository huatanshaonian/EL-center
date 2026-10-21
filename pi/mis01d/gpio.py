"""读 PI_SHDN_REQ（40 针 22 脚）。用 libgpiod 的 Python 绑定，v1（Ubuntu/Armbian 的 python3-libgpiod 1.6）和 v2 都支持。

内部上拉靠请求时的 bias 标志（内核 ≥ 5.5、pinctrl-rockchip 支持）。
"""


class InputLine:
    def __init__(self, chip, line, pull_up=True, consumer="mis01d"):
        import gpiod
        self._v2 = hasattr(gpiod, "request_lines")
        if self._v2:
            from gpiod.line import Bias, Direction
            path = chip if chip.startswith("/dev/") else "/dev/" + chip
            settings = gpiod.LineSettings(direction=Direction.INPUT,
                                          bias=Bias.PULL_UP if pull_up else Bias.AS_IS)
            self._req = gpiod.request_lines(path, consumer=consumer, config={line: settings})
            self._line = line
        else:
            self._gpiod = gpiod
            self._chip = gpiod.Chip(chip)
            self._ln = self._chip.get_line(line)
            flags = gpiod.LINE_REQ_FLAG_BIAS_PULL_UP if pull_up else 0
            self._ln.request(consumer=consumer, type=gpiod.LINE_REQ_DIR_IN, flags=flags)

    def get(self):
        if self._v2:
            from gpiod.line import Value
            return 1 if self._req.get_value(self._line) == Value.ACTIVE else 0
        return self._ln.get_value()

    def close(self):
        try:
            if self._v2:
                self._req.release()
            else:
                self._ln.release()
                self._chip.close()
        except Exception:
            pass


class FakeLine:
    """dry_run / 电脑上调试用：一直读高（不请求关机）。"""

    def get(self):
        return 1

    def close(self):
        pass
