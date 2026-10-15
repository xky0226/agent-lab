def words(text):
    """按空白切词，并统一转成小写。"""
    return text.split()


def count_words(text):
    """统计每个词出现的次数，返回 词 -> 次数。"""
    counts = {}
    for w in words(text):
        counts[w] = counts.get(w, 0) + 1
    return counts
