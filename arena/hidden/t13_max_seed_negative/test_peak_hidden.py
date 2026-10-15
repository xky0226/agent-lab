import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from peak import max_of

def test_empty():
    assert max_of([]) is None


def test_all_equal():
    assert max_of([4, 4]) == 4


def test_mixed():
    assert max_of([-1, 0, 1]) == 1


def test_float():
    assert max_of([0.5, -0.5]) == 0.5
