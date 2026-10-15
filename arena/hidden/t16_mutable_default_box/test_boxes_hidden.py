import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from boxes import add_item

def test_fresh_dict_each_time():
    assert add_item("a", 1) == {"a": 1}
    assert add_item("b", 2) == {"b": 2}


def test_explicit_box_is_mutated():
    box = {"z": 0}
    out = add_item("a", 1, box)
    assert out == {"z": 0, "a": 1}
    assert box == {"z": 0, "a": 1}


def test_none_gives_new_dict():
    assert add_item("k", 9, None) == {"k": 9}
    assert add_item("k", 9, None) == {"k": 9}


def test_overwrite():
    assert add_item("a", 2, {"a": 1}) == {"a": 2}
