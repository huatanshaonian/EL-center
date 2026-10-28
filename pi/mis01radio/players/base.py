class Player:
    """一种电台类型的播放器。控制器同一时间只开一个实例。"""
    TYPE = ""
    LABEL = ""
    # 该类型自己的字段：{"key", "label", "hint", "required", "multiline"}
    FIELDS = []

    def __init__(self, ctx):
        self.ctx = ctx          # 控制器：ctx.store、ctx.browser

    def start(self, station):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def poll(self):
        """返回 {"state": "starting"|"playing"|"stalled"|"dead", "title": 当前曲目, "detail": 说明}。
        dead = 进程没了，控制器会重开；stalled = 还在但没出声音，只显示提示。"""
        raise NotImplementedError

    @classmethod
    def describe(cls):
        return {"type": cls.TYPE, "label": cls.LABEL, "fields": cls.FIELDS}
