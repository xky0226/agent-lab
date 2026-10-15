import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from counting import words, count_words

def test_words_plain():
    assert words("a b") == ["a", "b"]


def test_count_case():
    assert count_words("Hello hello HELLO") == {"hello": 3}
