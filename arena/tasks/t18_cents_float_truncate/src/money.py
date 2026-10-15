def to_cents(yuan):
    """元 -> 分（四舍五入到整数分）。"""
    return int(yuan * 100)


def total_cents(prices):
    """把一组单价（元）换算成分之后加起来。"""
    return sum(to_cents(p) for p in prices)
