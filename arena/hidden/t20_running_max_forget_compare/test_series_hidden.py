import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from series import running_max

def test_empty():
    assert running_max([]) == []


def test_single():
    assert running_max([4]) == [4]


def test_all_equal():
    assert running_max([2, 2]) == [2, 2]


def test_negative():
    assert running_max([-3, -1, -5]) == [-3, -1, -1]
