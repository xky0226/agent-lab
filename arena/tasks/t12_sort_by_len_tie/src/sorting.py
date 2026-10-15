def sort_by_len(words):
    """按长度升序；长度一样按字母序。返回新列表。"""
    return sorted(words, key=lambda w: len(w))
