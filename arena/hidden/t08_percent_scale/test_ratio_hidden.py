import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from ratio import percent

def test_third():
    assert percent(1, 3) == 33.3


def test_zero_done():
    assert percent(0, 5) == 0.0


def test_over():
    assert percent(5, 4) == 125.0


def test_rounding():
    assert percent(2, 3) == 66.7
