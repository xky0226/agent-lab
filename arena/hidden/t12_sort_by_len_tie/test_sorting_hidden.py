import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from sorting import sort_by_len

def test_mixed():
    assert sort_by_len(["bbb", "a", "cc", "dd"]) == ["a", "cc", "dd", "bbb"]


def test_empty():
    assert sort_by_len([]) == []


def test_one():
    assert sort_by_len(["zz"]) == ["zz"]


def test_all_same_len():
    assert sort_by_len(["c", "a", "b"]) == ["a", "b", "c"]
