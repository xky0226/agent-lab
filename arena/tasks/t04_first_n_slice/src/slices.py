def first_n(items, n):
    """返回 items 的前 n 个元素（新列表）；n 比长度大就全给。"""
    return list(items[:n - 1])
