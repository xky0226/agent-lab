import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from tags import join_tags

def test_three():
    assert join_tags(["a", "b", "c"]) == "#a #b #c"


def test_keeps_order():
    assert join_tags(["z", "a"]) == "#z #a"


def test_no_alias():
    src = ["a"]
    join_tags(src)
    assert src == ["a"]
