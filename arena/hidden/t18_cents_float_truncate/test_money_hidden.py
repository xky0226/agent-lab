import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from money import to_cents, total_cents

def test_single_awkward():
    assert to_cents(0.29) == 29


def test_zero():
    assert to_cents(0) == 0


def test_exact():
    assert to_cents(3.5) == 350


def test_negative():
    assert to_cents(-1.5) == -150
