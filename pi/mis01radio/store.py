"""电台表与设置：存在一个 JSON 文件里（默认 /var/lib/mis01radio/radio.json），网页改了立即写回。"""
import copy
import hashlib
import json
import logging
import os
import re
import secrets
import threading

from . import vfdtext

log = logging.getLogger("store")

DEFAULT_SETTINGS = {
    "volume": 40,              # 0–100
    "resume": False,           # 服务启动时接着放上次的电台
    "last_id": "",
    "alsa_card": "auto",       # auto = 找耳机口（es8316），或填 /proc/asound/cards 里的名字
    "alsa_dmix": True,         # 经 dmix 混音（换台时 mpv 和浏览器短暂重叠不会抢设备）
    "proxy": "",               # 例 http://192.168.1.2:10808，留空不用
    "browser_mode": "headless",  # headless | xvfb（headless 没声音时改 xvfb）
    "browser_idle_min": 10,    # 远程画面用完、又没在放网页电台时，浏览器多久后关
    "vfd_volume_s": 2,         # 调音量时 IV-18 显示 "UOL  nn" 的秒数
    "password_hash": "",       # 网页密码（加盐 sha256）；空 = 不要密码
}

# 第一次运行时的电台表
DEFAULT_STATIONS = [
    {"id": "caroline", "name": "Radio Caroline", "type": "stream", "enabled": True,
     "vfd": "CAroLInE", "url": "http://sc6.radiocaroline.net:8040/stream"},
    {"id": "br24", "name": "BR24", "type": "browser", "enabled": True,
     "vfd": " br 24", "page_url": "https://www.br.de/radio/live/br24/",
     "play_js": "document.querySelector('[aria-label=\"Livestream abspielen\"]')?.click()", "check_js": ""},
]

_ID_RE = re.compile(r"^[a-z0-9_-]{1,32}$")


def hash_password(pw):
    salt = secrets.token_hex(8)
    return salt + "$" + hashlib.sha256((salt + pw).encode()).hexdigest()


def check_password(stored, pw):
    if not stored:
        return True
    salt, _, h = stored.partition("$")
    return secrets.compare_digest(hashlib.sha256((salt + pw).encode()).hexdigest(), h)


class Store:
    def __init__(self, path, types):
        self.path = path
        self.types = types          # {类型名: 播放器类}，用来检查各类型自己的字段
        self.lock = threading.RLock()
        self.settings = dict(DEFAULT_SETTINGS)
        self.stations = copy.deepcopy(DEFAULT_STATIONS)
        self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
        except FileNotFoundError:
            log.info("%s 不存在，用默认电台表", self.path)
            self.save()
            return
        except (OSError, ValueError) as e:
            log.error("读 %s 失败（%s），用默认值，不覆盖原文件", self.path, e)
            return
        self.settings.update({k: v for k, v in d.get("settings", {}).items() if k in DEFAULT_SETTINGS})
        self.stations = d.get("stations", self.stations)

    def save(self):
        with self.lock:
            d = {"settings": self.settings, "stations": self.stations}
            tmp = self.path + ".tmp"
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=1)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)

    # ---- 电台
    def get(self, sid):
        with self.lock:
            for s in self.stations:
                if s["id"] == sid:
                    return dict(s)
        return None

    def enabled(self):
        with self.lock:
            return [dict(s) for s in self.stations if s.get("enabled", True)]

    def validate(self, st):
        """检查一条电台，返回 (清洗后的 dict, 错误说明或 None)。"""
        t = st.get("type")
        if t not in self.types:
            return None, "未知类型 %s" % t
        out = {"id": str(st.get("id", "")).strip().lower(), "name": str(st.get("name", "")).strip(),
               "type": t, "enabled": bool(st.get("enabled", True)), "vfd": str(st.get("vfd", ""))}
        if not _ID_RE.match(out["id"]):
            return None, "编号只能用小写字母、数字、- 和 _（1–32 个）"
        if not out["name"]:
            return None, "名字不能为空"
        err = vfdtext.check(out["vfd"])
        if err:
            return None, "IV-18 文字：" + err
        for f in self.types[t].FIELDS:
            v = str(st.get(f["key"], "")).strip()
            if f.get("required") and not v:
                return None, "“%s”不能为空" % f["label"]
            out[f["key"]] = v
        return out, None

    def upsert(self, st, old_id=None):
        clean, err = self.validate(st)
        if err:
            return err
        with self.lock:
            key = old_id or clean["id"]
            for i, s in enumerate(self.stations):
                if s["id"] == key:
                    if clean["id"] != key and self.get(clean["id"]):
                        return "编号 %s 已被占用" % clean["id"]
                    self.stations[i] = clean
                    break
            else:
                if self.get(clean["id"]):
                    return "编号 %s 已被占用" % clean["id"]
                self.stations.append(clean)
            self.save()
        return None

    def delete(self, sid):
        with self.lock:
            self.stations = [s for s in self.stations if s["id"] != sid]
            self.save()

    def reorder(self, ids):
        with self.lock:
            pos = {sid: i for i, sid in enumerate(ids)}
            self.stations.sort(key=lambda s: pos.get(s["id"], len(pos)))
            self.save()

    # ---- 设置
    def update_settings(self, d):
        with self.lock:
            for k, v in d.items():
                if k not in DEFAULT_SETTINGS or k == "password_hash":
                    continue
                dv = DEFAULT_SETTINGS[k]
                if isinstance(dv, bool):
                    v = bool(v)
                elif isinstance(dv, int):
                    v = int(v)
                else:
                    v = str(v).strip()
                self.settings[k] = v
            self.settings["volume"] = max(0, min(100, self.settings["volume"]))
            if self.settings["browser_mode"] not in ("headless", "xvfb"):
                self.settings["browser_mode"] = "headless"
            self.save()

    def set_password(self, pw):
        with self.lock:
            self.settings["password_hash"] = hash_password(pw) if pw else ""
            self.save()

    def public_settings(self):
        with self.lock:
            d = {k: v for k, v in self.settings.items() if k != "password_hash"}
            d["has_password"] = bool(self.settings["password_hash"])
            return d
