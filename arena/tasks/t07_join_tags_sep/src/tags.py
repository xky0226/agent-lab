def join_tags(tags):
    """把标签拼成 "#a #b" 的形式；空列表返回空串。"""
    return "".join("#" + t for t in tags)
