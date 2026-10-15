import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lists import double_all

def test_three():
    assert double_all([1, 2, 3]) == [2, 4, 6]


def test_single():
    assert double_all([7]) == [14]
