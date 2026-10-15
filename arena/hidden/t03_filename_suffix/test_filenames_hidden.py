import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from filenames import group_by_stem, strip_ext

def test_strip_basic():
    assert strip_ext("notes.txt") == "notes"
    assert strip_ext("a.txt") == "a"


def test_strip_single_letter():
    assert strip_ext("x.txt") == "x"


def test_strip_trap():
    assert strip_ext("test.txt") == "test"
    assert strip_ext("index.txt") == "index"


def test_strip_no_ext():
    assert strip_ext("readme") == "readme"


def test_group_counts():
    assert group_by_stem(["report.txt", "next.txt", "report.txt"]) == {"report": 2, "next": 1}
