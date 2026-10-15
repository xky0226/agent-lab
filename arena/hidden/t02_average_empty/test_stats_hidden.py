import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from stats import average

def test_single():
    assert average([5]) == 5.0


def test_empty_none():
    assert average([]) is None


def test_zeros():
    assert average([0, 0]) == 0.0


def test_negative():
    assert average([-1, 1]) == 0.0


def test_rounding():
    assert average([1, 2, 3, 4]) == 2.5
