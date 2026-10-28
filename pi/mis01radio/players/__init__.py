"""电台类型。加一种新类型：在本目录写一个 Player 子类（TYPE、LABEL、FIELDS、start/stop/poll），再加进 TYPES。

管理网页按 FIELDS 自动生成该类型的输入框，不用改网页。
"""
from .base import Player
from .browser import BrowserPlayer
from .stream import StreamPlayer

TYPES = {p.TYPE: p for p in (StreamPlayer, BrowserPlayer)}

__all__ = ["Player", "TYPES"]
