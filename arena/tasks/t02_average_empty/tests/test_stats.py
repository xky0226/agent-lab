import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stats import average

def test_three():
    assert average([1, 2, 3]) == 2.0


def test_decimal():
    assert average([1, 2]) == 1.5


def test_empty():
    assert average([]) is None
