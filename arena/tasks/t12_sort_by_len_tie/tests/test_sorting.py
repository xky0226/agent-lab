import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sorting import sort_by_len

def test_by_length():
    assert sort_by_len(["ccc", "a", "bb"]) == ["a", "bb", "ccc"]


def test_tie():
    assert sort_by_len(["bb", "aa", "ab"]) == ["aa", "ab", "bb"]
