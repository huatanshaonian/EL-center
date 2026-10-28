"""直链电台（http/https 流、m3u8、pls/m3u）：mpv 播放，经 IPC 读状态和曲目名（ICY StreamTitle）。"""
import json
import logging
import os
import signal
import socket
import subprocess

from .. import audio
from .base import Player

log = logging.getLogger("stream")


class StreamPlayer(Player):
    TYPE = "stream"
    LABEL = "直链（mpv）"
    FIELDS = [{"key": "url", "label": "流地址", "required": True,
               "hint": "http(s) 音频流、m3u8、pls/m3u 都可以，例 http://sc6.radiocaroline.net:8040/stream"}]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.proc = None
        self.ipc = os.path.expanduser("~/mpv.sock")

    def start(self, station):
        self.stop()
        cmd = ["mpv", "--no-video", "--no-terminal", "--idle=no", "--ao=alsa", "--audio-device=alsa/" + audio.PCM,
               "--input-ipc-server=" + self.ipc, "--network-timeout=20", "--cache=yes", "--cache-secs=10",
               "--loop-playlist=inf", station["url"]]
        env = dict(os.environ)
        proxy = self.ctx.store.settings.get("proxy")
        if proxy:
            env["http_proxy"] = env["https_proxy"] = proxy
        log.info("mpv 播放 %s", station["url"])
        self.proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     start_new_session=True)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(5)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()
        self.proc = None

    def _get(self, prop):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(self.ipc)
            s.sendall((json.dumps({"command": ["get_property", prop]}) + "\n").encode())
            f = s.makefile("rb")
            for line in f:
                m = json.loads(line)
                if "event" not in m:
                    return m.get("data") if m.get("error") == "success" else None
        return None

    def poll(self):
        if not self.proc or self.proc.poll() is not None:
            return {"state": "dead", "title": "", "detail": "mpv 退出了（网络断了或地址失效）"}
        try:
            idle = self._get("core-idle")
            meta = self._get("metadata") or {}
            title = meta.get("icy-title") or ""
            if idle is False:
                return {"state": "playing", "title": title, "detail": ""}
            return {"state": "starting", "title": title, "detail": "缓冲中"}
        except (OSError, ValueError):
            return {"state": "starting", "title": "", "detail": "连接中"}
