import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from money import to_cents, total_cents

def test_simple():
    assert total_cents([1.5, 2.5]) == 400


def test_awkward():
    assert total_cents([0.29, 0.01]) == 30
