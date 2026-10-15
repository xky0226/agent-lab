def percent(done, total):
    """完成率，百分数（保留一位小数）。total 为 0 时返回 0.0。"""
    if total == 0:
        return 0.0
    return round(done / total, 1)
