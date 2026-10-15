import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from slices import first_n

def test_all():
    assert first_n([1, 2, 3], 3) == [1, 2, 3]


def test_zero():
    assert first_n([1, 2], 0) == []


def test_empty():
    assert first_n([], 3) == []


def test_keeps_order():
    assert first_n("abcd", 2) == ["a", "b"]


def test_no_alias():
    src = [1, 2, 3]
    out = first_n(src, 2)
    out.append(99)
    assert src == [1, 2, 3]
