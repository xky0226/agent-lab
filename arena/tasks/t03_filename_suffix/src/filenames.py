def strip_ext(name):
    """去掉文件名末尾的 ".txt" 后缀。"""
    return name.rstrip(".txt")


def group_by_stem(names):
    """按「去后缀后的主名」归类，返回 主名 -> 出现次数。"""
    counts = {}
    for n in names:
        stem = strip_ext(n)
        counts[stem] = counts.get(stem, 0) + 1
    return counts
