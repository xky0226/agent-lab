import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from picks import every_other

def test_empty():
    assert every_other([]) == []


def test_one():
    assert every_other([9]) == [9]


def test_numbers():
    assert every_other([1, 2, 3, 4, 5]) == [1, 3, 5]


def test_string():
    assert every_other("abcde") == ["a", "c", "e"]
