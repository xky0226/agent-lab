import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from series import running_max

def test_rising():
    assert running_max([1, 3, 2]) == [1, 3, 3]


def test_falling():
    assert running_max([5, 1]) == [5, 5]
