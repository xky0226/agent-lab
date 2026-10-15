import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from picks import every_other

def test_four():
    assert every_other(["a", "b", "c", "d"]) == ["a", "c"]


def test_three():
    assert every_other([1, 2, 3]) == [1, 3]
