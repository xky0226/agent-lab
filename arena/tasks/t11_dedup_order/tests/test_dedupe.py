import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dedupe import dedup

def test_simple():
    assert dedup([1, 1]) == [1]


def test_empty():
    assert dedup([]) == []


def test_order():
    assert dedup([3, 1, 3, 2]) == [3, 1, 2]
