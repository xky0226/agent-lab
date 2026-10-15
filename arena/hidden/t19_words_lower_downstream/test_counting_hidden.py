import os
import sys

_src = os.environ.get("ARENA_SRC")
if not _src:
    raise RuntimeError("ARENA_SRC 没设 —— 判分测试只能由 _make_tasks.py / _eval.py 启动（模型的 run_tests 【故意】不跑它）")
sys.path.insert(0, _src)

from counting import words, count_words

def test_words_lower():
    assert words("A B") == ["a", "b"]


def test_words_empty():
    assert words("") == []


def test_count_mixed():
    assert count_words("a A b") == {"a": 2, "b": 1}


def test_count_empty():
    assert count_words("") == {}


def test_count_whitespace():
    assert count_words("  a   a  ") == {"a": 2}
