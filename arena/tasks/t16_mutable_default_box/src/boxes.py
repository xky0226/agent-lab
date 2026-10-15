def add_item(key, value, box={}):
    """把 key->value 放进 box 并返回它。

    box 省略或传 None -> 新建一个空字典（每次都是新的）；
    传了字典 -> 就地改它（改动会留在外面）。
    """
    if box is None:
        box = {}
    box[key] = value
    return box
