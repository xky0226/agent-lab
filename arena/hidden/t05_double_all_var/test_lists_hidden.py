import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from lists import double_all

def test_negative():
    assert double_all([0, -1, -2]) == [0, -2, -4]


def test_empty():
    assert double_all([]) == []


def test_float():
    assert double_all([0.5, 1.5]) == [1.0, 3.0]


def test_not_alias():
    src = [1, 2]
    out = double_all(src)
    out.append(0)
    assert src == [1, 2]
