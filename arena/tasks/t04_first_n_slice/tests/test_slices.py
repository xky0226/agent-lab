import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from slices import first_n

def test_two():
    assert first_n([1, 2, 3], 2) == [1, 2]


def test_one():
    assert first_n(["a", "b"], 1) == ["a"]


def test_more_than_len():
    assert first_n([1, 2], 5) == [1, 2]
