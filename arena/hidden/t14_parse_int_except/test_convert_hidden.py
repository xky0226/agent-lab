import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from convert import parse_int

def test_none():
    assert parse_int(None) == 0


def test_spaces():
    assert parse_int("  8  ") == 8


def test_float_string():
    assert parse_int("3.9") == 0


def test_empty():
    assert parse_int("") == 0
