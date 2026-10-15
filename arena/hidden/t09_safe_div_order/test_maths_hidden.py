import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from maths import safe_div

def test_negative():
    assert safe_div(-6, 3) == -2.0


def test_zero_divided():
    assert safe_div(0, 5) == 0.0


def test_rounding():
    assert safe_div(1, 3) == 0.33


def test_zero_over_zero():
    assert safe_div(0, 0) is None
