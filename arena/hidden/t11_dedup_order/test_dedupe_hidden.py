import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from dedupe import dedup

def test_all_same():
    assert dedup([7, 7, 7]) == [7]


def test_no_mutation():
    src = [1, 1, 2]
    dedup(src)
    assert src == [1, 1, 2]


def test_mixed_order():
    assert dedup([5, 4, 5, 4, 3]) == [5, 4, 3]
