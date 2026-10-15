def parse_pair(s):
    """把 "名字:值" 拆成 (名字, 值)。

    没有冒号 -> 值给空串；只按【第一个】冒号拆。
    """
    if ":" not in s:
        return (s, "")
    return tuple(s.split(":"))
