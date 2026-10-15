import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from grade import grade

def test_a_line():
    assert grade(90) == "A"


def test_b_line():
    assert grade(80) == "B"


def test_c_line():
    assert grade(70) == "C"


def test_d_line():
    assert grade(60) == "D"


def test_edges():
    assert grade(100) == "A"
    assert grade(0) == "F"
    assert grade(59) == "F"
