"""IV-18 能显示的文字（与 ESP 固件 vfd_font.c 同一张表，改了要两边一起改）。

七段 + 小数点，8 位；"." 并到前一位；"*" 显示为 °。K M V W X Z 等显示不了。
"""

# 有大小写两种字形的字母；其余字母大小写同形
_TWO_FORMS = set("CcHhOoUuIi")
_ONE_FORM = set("ABDEFGJLNPQRSTY")
_SYMBOLS = set("0123456789 -_='*")


def char_ok(c):
    return c in _SYMBOLS or c in _TWO_FORMS or c.upper() in _ONE_FORM


def check(text):
    """合法返回 None，否则返回说明。"""
    if text.strip().upper() == "OFF":
        return "不能是 OFF（协议里表示停播）"
    if '"' in text:
        return '不能含双引号（协议用它包文字）'
    n = 0
    prev_dp = True          # 开头的点独占一位
    for c in text:
        if c == ".":
            if prev_dp:
                n += 1
            prev_dp = True
            continue
        if not char_ok(c):
            return "IV-18 显示不了“%s”（七段表示不了 K M V W X Z 等）" % c
        n += 1
        prev_dp = False
    if n > 8:
        return "超过 8 位（%d 位；“.” 并到前一位不占位）" % n
    return None
