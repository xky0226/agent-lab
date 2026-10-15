import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from pairs import parse_pair

def test_empty_value():
    assert parse_pair("k:") == ("k", "")


def test_empty_key():
    assert parse_pair(":v") == ("", "v")


def test_empty():
    assert parse_pair("") == ("", "")


def test_many_colons():
    assert parse_pair("a:b:c:d") == ("a", "b:c:d")
