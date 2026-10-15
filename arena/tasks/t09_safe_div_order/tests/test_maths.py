import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from maths import safe_div

def test_normal():
    assert safe_div(6, 2) == 3.0


def test_zero_divisor():
    assert safe_div(1, 0) is None
