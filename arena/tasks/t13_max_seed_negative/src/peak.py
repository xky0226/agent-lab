def max_of(nums):
    """返回列表里的最大值；空列表返回 None。"""
    if not nums:
        return None
    best = 0
    for n in nums[1:]:
        if n > best:
            best = n
    return best
