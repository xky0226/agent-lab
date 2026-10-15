def pad_right(items, n, fill=0):
    """返回长度 n 的新列表，不够的用 fill 补在右边。

    已经有 n 个或更多就原样返回一份拷贝（不截断）。
    传入的 items 不会被改动。
    """
    out = items
    while len(out) < n:
        out.append(fill)
    return out
