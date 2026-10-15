def safe_div(a, b):
    """a / b，保留两位小数；b 为 0 时返回 None。"""
    result = round(a / b, 2)
    if b == 0:
        return None
    return result
