def parse_int(s, default=0):
    """把字符串转成整数；转不了（包括 None）就给 default。"""
    try:
        return int(s)
    except TypeError:
        return default
