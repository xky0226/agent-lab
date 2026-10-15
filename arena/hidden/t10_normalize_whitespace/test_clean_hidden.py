import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from clean import normalize

def test_mixed_whitespace():
    assert normalize("a \t\n b") == "a b"


def test_only_whitespace():
    assert normalize("   ") == ""


def test_untouched():
    assert normalize("word") == "word"


def test_three_words():
    assert normalize(" a  b   c ") == "a b c"
