import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from padding import pad_right

def test_empty():
    assert pad_right([], 2) == [0, 0]


def test_already_long():
    assert pad_right([1, 2, 3], 2) == [1, 2, 3]


def test_custom_fill():
    assert pad_right(["a"], 3, "-") == ["a", "-", "-"]


def test_untouched_when_padded():
    src = [1]
    out = pad_right(src, 3)
    assert out == [1, 0, 0]
    assert src == [1]
