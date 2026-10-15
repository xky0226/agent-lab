import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from peak import max_of

def test_positive():
    assert max_of([1, 5, 3]) == 5


def test_single():
    assert max_of([7]) == 7


def test_negative():
    assert max_of([-5, -2, -9]) == -2
