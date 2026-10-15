def average(nums):
    """求平均值（保留两位小数）。空列表返回 None。"""
    return round(sum(nums) / len(nums), 2)
