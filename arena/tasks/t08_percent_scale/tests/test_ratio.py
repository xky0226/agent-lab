import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ratio import percent

def test_half():
    assert percent(1, 2) == 50.0


def test_all():
    assert percent(3, 3) == 100.0


def test_zero_total():
    assert percent(0, 0) == 0.0
